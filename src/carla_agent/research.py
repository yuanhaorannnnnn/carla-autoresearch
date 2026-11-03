"""Bounded, frozen RayCast parameter comparisons over the shared capture operation."""

import argparse
import contextlib
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import struct
import subprocess
import sys
import time
import uuid

from . import __version__, bridge
from .protocol import AgentError, atomic_json, load_profile, read_json

TERMINAL = {"COMPLETED", "FAILED", "INTERRUPTED", "STOPPED", "BUDGET_EXHAUSTED"}
SCOPE = ("tradeoff: conditional tick-to-sensor-callback latency on this local binary and workload, "
         "subject to finite points and the declared point floor; no geometric equivalence, "
         "physical accuracy, kernel timing, or source-build attribution is established")


def _error(message, code="invalid_plan", exit_code=2):
    raise AgentError(code, message, exit_code)


def _fields(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        _error("Expected exactly required fields " + ", ".join(required) + "; optional: " + ", ".join(optional))


def _number(value, name, minimum, maximum=None, integer=False):
    if type(value) not in ((int,) if integer else (int, float)) or (isinstance(value, float) and not math.isfinite(value)) or value < minimum or (maximum is not None and value > maximum):
        _error(name + " is outside its finite bounds")
    return value


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        _error(name + " must be a nonempty string")


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_plan(plan, base):
    _fields(plan, ("schema_version", "profile", "workload", "allowed_attributes", "candidates", "objective", "validity_contract", "comparison_policy", "confirmation", "budget"))
    if type(plan["schema_version"]) is not int or plan["schema_version"] != 1:
        _error("schema_version must be 1")
    _text(plan["profile"], "profile")
    plan = json.loads(json.dumps(plan, allow_nan=False))
    plan["profile"] = str((Path(base) / plan["profile"]).resolve())
    recipe = plan["workload"]
    _fields(recipe, ("map", "sensor_blueprint", "sensor_attributes", "frames", "warmup_frames", "fixed_delta_seconds"), ("vehicle_blueprint", "spawn_index"))
    _text(recipe["map"], "map")
    if recipe["sensor_blueprint"] != "sensor.lidar.ray_cast":
        _error("Research v1 supports explicit RayCast LiDAR only")
    _number(recipe["frames"], "frames", 1, 10000, True)
    _number(recipe["warmup_frames"], "warmup_frames", 0, 1000, True)
    _number(recipe["fixed_delta_seconds"], "fixed_delta_seconds", 0.001, 1)
    _number(recipe.get("spawn_index", 0), "spawn_index", 0, 100000, True)
    _text(recipe.get("vehicle_blueprint", "vehicle.tesla.model3"), "vehicle_blueprint")
    attrs = recipe["sensor_attributes"]
    if not isinstance(attrs, dict) or any(not isinstance(k, str) or not k or not isinstance(v, (str, int, float, bool)) or (isinstance(v, float) and not math.isfinite(v)) for k, v in attrs.items()):
        _error("sensor_attributes must contain named finite scalar attributes")
    allowed = plan["allowed_attributes"]
    if not isinstance(allowed, list) or not allowed or any(not isinstance(k, str) or k not in attrs for k in allowed) or len(set(allowed)) != len(allowed):
        _error("allowed_attributes must be unique attributes explicitly present in workload")
    candidates = plan["candidates"]
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 100:
        _error("candidates must contain 1..100 finite candidates")
    ids = set()
    for candidate in candidates:
        _fields(candidate, ("id", "sensor_attributes"))
        name, overrides = candidate["id"], candidate["sensor_attributes"]
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", name) or name in ids:
            _error("candidate IDs must be unique safe names")
        ids.add(name)
        if not isinstance(overrides, dict) or not overrides or set(overrides) - set(allowed):
            _error("candidate changes must be declared in allowed_attributes")
        if any(not isinstance(v, (str, int, float, bool)) or (isinstance(v, float) and not math.isfinite(v)) for v in overrides.values()):
            _error("candidate attributes must be finite scalars")
        if all(attrs[k] == v for k, v in overrides.items()):
            _error("candidate must change an allowed attribute")
    if plan["objective"] != {"metric": "tick_to_sensor_callback_ms", "unit": "ms", "direction": "minimize"}:
        _error("v1 objective is tick_to_sensor_callback_ms, ms, minimize")
    validity = plan["validity_contract"]
    _fields(validity, ("mode", "min_points_per_frame", "require_finite_points", "threshold_source"))
    if validity["mode"] != "tradeoff" or validity["require_finite_points"] is not True:
        _error("v1 requires tradeoff and finite points; semantic_preserving needs an implemented geometry oracle")
    _number(validity["min_points_per_frame"], "min_points_per_frame", 1, integer=True)
    _text(validity["threshold_source"], "validity threshold_source")
    policy = plan["comparison_policy"]
    _fields(policy, ("repeats", "min_improvement_fraction", "max_pair_relative_spread", "threshold_source"))
    _number(policy["repeats"], "repeats", 2, 100, True)
    _number(policy["min_improvement_fraction"], "min_improvement_fraction", 0, 1)
    _number(policy["max_pair_relative_spread"], "max_pair_relative_spread", 0, 2)
    _text(policy["threshold_source"], "comparison threshold_source")
    _fields(plan["confirmation"], ("repeats",))
    _number(plan["confirmation"]["repeats"], "confirmation repeats", 2, 100, True)
    budget = plan["budget"]
    _fields(budget, ("max_trials", "max_seconds", "trial_timeout_seconds"))
    _number(budget["max_trials"], "max_trials", 1, 100000, True)
    _number(budget["max_seconds"], "max_seconds", 0.01, 604800)
    _number(budget["trial_timeout_seconds"], "trial_timeout_seconds", 0.01, 86400)
    return plan


def validate_request(plan_path):
    source = Path(plan_path).resolve()
    plan = validate_plan(read_json(source), source.parent)
    profile = load_profile(plan["profile"])
    if profile["session_policy"] != "exclusive" or not profile.get("expected_server_version") or not profile.get("server_pid"):
        _error("Research requires exclusive policy, expected_server_version and server_pid", "invalid_profile")
    selection = len(plan["candidates"]) * plan["comparison_policy"]["repeats"] * 2
    confirmation = plan["confirmation"]["repeats"] * 2
    return {"valid": True, "validation_scope": "plan_and_profile_only", "simulator_checked": False,
            "plan": plan, "planned_selection_trials": selection, "planned_confirmation_trials": confirmation,
            "worst_case_trials": selection + confirmation,
            "budget_sufficient": plan["budget"]["max_trials"] >= selection + confirmation}


def plan_schema():
    """The plan object accepted by research start, with no implicit thresholds."""
    def obj(properties, required=None):
        return {"type": "object", "additionalProperties": False, "required": list(properties) if required is None else required, "properties": properties}
    scalar = {"type": ["string", "number", "boolean"]}
    attrs = {"type": "object", "additionalProperties": scalar}
    positive = {"type": "number", "minimum": 0.01}
    repeats = {"type": "integer", "minimum": 2, "maximum": 100}
    workload = obj({"map": {"type": "string", "minLength": 1}, "sensor_blueprint": {"const": "sensor.lidar.ray_cast"}, "sensor_attributes": attrs,
                    "frames": {"type": "integer", "minimum": 1, "maximum": 10000}, "warmup_frames": {"type": "integer", "minimum": 0, "maximum": 1000},
                    "fixed_delta_seconds": {"type": "number", "minimum": 0.001, "maximum": 1}, "vehicle_blueprint": {"type": "string"}, "spawn_index": {"type": "integer", "minimum": 0, "maximum": 100000}},
                   ["map", "sensor_blueprint", "sensor_attributes", "frames", "warmup_frames", "fixed_delta_seconds"])
    return obj({"schema_version": {"const": 1}, "profile": {"type": "string", "minLength": 1}, "workload": workload,
                "allowed_attributes": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string"}},
                "candidates": {"type": "array", "minItems": 1, "maxItems": 100, "items": obj({"id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"}, "sensor_attributes": attrs})},
                "objective": obj({"metric": {"const": "tick_to_sensor_callback_ms"}, "unit": {"const": "ms"}, "direction": {"const": "minimize"}}),
                "validity_contract": obj({"mode": {"const": "tradeoff"}, "min_points_per_frame": {"type": "integer", "minimum": 1}, "require_finite_points": {"const": True}, "threshold_source": {"type": "string", "minLength": 1}}),
                "comparison_policy": obj({"repeats": repeats, "min_improvement_fraction": {"type": "number", "minimum": 0, "maximum": 1}, "max_pair_relative_spread": {"type": "number", "minimum": 0, "maximum": 2}, "threshold_source": {"type": "string", "minLength": 1}}),
                "confirmation": obj({"repeats": repeats}), "budget": obj({"max_trials": {"type": "integer", "minimum": 1, "maximum": 100000}, "max_seconds": {**positive, "maximum": 604800}, "trial_timeout_seconds": {**positive, "maximum": 86400}})})


@contextlib.contextmanager
def _lock(run, wait=False):
    with (run / "writer.lock").open("a") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
        except BlockingIOError as exc:
            raise AgentError("run_busy", "Run has an active writer; use status", 5) from exc
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)



@contextlib.contextmanager
def _instance_lock(run, identity, probe=False):
    # Match the worker's per-user XDG state convention; host aliases share one verified process key.
    state_root = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))) / "carla-agent"
    if not state_root.is_absolute():
        _error("XDG_STATE_HOME must be absolute so all controllers share the same instance lock", "invalid_environment", 3)
    state_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = _digest({"pid": identity["pid"], "start_ticks": identity["start_ticks"]})
    path = state_root / ("research-" + key + ".lock")
    with path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise AgentError("run_busy", "Another research run owns this server process; use a dedicated instance", 5, {"lock_file": str(path)}) from exc
        try:
            if not probe:
                owner = {"schema_version": 1, "run_path": str(run), "controller": _process(os.getpid()), "server_identity": identity, "acquired_at": time.time()}
                lock.seek(0)
                lock.truncate()
                lock.write(json.dumps(owner, allow_nan=False) + "\n")
                lock.flush()
                os.fsync(lock.fileno())
                _event(run, "research_lock_acquired", lock_file=str(path), server_identity=identity)
            yield
        finally:
            if not probe:
                _event(run, "research_lock_released", lock_file=str(path))
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _process(pid):
    try:
        stat = (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
        return {"pid": pid, "start_ticks": stat[19], "pgrp": int(stat[2]), "session": int(stat[3]), "state": stat[0]}
    except (OSError, IndexError, ValueError):
        return None


def _alive(owner):
    current = _process(owner["pid"]) if owner else None
    return bool(current and current["state"] != "Z" and current["start_ticks"] == owner["start_ticks"])


def _orphaned(owner):
    if not owner or owner.get("session") != owner["pid"]:
        return False
    for path in Path("/proc").iterdir():
        if path.name.isdigit():
            proc = _process(int(path.name))
            if proc and proc["state"] != "Z" and proc["session"] == owner["pid"]:
                return True
    return False


def _save(run, state):
    atomic_json(run / "state.json", state)


def _event(run, kind, **values):
    with (run / "events.jsonl").open("a") as stream:
        stream.write(json.dumps({"time": time.time(), "event": kind, **values}, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _run_path(value):
    path = Path(value)
    if not path.is_absolute() or not (path / "manifest.json").is_file():
        _error("--run must be an absolute research run directory", "invalid_run")
    return path.resolve()


def _world_identity(profile):
    world = bridge.invoke(profile, "world.inspect", {})
    if type(world.get("episode_id")) is not int or not isinstance(world.get("map"), str):
        _error("World inspection cannot establish episode/map", "identity_unverified", 3)
    return {"episode_id": world["episode_id"], "map": world["map"]}


def _prepare(plan_path):
    source = Path(plan_path).resolve()
    plan = validate_plan(read_json(source), source.parent)
    profile = load_profile(plan["profile"])
    if profile["session_policy"] != "exclusive" or not profile.get("expected_server_version"):
        _error("Research requires exclusive policy and expected_server_version", "invalid_profile")
    identity = bridge.server_identity(profile)
    world_identity = _world_identity(profile)
    if world_identity["map"] != plan["workload"]["map"]:
        _error("Current map does not match frozen workload", "identity_changed", 5)
    run = Path(profile["output_root"]) / "runs" / uuid.uuid4().hex
    run.mkdir(parents=True, exist_ok=False)
    (run / "trials").mkdir()
    atomic_json(run / "plan.json", plan)
    atomic_json(run / "profile.json", profile)
    atomic_json(run / "manifest.json", {"schema_version": 1, "run_id": run.name, "created_at": time.time(), "plugin_version": __version__,
                "plan_source": str(source), "plan_sha256": _digest(plan), "profile_sha256": _digest(profile), "server_identity": identity, "world_identity": world_identity, "conclusion_scope": SCOPE})
    state = {"schema_version": 1, "run_id": run.name, "status": "CREATED", "execution_status": "not_started", "validity": "not_evaluated", "verdict": "not_evaluated",
             "worker": None, "active_seconds": 0.0, "trials": [], "selected_candidate": None, "comparisons": {}, "confirmation": None}
    _save(run, state)
    return run


def _frozen_inputs(run):
    manifest, frozen = read_json(run / "manifest.json"), read_json(run / "plan.json")
    plan = validate_plan(frozen, run)
    profile = load_profile(run / "profile.json")
    if manifest["run_id"] != run.name or _digest(plan) != manifest["plan_sha256"] or _digest(profile) != manifest["profile_sha256"]:
        _error("Frozen run inputs do not match manifest", "recovery_conflict", 5)
    return manifest, plan, profile


def _inputs(run):
    manifest, plan, profile = _frozen_inputs(run)
    if _digest(load_profile(plan["profile"])) != manifest["profile_sha256"]:
        _error("Source profile changed since start", "recovery_conflict", 5)
    original = Path(manifest["plan_source"])
    if _digest(validate_plan(read_json(original), original.parent)) != manifest["plan_sha256"]:
        _error("Source plan changed since start", "recovery_conflict", 5)
    if bridge.server_identity(profile) != manifest["server_identity"]:
        _error("Server PID/start/port/executable identity changed", "identity_changed", 5)
    if _world_identity(profile) != manifest["world_identity"]:
        _error("World episode/map changed", "identity_changed", 5)
    return manifest, plan, profile


def _specs(plan, stage="selection", candidate_id=None):
    result = []
    candidates = [c for c in plan["candidates"] if candidate_id is None or c["id"] == candidate_id]
    repeats = plan["comparison_policy"]["repeats"] if stage == "selection" else plan["confirmation"]["repeats"]
    for candidate in candidates:
        for pair in range(repeats):
            for arm in (("baseline", "candidate") if pair % 2 == 0 else ("candidate", "baseline")):
                recipe = json.loads(json.dumps(plan["workload"]))
                if arm == "candidate":
                    recipe["sensor_attributes"].update(candidate["sensor_attributes"])
                result.append({"key": f"{stage}:{candidate['id']}:{pair}:{arm}", "stage": stage, "candidate_id": candidate["id"], "pair": pair, "arm": arm, "recipe": recipe})
    return result


def _artifact_path(root, value):
    if not isinstance(value, str):
        _error("Capture is missing an artifact path", "invalid_capture", 4)
    path = (root / value).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        _error("Capture artifact is missing or outside its fresh trial directory", "invalid_capture", 4)
    return path


def _validate_capture(output, result, recipe, validity, expected_world):
    """Validate raw XYZI and timing facts, never accept an aggregate metrics file."""
    frames = result.get("frames")
    metadata = _artifact_path(output, result.get("metadata"))
    capture = read_json(metadata)
    if capture.get("status") != "complete" or capture.get("recipe") != recipe or capture.get("frames") != frames:
        _error("Capture metadata/result/recipe disagree", "invalid_capture", 4)
    if capture.get("session_identity") != expected_world or result.get("session_identity") != expected_world:
        _error("Capture world episode/map differs from the frozen run", "identity_changed", 5)
    cleanup = result.get("cleanup", {})
    if cleanup.get("closed") is not True or cleanup.get("settings_restored") is not True:
        _error("Capture cleanup is unverified", "cleanup_required", 5)
    if not isinstance(frames, list) or len(frames) != recipe["frames"]:
        _error("Capture has an incomplete frame set", "invalid_capture", 4)
    files, samples, points = {}, [], []
    previous, previous_timestamp = None, None
    for frame in frames:
        fid, stamp = frame.get("frame"), frame.get("sensor_timestamp")
        if type(fid) is not int or (previous is not None and fid != previous + 1):
            _error("Frame IDs must be unique and contiguous", "invalid_capture", 4)
        if type(stamp) not in (int, float) or not math.isfinite(stamp) or (previous_timestamp is not None and not math.isclose(stamp - previous_timestamp, recipe["fixed_delta_seconds"], rel_tol=1e-6, abs_tol=1e-6)):
            _error("Sensor timestamps do not follow the fixed step", "invalid_capture", 4)
        world = frame.get("world", {})
        timestamp = world.get("timestamp", {})
        if world.get("frame") != fid or type(timestamp.get("elapsed_seconds")) not in (int, float) or not math.isclose(timestamp["elapsed_seconds"], stamp, rel_tol=0, abs_tol=1e-6):
            _error("World and sensor frame/timestamp disagree", "invalid_capture", 4)
        start, received = frame.get("tick_start_monotonic_ns"), frame.get("receive_monotonic_ns")
        if type(start) is not int or type(received) is not int or not 0 <= start < received < 2 ** 63:
            _error("Invalid tick-to-callback monotonic timing", "invalid_capture", 4)
        samples.append((received - start) / 1e6)
        raw = _artifact_path(output, frame.get("file"))
        if str(raw) in files:
            _error("Frame artifact reused", "invalid_capture", 4)
        if frame.get("format") != "float32" or frame.get("fields") != ["x", "y", "z", "intensity"] or frame.get("byte_order") not in ("little", "big"):
            _error("Expected explicit raw float32 XYZI", "invalid_capture", 4)
        size = raw.stat().st_size
        count = frame.get("points")
        if type(count) is not int or count < validity["min_points_per_frame"] or size != count * 16 or frame.get("bytes") != size:
            _error("Point floor or raw byte count failed", "invalid_capture", 4)
        unpack = struct.Struct(("<" if frame["byte_order"] == "little" else ">") + "ffff")
        with raw.open("rb") as stream:
            for block in iter(lambda: stream.read(16 * 65536), b""):
                if any(not all(math.isfinite(v) for v in point) for point in unpack.iter_unpack(block)):
                    _error("Raw points contain nonfinite coordinates/intensity", "invalid_capture", 4)
        files[str(raw)] = _file_digest(raw)
        points.append(count)
        previous, previous_timestamp = fid, stamp
    files[str(metadata)] = _file_digest(metadata)
    return {"validity": "valid", "metric": statistics.median(samples), "metric_name": "tick_to_sensor_callback_ms", "unit": "ms", "frame_count": len(frames),
            "min_points": min(points), "artifacts": {str(Path(path).relative_to(output)): digest for path, digest in files.items()}}


def _verify_completed(run, state, plan, manifest):
    known = {s["key"]: s for s in _specs(plan)}
    for candidate in plan["candidates"]:
        known.update({s["key"]: s for s in _specs(plan, "confirmation", candidate["id"])})
    seen, seen_ids = set(), set()
    if state.get("run_id") != run.name or type(state.get("active_seconds")) not in (int, float) or not math.isfinite(state["active_seconds"]) or state["active_seconds"] < 0:
        _error("Invalid persisted run state", "recovery_conflict", 5)
    for trial in state["trials"]:
        if not isinstance(trial.get("id"), str) or not re.fullmatch(r"[0-9]{5,6}-[0-9a-f]{12}", trial["id"]):
            _error("Invalid trial directory identity", "recovery_conflict", 5)
        if trial["id"] in seen_ids:
            _error("Trial directory identity is reused", "recovery_conflict", 5)
        seen_ids.add(trial["id"])
        if trial.get("status") not in ("RUNNING", "COMPLETE", "FAILED", "INTERRUPTED"):
            _error("Unknown persisted trial status", "recovery_conflict", 5)
        spec = known.get(trial.get("key"))
        if spec is None or any(trial.get(k) != spec[k] for k in ("stage", "candidate_id", "pair", "arm", "recipe")):
            _error("Trial does not match frozen schedule", "recovery_conflict", 5)
        if trial["status"] != "COMPLETE":
            continue
        if trial["key"] in seen:
            _error("Duplicate completed trial for one scheduled arm", "recovery_conflict", 5)
        seen.add(trial["key"])
        trial_dir = run / "trials" / trial["id"]
        saved = read_json(trial_dir / "trial.json")
        if saved != trial or trial.get("server_identity") != manifest["server_identity"]:
            _error("Trial completion disagrees with evidence", "recovery_conflict", 5)
        if trial["summary"]["validity"] == "valid":
            output = trial_dir / "capture"
            for path, digest in trial["summary"]["artifacts"].items():
                if _file_digest(_artifact_path(output, path)) != digest:
                    _error("Completed trial artifact changed", "recovery_conflict", 5)
            result = read_json(output / "result.json")
            if _validate_capture(output, result, trial["recipe"], plan["validity_contract"], manifest["world_identity"]) != trial["summary"]:
                _error("Completed trial metrics do not match raw evidence", "recovery_conflict", 5)


def _comparison(state, plan, candidate_id, stage):
    trials = {t["key"]: t for t in state["trials"] if t["status"] == "COMPLETE"}
    specs = _specs(plan, stage, candidate_id)
    if any(s["key"] not in trials for s in specs):
        return {"verdict": "not_evaluated", "validity": "incomplete", "reason": "independent pairs are incomplete"}
    if any(trials[s["key"]]["summary"]["validity"] != "valid" for s in specs):
        return {"verdict": "not_evaluated", "validity": "invalid", "reason": "at least one paired trial failed validity"}
    by_pair = {}
    for spec in specs:
        by_pair.setdefault(spec["pair"], {})[spec["arm"]] = trials[spec["key"]]["summary"]["metric"]
    fractions = [(v["baseline"] - v["candidate"]) / v["baseline"] for v in by_pair.values()]
    median = statistics.median(fractions)
    spread = max(fractions) - min(fractions)
    policy = plan["comparison_policy"]
    if spread > policy["max_pair_relative_spread"]:
        verdict, reason = "inconclusive", "pair-relative spread exceeds frozen noise bound"
    elif median <= 0 or median < policy["min_improvement_fraction"]:
        verdict, reason = "discard", "improvement does not meet the frozen threshold"
    else:
        verdict, reason = "eligible", "paired improvement meets the frozen threshold"
    return {"verdict": verdict, "validity": "valid", "reason": reason, "pair_improvement_fractions": fractions, "median_improvement_fraction": median, "pair_relative_spread": spread}


def _decision(state, plan):
    comparisons = {c["id"]: _comparison(state, plan, c["id"], "selection") for c in plan["candidates"]}
    eligible = [k for k, v in comparisons.items() if v["verdict"] == "eligible"]
    selected = min(eligible, key=lambda k: (-comparisons[k]["median_improvement_fraction"], k)) if eligible else None
    confirmation = _comparison(state, plan, selected, "confirmation") if selected else None
    values = list(comparisons.values())
    validity = "valid" if all(c["validity"] == "valid" for c in values) else "invalid"
    verdict = "not_evaluated"
    if confirmation:
        validity = confirmation["validity"]
        verdict = "keep" if confirmation["verdict"] == "eligible" else confirmation["verdict"]
    elif all(c["verdict"] == "discard" for c in values):
        verdict = "discard"
    elif any(c["verdict"] == "inconclusive" for c in values):
        verdict = "inconclusive"
    return {"comparisons": comparisons, "selected_candidate": selected, "confirmation": confirmation, "validity": validity, "verdict": verdict}


def _verify_final(state, plan):
    decision = _decision(state, plan)
    if any(c["validity"] == "incomplete" for c in decision["comparisons"].values()) or (decision["confirmation"] and decision["confirmation"]["validity"] == "incomplete"):
        _error("Completed status lacks all frozen independent pairs", "recovery_conflict", 5)
    if any(state.get(k) != v for k, v in decision.items()):
        _error("Persisted verdict differs from raw-evidence comparison", "recovery_conflict", 5)


def _finish(run, state, status, error=None):
    state["status"] = status
    state["execution_status"] = "complete" if status == "COMPLETED" else status.lower()
    if error:
        state["error"] = error.as_dict()
    _save(run, state)
    _event(run, "finished", status=status, verdict=state["verdict"])
    report = _report(run, state)
    atomic_json(run / "report.json", report)
    lines = ["# CARLA parameter comparison", "", f"Execution: {status}", f"Validity: {state['validity']}", f"Verdict: {state['verdict']}", "", SCOPE, "", "Independent paired trials are the repetition unit. Frames within a trial are not independent repeats.",
             "The deadline bounds capture execution; worker cleanup can add up to 10 seconds.", "", "```json", json.dumps(report, indent=2, allow_nan=False), "```", ""]
    (run / "report.md").write_text("\n".join(lines))
    return report


def _report(run, state):
    return {"run_id": run.name, "run_path": str(run), "execution_status": state["execution_status"], "status": state["status"], "validity": state["validity"], "verdict": state["verdict"],
            "selected_candidate": state["selected_candidate"], "comparisons": state["comparisons"], "confirmation": state["confirmation"], "trial_count": len(state["trials"]),
            "active_seconds": state["active_seconds"], "conclusion_scope": SCOPE, "error": state.get("error"),
            "artifact_paths": {"manifest": str(run / "manifest.json"), "state": str(run / "state.json"), "report_json": str(run / "report.json"), "report_markdown": str(run / "report.md")}}


def _recover_trials(run, state, profile, deadline):
    for trial in state["trials"]:
        if trial["status"] == "COMPLETE":
            continue
        metadata = run / "trials" / trial["id"] / "capture" / "capture.json"
        if trial.get("recovery_cleanup_complete"):
            continue
        if metadata.exists():
            capture = read_json(metadata)
            if capture.get("recipe") != trial["recipe"]:
                _error("Interrupted capture recipe changed", "recovery_conflict", 5)
            if not capture.get("cleanup", {}).get("closed"):
                session = capture.get("session_id")
                if not session:
                    _error("Interrupted capture ownership cannot be proven; inspect instance lease", "cleanup_required", 5)
                bridge.invoke(profile, "session.close", {"session_id": session}, timeout_seconds=max(0.01, deadline - time.monotonic()))
        elif trial["status"] in ("RUNNING", "INTERRUPTED", "FAILED"):
            _error("Missing capture metadata; inspect instance lease before recovery", "cleanup_required", 5)
        trial["status"] = "INTERRUPTED"
        trial["recovery_cleanup_complete"] = True
        atomic_json(run / "trials" / trial["id"] / "trial.json", trial)
    _save(run, state)


def _execute(run, recovering=False, wait_for_launch=False):
    # The spawned child waits until its parent has persisted its PID and released the launch lock.
    with _lock(run, wait=wait_for_launch):
        state = read_json(run / "state.json")
        if wait_for_launch and (not state.get("worker") or state["worker"]["pid"] != os.getpid() or state["worker"]["start_ticks"] != _process(os.getpid())["start_ticks"]):
            _error("This worker does not own the launch record", "run_busy", 5)
        manifest, plan, profile = _inputs(run)
        _verify_completed(run, state, plan, manifest)
        with _instance_lock(run, manifest["server_identity"]):
            state["worker"] = _process(os.getpid())
            state["status"], state["execution_status"] = "RUNNING", "running"
            state.pop("error", None)
            _save(run, state)
            _event(run, "running", recovering=recovering)
            started = time.monotonic()
            prior_seconds = state["active_seconds"]
            if recovering:
                for trial in state["trials"]:
                    if trial["status"] == "RUNNING":
                        prior_seconds += min(max(0, time.time() - trial["started_at"]), plan["budget"]["trial_timeout_seconds"] + 10)
                state["active_seconds"] = prior_seconds
            deadline = started + max(0, plan["budget"]["max_seconds"] - prior_seconds)
            status, failure = "COMPLETED", None
            try:
                if recovering:
                    _recover_trials(run, state, profile, deadline)
                stages = [("selection", None)]
                for stage, selected in stages:
                    for spec in _specs(plan, stage, selected):
                        if any(t["key"] == spec["key"] and t["status"] == "COMPLETE" for t in state["trials"]):
                            continue
                        if (run / "stop-request.json").exists():
                            status = "STOPPED"
                            break
                        remaining = deadline - time.monotonic()
                        if len(state["trials"]) >= plan["budget"]["max_trials"] or remaining <= 0:
                            status = "BUDGET_EXHAUSTED"
                            break
                        if bridge.server_identity(profile) != manifest["server_identity"]:
                            _error("Server identity changed before trial", "identity_changed", 5)
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            status = "BUDGET_EXHAUSTED"
                            break
                        trial = {**spec, "id": f"{len(state['trials']) + 1:05d}-{uuid.uuid4().hex[:12]}", "status": "RUNNING", "server_identity": manifest["server_identity"], "started_at": time.time()}
                        state["trials"].append(trial)
                        trial_dir = run / "trials" / trial["id"]
                        trial_dir.mkdir()
                        atomic_json(trial_dir / "trial.json", trial)
                        state["active_seconds"] = prior_seconds + time.monotonic() - started
                        _save(run, state)
                        _event(run, "trial_started", trial_id=trial["id"], key=trial["key"])
                        try:
                            output = trial_dir / "capture"
                            result = bridge.invoke(profile, "capture.run", {"recipe": spec["recipe"]}, output_dir=output,
                                                   timeout_seconds=min(remaining, plan["budget"]["trial_timeout_seconds"]))
                            if bridge.server_identity(profile) != manifest["server_identity"]:
                                _error("Server identity changed during trial", "identity_changed", 5)
                            try:
                                summary = _validate_capture(output, result, spec["recipe"], plan["validity_contract"], manifest["world_identity"])
                            except AgentError as exc:
                                if exc.code != "invalid_capture":
                                    raise
                                summary = {"validity": "invalid", "error": exc.as_dict()}
                            trial.update(status="COMPLETE", summary=summary, finished_at=time.time())
                        except BaseException as exc:
                            trial["status"] = "INTERRUPTED" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "FAILED"
                            trial["error"] = exc.as_dict() if isinstance(exc, AgentError) else {"code": "interrupted", "message": str(exc)}
                            raise
                        finally:
                            atomic_json(trial_dir / "trial.json", trial)
                            state["active_seconds"] = prior_seconds + time.monotonic() - started
                            _save(run, state)
                        if (run / "stop-request.json").exists():
                            status = "STOPPED"
                            break
                        if time.monotonic() > deadline:
                            status = "BUDGET_EXHAUSTED"
                            break
                    if status != "COMPLETED":
                        break
                    if stage == "selection":
                        state["comparisons"] = {c["id"]: _comparison(state, plan, c["id"], "selection") for c in plan["candidates"]}
                        eligible = [k for k, v in state["comparisons"].items() if v["verdict"] == "eligible"]
                        if eligible:
                            selected = min(eligible, key=lambda k: (-state["comparisons"][k]["median_improvement_fraction"], k))
                            state["selected_candidate"] = selected
                            stages.append(("confirmation", selected))
                        _save(run, state)
                    else:
                        state["confirmation"] = _comparison(state, plan, selected, "confirmation")
                if status == "COMPLETED":
                    if bridge.server_identity(profile) != manifest["server_identity"] or _world_identity(profile) != manifest["world_identity"]:
                        _error("Server/world identity changed before final comparison", "identity_changed", 5)
                    state.update(_decision(state, plan))
                    _verify_final(state, plan)
            except (KeyboardInterrupt, SystemExit):
                status = "INTERRUPTED"
            except AgentError as exc:
                status, failure = "FAILED", exc
            except (OSError, ValueError, KeyError, TypeError) as exc:
                status, failure = "FAILED", AgentError("research_failed", str(exc))
            state["active_seconds"] = prior_seconds + time.monotonic() - started
            if status != "COMPLETED":
                state["verdict"] = "not_evaluated"
            return _finish(run, state, status, failure)


def _launch(run, foreground=False, recovering=False):
    with _lock(run):
        state = read_json(run / "state.json")
        if recovering:
            if _alive(state.get("worker")) or _orphaned(state.get("worker")):
                _error("Controller or an owned execution process is still alive; inspect status", "run_busy", 5)
            manifest, plan, profile = _inputs(run)
            _verify_completed(run, state, plan, manifest)
            if state["status"] == "COMPLETED":
                _error("Completed runs cannot be resumed", "recovery_conflict", 5)
            if (run / "stop-request.json").exists():
                (run / "stop-request.json").unlink()
        identity = read_json(run / "manifest.json")["server_identity"]
        with _instance_lock(run, identity, probe=True):
            command = [sys.executable, "-m", "carla_agent.research", "--worker", str(run)]
            if recovering:
                command.append("--recovering")
            env = os.environ.copy()
            source = str(Path(__file__).resolve().parent.parent)
            env["PYTHONPATH"] = source + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            try:
                with (run / "controller.log").open("a") as log:
                    process = subprocess.Popen(command, cwd=str(run), env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
            except OSError as exc:
                raise AgentError("controller_unavailable", str(exc), 3) from exc
            state["worker"] = _process(process.pid)
            state["status"], state["execution_status"] = "STARTING", "starting"
            _save(run, state)

    if foreground:
        try:
            process.wait()
        except KeyboardInterrupt:
            atomic_json(run / "stop-request.json", {"run_id": run.name, "requested_at": time.time()})
            raise
    return status(run)


def status(run):
    run = _run_path(run)
    state = read_json(run / "state.json")
    if state["status"] == "COMPLETED":
        manifest, plan, profile = _frozen_inputs(run)
        _verify_completed(run, state, plan, manifest)
        _verify_final(state, plan)
    report = _report(run, state)
    report["controller_alive"] = _alive(state.get("worker"))
    if state["status"] not in TERMINAL and not report["controller_alive"]:
        report["status"] = "INTERRUPTED"
        report["execution_status"] = "interrupted"
        report["verdict"] = "not_evaluated"
        report["recovery_required"] = True
    return report


def compare(run):
    run = _run_path(run)
    state = read_json(run / "state.json")
    if state["status"] not in TERMINAL:
        _error("Comparison requires a terminal run", "run_busy", 5)
    try:
        lock = (run / "writer.lock").open("r")
    except OSError as exc:
        raise AgentError("invalid_run", "Existing writer.lock is required for read-only comparison", 2) from exc
    with lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise AgentError("run_busy", "Run has an active writer; compare after it finishes", 5) from exc
        try:
            state = read_json(run / "state.json")
            if state["status"] not in TERMINAL:
                _error("Comparison requires a terminal run", "run_busy", 5)
            manifest, plan, _ = _frozen_inputs(run)
            _verify_completed(run, state, plan, manifest)
            if state["status"] == "COMPLETED":
                _verify_final(state, plan)
            decision = _decision(state, plan)
            incomplete = state["status"] != "COMPLETED"
            if incomplete:
                decision.update(validity="incomplete", verdict="not_evaluated")
            return dict(_report(run, dict(state, **decision)), read_only=True, incomplete=incomplete)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def dispatch(args):
    if args.action == "validate":
        return validate_request(args.plan)
    if args.action == "start":
        return _launch(_prepare(args.plan), args.foreground)
    run = _run_path(args.run)
    if args.action == "compare":
        return compare(run)
    if args.action in ("status", "report"):
        return status(run)
    if args.action == "stop":
        atomic_json(run / "stop-request.json", {"run_id": run.name, "requested_at": time.time()})
        return {**status(run), "stop_requested": True, "stop_policy": "finish the current bounded trial and cleanup; do not start another"}
    if args.action == "resume":
        if not args.retry_interrupted:
            _error("resume requires --retry-interrupted; unfinished trials restart in fresh directories", "retry_required")
        return _launch(run, args.foreground, recovering=True)
    _error("Unknown research action")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", required=True)
    parser.add_argument("--recovering", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = _execute(_run_path(args.worker), args.recovering, wait_for_launch=True)
        return 0 if report["status"] == "COMPLETED" else 4
    except AgentError as exc:
        # Startup/preflight failures must leave a terminal state, including instance contention.
        try:
            run = _run_path(args.worker)
            with _lock(run):
                state = read_json(run / "state.json")
                owner = state.get("worker")
                if owner and owner["pid"] == os.getpid() and owner["start_ticks"] == _process(os.getpid())["start_ticks"]:
                    state["verdict"] = "not_evaluated"
                    _finish(run, state, "FAILED", exc)
        except (AgentError, OSError, ValueError, KeyError):
            pass
        print(json.dumps({"error": exc.as_dict()}), file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
