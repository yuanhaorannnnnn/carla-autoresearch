"""Invoke the isolated CARLA worker without activating or modifying environments."""

import hashlib
import json
import os
import socket
import sys
from pathlib import Path
import subprocess
import uuid

from .protocol import AgentError, READ_ONLY, atomic_json, load_profile, validate_parameters


def invoke(profile, operation, parameters, output_dir=None, timeout_seconds=None):
    validate_parameters(operation, parameters)
    if operation not in READ_ONLY:
        if profile.get("session_policy") != "exclusive":
            raise AgentError("exclusive_session_required", "Set session_policy=exclusive only for a dedicated instance", 3)
        if not profile.get("expected_server_version"):
            raise AgentError("server_version_required", "Pin expected_server_version before mutations", 3)
    python = Path(profile["client_python"])
    if not python.is_file() or not os.access(python, os.X_OK):
        raise AgentError("client_python_unavailable", str(python), 3)
    output = None
    if operation == "capture.run":
        recipe = parameters["recipe"]
        count, warmup = recipe.get("frames", 10), recipe.get("warmup_frames", 2)
        if type(count) is not int or type(warmup) is not int or not 1 <= count <= 10000 or not 0 <= warmup <= 1000:
            raise AgentError("invalid_recipe", "frames must be 1..10000 and warmup_frames 0..1000", 2)
        output = Path(output_dir) if output_dir is not None else Path(profile["output_root"]) / "captures" / uuid.uuid4().hex
        output = output.resolve()
        if Path(profile["output_root"]).resolve() not in output.parents:
            raise AgentError("invalid_output_path", "Capture output must be a child of output_root", 2)
        try:
            output.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise AgentError("output_exists", "Use a fresh capture directory; old metrics are never reused", 5) from exc
        except OSError as exc:
            raise AgentError("output_unavailable", str(exc), 3) from exc
    request = {"operation": operation, "profile": profile, "parameters": parameters,
               "output_dir": str(output) if output else None}
    try:
        payload = json.dumps(request, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise AgentError("invalid_parameters", str(exc), 2) from exc
    timeout = profile["timeout_seconds"]
    if operation == "capture.run":
        timeout = timeout * (count + warmup + 5)
    elif operation == "world.tick":
        frames = parameters.get("frames", 1)
        if not 1 <= frames <= 1000:
            raise AgentError("invalid_parameters", "frames must be 1..1000", 2)
        timeout *= frames + 2
    else:
        timeout = max(10, timeout * 3)
    if timeout_seconds is not None:
        import math
        if type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise AgentError("invalid_timeout", "timeout_seconds override must be finite and positive", 2)
        timeout = min(timeout, timeout_seconds)
    worker = Path(__file__).with_name("worker.py")
    proc = None
    try:
        proc = subprocess.Popen([str(python), str(worker)], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = proc.communicate(payload, timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                stdout, stderr = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
            raise AgentError("worker_timeout", "Worker timed out; inspect session cleanup before retry",
                             details={"cleanup_required": True, "output_dir": str(output) if output else None})
        if output:
            (output / "worker.log").write_text(stderr)
        try:
            envelope = json.loads(stdout)
        except ValueError as exc:
            code = "worker_crashed" if proc.returncode < 0 else "worker_protocol_error"
            raise AgentError(code, "Worker exited without a JSON envelope; check PythonAPI/server compatibility",
                             details={"exit_code": proc.returncode, "stderr": stderr[-2000:]}) from exc
        if not isinstance(envelope, dict) or type(envelope.get("ok")) is not bool:
            raise AgentError("worker_protocol_error", "Missing boolean ok")
        if not envelope["ok"]:
            error = envelope.get("error", {})
            if not isinstance(error, dict):
                raise AgentError("worker_protocol_error", "Invalid error envelope")
            raise AgentError(error.get("code", "worker_failed"), error.get("message", "Worker failed"),
                             details=error.get("details", {}))
        if proc.returncode != 0 or not isinstance(envelope.get("result"), dict):
            raise AgentError("worker_protocol_error", "Success envelope disagrees with exit code/result")
        result = envelope["result"]
        if output:
            result["artifact_dir"] = str(output)
            atomic_json(output / "result.json", result)
        return result
    except (KeyboardInterrupt, SystemExit):
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        raise
    except OSError as exc:
        error = AgentError("worker_unavailable", str(exc), 3)
        if output:
            atomic_json(output / "failure.json", error.as_dict())
        raise error from exc
    except AgentError as exc:
        if output:
            atomic_json(output / "failure.json", exc.as_dict())
        raise
    finally:
        if output:
            atomic_json(output / "request.json", request)


def server_identity(profile):
    """Linux local process provenance; never infer identity from server version alone."""
    host = profile.get("host", "127.0.0.1")
    if host not in ("127.0.0.1", "::1"):
        raise AgentError("identity_unverified", "v1 research requires a literal local address (127.0.0.1 or ::1)", 3)
    pid = profile.get("server_pid")
    if type(pid) is not int or pid <= 0:
        raise AgentError("identity_unverified", "Research requires server_pid", 3)
    base = Path("/proc") / str(pid)
    try:
        stat = (base / "stat").read_text().rsplit(")", 1)[1].split()
        started = stat[19]
        exe = (base / "exe").resolve(strict=True)
        sockets = set()
        for fd in (base / "fd").iterdir():
            try:
                target = os.readlink(fd)
            except FileNotFoundError:
                continue
            if target.startswith("socket:["):
                sockets.add(target[8:-1])
        owned = False
        for name in (("tcp",) if host == "127.0.0.1" else ("tcp6",)):
            path = base / "net" / name
            if not path.exists():
                continue
            for line in path.read_text().splitlines()[1:]:
                fields = line.split()
                encoded, port = fields[1].split(":")
                packed = bytes.fromhex(encoded)
                if sys.byteorder == "little":
                    packed = b"".join(packed[i:i+4][::-1] for i in range(0, len(packed), 4))
                address = socket.inet_ntop(socket.AF_INET if name == "tcp" else socket.AF_INET6, packed)
                wildcard = "0.0.0.0" if name == "tcp" else "::"
                if fields[3] == "0A" and address in (host, wildcard) and int(port, 16) == profile["port"] and fields[9] in sockets:
                    owned = True
        if not owned:
            raise AgentError("identity_unverified", "server_pid does not own the configured listening port", 3)
        digest = hashlib.sha256()
        with exe.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        return {"pid": pid, "start_ticks": started, "executable": str(exe),
                "executable_sha256": digest.hexdigest(), "port": profile["port"]}
    except OSError as exc:
        raise AgentError("identity_unverified", str(exc), 3) from exc


def run_operation(profile_path, operation, parameters):
    return invoke(load_profile(profile_path), operation, parameters)
