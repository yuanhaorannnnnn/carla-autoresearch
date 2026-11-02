"""Isolated Python >=3.8 CARLA worker; stdout is a single JSON response."""
import contextlib
import fcntl
import importlib
import json
import math
import os
from pathlib import Path
import queue
import signal
import sys
import time
import uuid


class WorkerError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code, self.details = code, details or {}


def fail(code, message, **details):
    raise WorkerError(code, message, details)


def number(value, name, minimum, maximum, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or (isinstance(value, float) and not math.isfinite(value)):
        fail("invalid_parameters", name + " must be a finite number")
    if integer and not isinstance(value, int):
        fail("invalid_parameters", name + " must be an integer")
    if not minimum <= value <= maximum:
        fail("invalid_parameters", name + " is out of bounds", minimum=minimum, maximum=maximum)
    return value


def fields(value, allowed, required=()):
    if not isinstance(value, dict):
        fail("invalid_parameters", "parameters must be an object")
    extra, missing = set(value) - set(allowed), set(required) - set(value)
    if extra or missing:
        fail("invalid_parameters", "unknown or missing fields", unknown=sorted(extra), missing=sorted(missing))


def string(value, name):
    if not isinstance(value, str) or not value:
        fail("invalid_parameters", name + " must be a nonempty string")
    return value


def write_json(path, data):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x") as stream:
            json.dump(data, stream, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(str(temporary), str(path))
    finally:
        if temporary.exists():
            temporary.unlink()


def settings_dict(settings):
    result = {}
    for key in dir(settings):
        if key.startswith("_"):
            continue
        value = getattr(settings, key)
        if value is None or isinstance(value, (bool, int, float, str)):
            result[key] = value
    return result


def snapshot_dict(snapshot):
    timestamp = snapshot.timestamp
    return {"frame": snapshot.frame, "timestamp": {
        name: getattr(timestamp, name) for name in
        ("elapsed_seconds", "delta_seconds", "platform_timestamp") if hasattr(timestamp, name)}}


def capability(obj, name):
    try:
        return getattr(obj, name)
    except AttributeError:
        fail("unsupported_capability", "CARLA API is unavailable", capability=name)


def method(obj, name):
    value = capability(obj, name)
    if not callable(value):
        fail("unsupported_capability", "CARLA API is not callable", capability=name)
    return value


def vector_dict(vector, keys=("x", "y", "z")):
    return {key: capability(vector, key) for key in keys}


def transform_dict(transform):
    return {"location": vector_dict(capability(transform, "location")),
            "rotation": vector_dict(capability(transform, "rotation"), ("pitch", "yaw", "roll"))}


def blueprint_dict(blueprint):
    return {"id": blueprint.id, "attributes": {
        attribute.id: {"value": str(attribute), "modifiable": attribute.is_modifiable,
                       "recommended_values": list(attribute.recommended_values)}
        for attribute in blueprint}}


class Worker:
    def __init__(self, profile):
        if not isinstance(profile, dict):
            fail("invalid_profile", "profile must be an object")
        self.profile = profile
        self.host = profile.get("host", "127.0.0.1")
        self.port = number(profile.get("port", 2000), "port", 1, 65535, True)
        self.timeout = number(profile.get("timeout_seconds", 10), "timeout_seconds", 0.01, 120)
        try:
            self.carla = importlib.import_module("carla")
        except ImportError as exc:
            fail("carla_import_failed", str(exc), python=sys.executable)
        self.client = self.carla.Client(self.host, self.port)
        self.client.set_timeout(self.timeout)
        self.world = None

    def connect(self):
        client_version, server_version = self.client.get_client_version(), self.client.get_server_version()
        if client_version != server_version:
            fail("client_server_version_mismatch", "client and server versions differ; get_world refused", client_version=client_version, server_version=server_version)
        self.world = self.client.get_world()
        return self.world

    def root(self):
        root = Path(string(self.profile.get("output_root"), "output_root"))
        if not root.is_absolute():
            fail("invalid_profile", "output_root must be absolute")
        directory = root / ".carla-agent"
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @contextlib.contextmanager
    def locked(self, session_id=None):
        # The flock covers each mutation; the JSON lease survives worker exit.
        import hashlib
        self.directory = self.root()
        if session_id is not None:
            session_path = self.session_path(session_id)
            if not session_path.exists():
                fail("session_not_found", "session does not exist")
            lock_identity = json.loads(session_path.read_text())["identity"]
        else:
            lock_identity = self.identity()
        self.lock_identity = lock_identity
        # The server's random episode ID is shared by all DNS/IP aliases.
        key = hashlib.sha256(json.dumps(lock_identity, sort_keys=True).encode()).hexdigest()
        state = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))) / "carla-agent"
        state.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lease_path = state / (key + ".lease.json")
        with (state / (key + ".lock")).open("a") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                actual = self.identity()
                if actual != lock_identity:
                    fail("episode_changed", "world changed before acquiring episode lease", expected=lock_identity, actual=actual)
                # Preserve and respect leases written before the identity-key
                # migration; only the matching session may later remove one.
                for lease_path in state.glob("*.lease.json"):
                    if lease_path == self.lease_path:
                        continue
                    lease = json.loads(lease_path.read_text())
                    if session_id is not None and lease.get("session_id") == session_id:
                        self.lease_path = lease_path
                        continue
                    lease_identity = lease.get("identity")
                    if lease_identity is None and lease.get("session_path"):
                        old_path = Path(lease["session_path"])
                        if old_path.is_file():
                            lease_identity = json.loads(old_path.read_text()).get("identity")
                    if lease_identity == lock_identity:
                        fail("instance_busy", "episode already has a session lease", lease=lease)
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def require_mutation(self):
        if self.profile.get("session_policy") != "exclusive":
            fail("policy_denied", "mutation requires session_policy=exclusive")
        expected = self.profile.get("expected_server_version")
        if not expected:
            fail("version_required", "mutation requires expected_server_version")
        actual = self.client.get_server_version()
        if actual != expected:
            fail("version_mismatch", "server version does not match profile", expected=expected, actual=actual)

    def identity(self):
        self.world = self.client.get_world()
        return {"episode_id": self.world.id, "map": self.world.get_map().name}

    def session_path(self, session_id):
        if not isinstance(session_id, str) or len(session_id) != 32 or any(c not in "0123456789abcdef" for c in session_id):
            fail("invalid_parameters", "invalid session_id")
        return self.directory / (session_id + ".json")

    def load_session(self, session_id, closing=False):
        path = self.session_path(session_id)
        if not path.exists():
            fail("session_not_found", "session does not exist")
        session = json.loads(path.read_text())
        if session.get("closed"):
            fail("session_closed", "session is already closed")
        if not self.lease_path.exists() or json.loads(self.lease_path.read_text()).get("session_id") != session_id:
            fail("ownership_lost", "instance lease does not belong to this session")
        if not closing and session["lease_expires_at"] < time.time():
            fail("lease_expired", "session lease expired; explicitly close it before opening another")
        actual = self.identity()
        if actual != session["identity"]:
            fail("episode_changed", "world identity changed; no cleanup or restoration attempted", expected=session["identity"], actual=actual)
        if self.client.get_server_version() != session["server_version"]:
            fail("version_mismatch", "server version changed during session")
        if not closing:
            settings = self.world.get_settings()
            if any(getattr(settings, name) != value for name, value in session["applied_settings"].items()):
                fail("settings_changed", "world settings no longer match session")
        return session

    def save_session(self, session):
        session["lease_expires_at"] = time.time() + 3600
        write_json(self.session_path(session["session_id"]), session)
        write_json(self.lease_path, {"session_id": session["session_id"], "expires_at": session["lease_expires_at"], "identity": session["identity"], "session_path": str(self.session_path(session["session_id"]))})

    def open_session(self, parameters):
        fields(parameters, ("fixed_delta_seconds", "expected_map"))
        delta = number(parameters.get("fixed_delta_seconds", 0.05), "fixed_delta_seconds", 0.001, 1)
        identity = self.identity()
        if identity != self.lock_identity:
            fail("episode_changed", "world changed after acquiring episode lease", expected=self.lock_identity, actual=identity)
        if parameters.get("expected_map") and parameters["expected_map"] != identity["map"]:
            fail("map_mismatch", "current map does not match expected_map", actual=identity["map"])
        if self.lease_path.exists():
            fail("instance_busy", "instance has an existing session; close it explicitly", lease=json.loads(self.lease_path.read_text()))
        original = settings_dict(self.world.get_settings())
        session = {"session_id": uuid.uuid4().hex, "host": self.host, "port": self.port,
                   "identity": identity, "server_version": self.client.get_server_version(),
                   "original_settings": original, "applied_settings": {"synchronous_mode": True, "fixed_delta_seconds": delta},
                   "owned_actors": [], "closed": False}
        self.save_session(session)
        try:
            settings = self.world.get_settings()
            settings.synchronous_mode, settings.fixed_delta_seconds = True, delta
            self.world.apply_settings(settings)
        except BaseException as exc:
            # Keep the lease and original settings: a timed-out RPC may have applied.
            fail("settings_apply_failed", str(exc), session_id=session["session_id"], original_settings=original)
        return {"session_id": session["session_id"], "identity": identity,
                "lease_expires_at": session["lease_expires_at"], "original_settings": original}

    def owned_actor(self, session, actor_id):
        number(actor_id, "actor_id", 1, 2 ** 32 - 1, True)
        record = next((record for record in session["owned_actors"] if record["id"] == actor_id), None)
        if record is None:
            fail("actor_not_owned", "actor is not owned by this session", actor_id=actor_id)
        self.load_session(session["session_id"])
        actor = self.world.get_actor(actor_id)
        if actor is not None and actor.type_id != record["type_id"]:
            fail("ownership_lost", "owned actor identity changed", actor_id=actor_id)
        return actor

    def destroy(self, session, actor_id, closing=False):
        if closing:
            self.load_session(session["session_id"], closing=True)
            record = next((r for r in session["owned_actors"] if r["id"] == actor_id), None)
            if record is None:
                fail("actor_not_owned", "actor is not owned by this session")
            actor = self.world.get_actor(actor_id)
            if actor is not None and actor.type_id != record["type_id"]:
                fail("ownership_lost", "owned actor identity changed")
        else:
            actor = self.owned_actor(session, actor_id)
        if actor is not None:
            if getattr(actor, "is_listening", False):
                actor.stop()
            if not actor.destroy():
                fail("destroy_failed", "CARLA refused actor destruction", actor_id=actor_id)
        session["owned_actors"] = [record for record in session["owned_actors"] if record["id"] != actor_id]
        self.save_session(session)

    def close_session(self, session_id):
        session = self.load_session(session_id, closing=True)
        errors = []
        for record in reversed(list(session["owned_actors"])):
            try:
                self.destroy(session, record["id"], closing=True)
            except Exception as exc:
                errors.append({"actor_id": record["id"], "message": str(exc)})
        self.load_session(session_id, closing=True)
        settings = self.world.get_settings()
        current = {name: getattr(settings, name) for name in session["applied_settings"]}
        original = {name: session["original_settings"][name] for name in session["applied_settings"]}
        if current != session["applied_settings"] and current != original:
            fail("settings_changed", "settings no longer match session; restoration refused", cleanup_errors=errors)
        if errors:
            fail("cleanup_failed", "owned actors remain; lease retained", cleanup_errors=errors)
        for name in session["applied_settings"]:
            setattr(settings, name, session["original_settings"][name])
        self.world.apply_settings(settings)
        session["closed"] = True
        write_json(self.session_path(session_id), session)
        self.lease_path.unlink()
        return {"session_id": session_id, "closed": True, "settings_restored": True}

    def blueprint(self, blueprint_id, attributes=None):
        blueprint_id = string(blueprint_id, "blueprint")
        try:
            blueprint = self.world.get_blueprint_library().find(blueprint_id)
        except (RuntimeError, IndexError):
            fail("blueprint_not_found", "blueprint does not exist", blueprint=blueprint_id)
        if blueprint is None:
            fail("blueprint_not_found", "blueprint does not exist", blueprint=blueprint_id)
        if attributes is not None:
            if not isinstance(attributes, dict):
                fail("invalid_parameters", "attributes must be an object")
            for key, value in attributes.items():
                if not isinstance(key, str) or not blueprint.has_attribute(key):
                    fail("invalid_attribute", "unknown blueprint attribute", attribute=key)
                attribute = blueprint.get_attribute(key)
                if not attribute.is_modifiable or not isinstance(value, (str, int, float, bool)):
                    fail("invalid_attribute", "attribute is not modifiable or value is invalid", attribute=key)
                if isinstance(value, float) and not math.isfinite(value):
                    fail("invalid_attribute", "attribute must be finite", attribute=key)
                try:
                    blueprint.set_attribute(key, str(value).lower() if isinstance(value, bool) else str(value))
                except (RuntimeError, ValueError) as exc:
                    fail("invalid_attribute", str(exc), attribute=key)
        return blueprint

    def remember_actor(self, session, actor):
        session["owned_actors"].append({"id": actor.id, "type_id": actor.type_id})
        try:
            self.save_session(session)
        except BaseException:
            # The newly returned actor is ours even if disk persistence failed.
            if self.identity() == session["identity"]:
                actor.destroy()
            raise
        return {"actor_id": actor.id, "type_id": actor.type_id, "attributes": dict(actor.attributes)}

    def spawn(self, session, parameters):
        blueprint = self.blueprint(parameters["blueprint"])
        if not blueprint.id.startswith("vehicle."):
            fail("invalid_blueprint", "actors.spawn requires a vehicle blueprint")
        index = number(parameters.get("spawn_index", 0), "spawn_index", 0, 100000, True)
        points = self.world.get_map().get_spawn_points()
        if index >= len(points):
            fail("invalid_parameters", "spawn_index exceeds available spawn points", count=len(points))
        if blueprint.has_attribute("role_name"):
            blueprint.set_attribute("role_name", "carla-agent:" + session["session_id"])
        actor = self.world.try_spawn_actor(blueprint, points[index])
        if actor is None:
            fail("spawn_failed", "spawn point is occupied or blueprint cannot spawn")
        return self.remember_actor(session, actor)

    def attach(self, session, parameters):
        if parameters["blueprint"] == "sensor.lidar.ray_cast_mems" and self.profile.get("capability_profile", "standard") != "custom-mems":
            fail("capability_denied", "sprint42 MEMS attachment requires capability_profile=custom-mems")
        parent = self.owned_actor(session, parameters["parent_id"])
        if parent is None:
            fail("actor_missing", "owned parent no longer exists")
        blueprint = self.blueprint(parameters["blueprint"], parameters.get("attributes", {}))
        if not blueprint.id.startswith("sensor."):
            fail("invalid_blueprint", "sensors.attach requires a sensor blueprint")
        if blueprint.has_attribute("role_name"):
            if "role_name" in parameters.get("attributes", {}):
                role = str(blueprint.get_attribute("role_name"))
                for record in session["owned_actors"]:
                    if record["type_id"] == blueprint.id:
                        existing = self.owned_actor(session, record["id"])
                        if existing is not None and existing.attributes.get("role_name") == role:
                            fail("sensor_role_in_use", "owned sensor of this type already uses role_name", role_name=role)
            else:
                blueprint.set_attribute("role_name", session["session_id"] + "-" + uuid.uuid4().hex)
        transform = parameters.get("transform", {"z": 2.5})
        fields(transform, ("x", "y", "z", "pitch", "yaw", "roll"))
        values = {key: number(transform.get(key, 0), key, -100000, 100000) for key in ("x", "y", "z", "pitch", "yaw", "roll")}
        placement = self.carla.Transform(self.carla.Location(**{key: values[key] for key in ("x", "y", "z")}),
                                         self.carla.Rotation(**{key: values[key] for key in ("pitch", "yaw", "roll")}))
        actor = self.world.spawn_actor(blueprint, placement, attach_to=parent)
        return self.remember_actor(session, actor)

    def tick(self, session, frames):
        number(frames, "frames", 1, 10000, True)
        result = []
        for _ in range(frames):
            self.load_session(session["session_id"])
            result.append(self.world.tick(self.timeout))
        self.save_session(session)
        return {"frames": result}

    def control(self, session, parameters):
        values = parameters["control"]
        fields(values, ("throttle", "steer", "brake", "hand_brake", "reverse", "manual_gear_shift", "gear"))
        control = {key: number(values.get(key, 0), key, minimum, maximum)
                   for key, minimum, maximum in (("throttle", 0, 1), ("steer", -1, 1), ("brake", 0, 1))}
        for key in ("hand_brake", "reverse", "manual_gear_shift"):
            value = values.get(key, False)
            if type(value) is not bool:
                fail("invalid_parameters", key + " must be a boolean")
            control[key] = value
        control["gear"] = number(values.get("gear", 0), "gear", -1, 2 ** 31 - 1, True)
        actor = self.owned_actor(session, parameters["actor_id"])
        if actor is None:
            fail("actor_missing", "owned actor no longer exists")
        if not actor.type_id.startswith("vehicle."):
            fail("invalid_actor", "vehicle.control requires an owned vehicle")
        apply_control = method(actor, "apply_control")
        native = method(self.carla, "VehicleControl")()
        for key, value in control.items():
            capability(native, key)
            setattr(native, key, value)
        self.load_session(session["session_id"])
        apply_control(native)
        self.save_session(session)
        return {"actor_id": actor.id, "control": control, "submitted": True}

    def capture(self, parameters, output_dir):
        fields(parameters, ("recipe",), ("recipe",))
        recipe = parameters["recipe"]
        fields(recipe, ("map", "sensor_blueprint", "sensor_attributes", "vehicle_blueprint", "spawn_index", "frames", "warmup_frames", "fixed_delta_seconds"), ("map", "sensor_blueprint"))
        string(recipe["map"], "map")
        sensor_id = string(recipe["sensor_blueprint"], "sensor_blueprint")
        if sensor_id not in ("sensor.camera.rgb", "sensor.lidar.ray_cast"):
            fail("unsupported_sensor", "capture supports explicitly selected RGB and RayCast LiDAR only", blueprint=sensor_id)
        frames = number(recipe.get("frames", 10), "frames", 1, 10000, True)
        warmup = number(recipe.get("warmup_frames", 2), "warmup_frames", 0, 1000, True)
        self.blueprint(sensor_id, recipe.get("sensor_attributes", {}))
        vehicle = recipe.get("vehicle_blueprint", "vehicle.tesla.model3")
        self.blueprint(vehicle)
        if output_dir is None:
            fail("invalid_parameters", "capture requires an absolute output_dir")
        output = Path(output_dir)
        root = Path(self.profile["output_root"]).resolve()
        if not output.is_absolute() or root not in output.resolve().parents:
            fail("invalid_parameters", "output_dir must be a child of output_root")
        output.mkdir(parents=True, exist_ok=True)
        if any(output.iterdir()):
            fail("output_not_empty", "capture output_dir must be empty")
        session_id = None
        report = {"schema_version": 1, "sensor_blueprint": sensor_id, "recipe": recipe,
                  "frames": [], "discarded_old_frames": 0, "status": "running"}
        old_handlers = {}
        def interrupted(signum, frame):
            fail("interrupted", "capture interrupted by signal", signal=signum)
        try:
            for signum in (signal.SIGTERM, signal.SIGINT):
                old_handlers[signum] = signal.signal(signum, interrupted)
            opened = self.open_session({"fixed_delta_seconds": recipe.get("fixed_delta_seconds", 0.05), "expected_map": recipe["map"]})
            session_id = opened["session_id"]
            report["session_id"] = session_id
            report["session_identity"] = opened["identity"]
            write_json(output / "capture.json", report)
            session = self.load_session(session_id)
            parent = self.spawn(session, {"blueprint": vehicle, "spawn_index": recipe.get("spawn_index", 0)})
            self.owned_actor(session, parent["actor_id"]).set_simulate_physics(False)
            report["vehicle_physics"] = False
            sensor = self.attach(session, {"parent_id": parent["actor_id"], "blueprint": sensor_id, "attributes": recipe.get("sensor_attributes", {})})
            actor = self.owned_actor(session, sensor["actor_id"])
            incoming, pending = queue.Queue(maxsize=64), {}
            overflow = []
            def receive(data):
                try:
                    incoming.put_nowait((data, time.time_ns(), time.monotonic_ns()))
                except queue.Full:
                    overflow.append(True)
            actor.listen(receive)
            def save_measurement(target, snapshot, tick_start, tick_end, item):
                data, received_wall_ns, received_monotonic_ns = item
                filename = "%010d.%s" % (target, "bgra" if sensor_id == "sensor.camera.rgb" else "f32")
                raw = bytes(data.raw_data)
                record = {"frame": target, "sensor_timestamp": data.timestamp,
                          "world": snapshot, "receive_wall_ns": received_wall_ns,
                          "receive_monotonic_ns": received_monotonic_ns, "tick_start_monotonic_ns": tick_start,
                          "tick_end_monotonic_ns": tick_end, "tick_duration_ms": (tick_end - tick_start) / 1e6,
                          "receive_after_tick_ms": (received_monotonic_ns - tick_end) / 1e6,
                          "tick_to_callback_ms": (received_monotonic_ns - tick_start) / 1e6,
                          "file": filename, "bytes": len(raw)}
                if sensor_id == "sensor.camera.rgb":
                    if len(raw) != data.width * data.height * 4:
                        fail("invalid_sensor_data", "BGRA byte count does not match dimensions")
                    record.update({"format": "BGRA8", "width": data.width, "height": data.height, "row_order": "CARLA raw_data"})
                else:
                    if len(raw) % 16:
                        fail("invalid_sensor_data", "RayCast data is not a sequence of float32 x,y,z,intensity")
                    record.update({"format": "float32", "byte_order": sys.byteorder, "fields": ["x", "y", "z", "intensity"], "points": len(raw) // 16})
                (output / filename).write_bytes(raw)
                report["frames"].append(record)
                with (output / "frames.jsonl").open("a") as stream:
                    json.dump(record, stream, allow_nan=False)
                    stream.write("\n")
            # Startup frames may be absent. Only post-warmup targets require a
            # callback; GPU drain advances adaptively, capped at 32 extra ticks.
            max_drain = 32 if sensor_id == "sensor.camera.rgb" else 0
            report["pipeline_drain_ticks"] = 0
            report["max_pipeline_drain_ticks"] = max_drain
            report["warmup_sensor_frames"] = 0
            report["tick_frames"] = []
            outstanding = []
            production_ticks = warmup + frames
            for tick_index in range(production_ticks + max_drain):
                if tick_index >= production_ticks and not outstanding:
                    break
                self.load_session(session_id)
                tick_start = time.monotonic_ns()
                target = self.world.tick(self.timeout)
                tick_end = time.monotonic_ns()
                previous = report["tick_frames"][-1] if report["tick_frames"] else None
                report["tick_frames"].append(target)
                if previous is not None and target != previous + 1:
                    fail("external_tick_detected", "capture ticks are not consecutive", expected_frame=previous + 1, actual_frame=target, tick_index=tick_index)
                snapshot = self.world.get_snapshot()
                if snapshot.frame != target:
                    fail("frame_mismatch", "world snapshot does not match requested tick", tick=target, snapshot=snapshot.frame)
                if tick_index >= production_ticks:
                    report["pipeline_drain_ticks"] += 1
                if overflow:
                    fail("sensor_queue_overflow", "sensor callback queue exceeded 64 frames")
                if tick_index < warmup:
                    while True:
                        try:
                            incoming.get_nowait()
                            report["warmup_sensor_frames"] += 1
                        except queue.Empty:
                            break
                    continue
                if tick_index < production_ticks:
                    outstanding.append((target, snapshot_dict(snapshot), tick_start, tick_end))
                if len(outstanding) > 64:
                    fail("sensor_queue_overflow", "unmatched tick buffer exceeded 64 frames")
                can_advance = tick_index < production_ticks + max_drain - 1
                while outstanding:
                    target, snapshot, tick_start, tick_end = outstanding[0]
                    deadline = time.monotonic() + (min(self.timeout, 0.02) if can_advance and max_drain else self.timeout)
                    while target not in pending:
                        if overflow:
                            fail("sensor_queue_overflow", "sensor callback queue exceeded 64 frames")
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            break
                        try:
                            item = incoming.get(timeout=remaining)
                        except queue.Empty:
                            break
                        frame = item[0].frame
                        if frame < target:
                            report["discarded_old_frames"] += 1
                        else:
                            if frame in pending:
                                fail("duplicate_sensor_frame", "sensor emitted duplicate frame", frame=frame)
                            pending[frame] = item
                            if len(pending) > 64:
                                fail("sensor_queue_overflow", "out-of-order buffer exceeded 64 frames")
                    if target not in pending:
                        if not can_advance or not max_drain:
                            fail("sensor_timeout", "sensor did not produce the measurement frame within bounded drain", frame=target, drain_ticks=report["pipeline_drain_ticks"])
                        break
                    if overflow:
                        fail("sensor_queue_overflow", "sensor callback queue exceeded 64 frames")
                    save_measurement(target, snapshot, tick_start, tick_end, pending.pop(target))
                    outstanding.pop(0)
            if outstanding or len(report["frames"]) != frames:
                fail("sensor_timeout", "capture ended without all measurement frames")
            report["status"] = "complete"
        except BaseException as exc:
            if session_id is None and isinstance(exc, WorkerError):
                session_id = exc.details.get("session_id")
                if session_id:
                    report["session_id"] = session_id
            report["status"] = "failed"
            report["error"] = {"code": getattr(exc, "code", "capture_failed"), "message": str(exc)}
            if isinstance(exc, WorkerError):
                exc.details["output_dir"] = str(output)
                raise
            raise WorkerError("capture_failed", str(exc), {"output_dir": str(output)}) from exc
        finally:
            # Ignore repeated termination only during bounded cleanup, then restore handlers.
            for signum in old_handlers:
                signal.signal(signum, signal.SIG_IGN)
            active_error = sys.exc_info()[1]
            cleanup_failure = None
            try:
                if session_id:
                    try:
                        report["cleanup"] = self.close_session(session_id)
                    except Exception as cleanup_error:
                        report["cleanup"] = {"ok": False, "code": getattr(cleanup_error, "code", "cleanup_failed"), "message": str(cleanup_error)}
                        if active_error is None:
                            report["status"] = "cleanup_failed"
                            cleanup_failure = cleanup_error
                        if isinstance(active_error, WorkerError):
                            active_error.details["cleanup"] = report["cleanup"]
                report["metrics"] = {
                    "captured_frames": len(report["frames"]),
                    "raw_bytes": sum(record["bytes"] for record in report["frames"]),
                    "discarded_old_frames": report["discarded_old_frames"],
                    "pipeline_drain_ticks": report.get("pipeline_drain_ticks", 0),
                    "mean_tick_duration_ms": (sum(record["tick_duration_ms"] for record in report["frames"]) / len(report["frames"])) if report["frames"] else None}
                try:
                    write_json(output / "capture.json", report)
                except Exception as artifact_error:
                    primary = active_error or cleanup_failure
                    if isinstance(primary, WorkerError):
                        primary.details["artifact_error"] = str(artifact_error)
                    else:
                        raise
                if cleanup_failure is not None:
                    raise cleanup_failure
            finally:
                for signum, handler in old_handlers.items():
                    signal.signal(signum, handler)
        return {"output_dir": str(output), "metadata": str(output / "capture.json"), "session_identity": report["session_identity"], "vehicle_physics": report["vehicle_physics"], "frames": report["frames"], "metrics": report["metrics"], "cleanup": report.get("cleanup")}

    def run(self, operation, parameters, output_dir=None):
        if operation == "connection.doctor":
            fields(parameters, ())
            result = {"python": sys.executable, "client_version": self.client.get_client_version(), "server_version": self.client.get_server_version(), "host": self.host, "port": self.port}
            result["compatible"] = result["client_version"] == result["server_version"]
            if not result["compatible"]:
                return result
            self.connect()
            result["identity"] = self.identity()
            return result
        self.connect()
        if operation == "map.inspect":
            fields(parameters, ("limit",))
            limit = number(parameters.get("limit", 20), "limit", 1, 500, True)
            current_map = method(self.world, "get_map")()
            points = method(current_map, "get_spawn_points")()
            return {"map": capability(current_map, "name"), "spawn_points": {
                "total": len(points), "limit": limit,
                "points": [{"index": index, "transform": transform_dict(point)} for index, point in enumerate(points[:limit])]}}
        if operation == "weather.inspect":
            fields(parameters, ())
            weather = method(self.world, "get_weather")()
            names = ("cloudiness", "precipitation", "precipitation_deposits", "wind_intensity", "sun_azimuth_angle",
                     "sun_altitude_angle", "fog_density", "fog_distance", "fog_falloff", "wetness", "scattering_intensity",
                     "mie_scattering_scale", "rayleigh_scattering_scale", "dust_storm", "snow_precipitation",
                     "snow_accumulation", "environment_lighting_gain")
            values = {}
            for name in names:
                value = getattr(weather, name, None)
                if type(value) in (int, float) and math.isfinite(value):
                    values[name] = value
            if not values:
                fail("unsupported_capability", "No supported numeric weather fields are available", capability="WeatherParameters")
            return {"weather": values}
        if operation == "actors.inspect":
            fields(parameters, ("actor_id",), ("actor_id",))
            actor_id = number(parameters["actor_id"], "actor_id", 1, 2 ** 32 - 1, True)
            actor = method(self.world, "get_actor")(actor_id)
            if actor is None:
                fail("actor_missing", "actor does not exist", actor_id=actor_id)
            result = {"actor_id": actor_id, "type_id": capability(actor, "type_id"),
                      "transform": transform_dict(method(actor, "get_transform")()),
                      "velocity": vector_dict(method(actor, "get_velocity")()),
                      "acceleration": vector_dict(method(actor, "get_acceleration")())}
            bounding_box = getattr(actor, "bounding_box", None)
            if bounding_box is not None:
                result["bounding_box"] = dict(transform_dict(bounding_box), extent=vector_dict(capability(bounding_box, "extent")))
            return result
        if operation == "spectator.inspect":
            fields(parameters, ())
            spectator = method(self.world, "get_spectator")()
            return {"transform": transform_dict(method(spectator, "get_transform")())}
        if operation == "world.inspect":
            fields(parameters, ())
            points = self.world.get_map().get_spawn_points()
            return dict(self.identity(), settings=settings_dict(self.world.get_settings()), snapshot=snapshot_dict(self.world.get_snapshot()),
                        spawn_points={"total": len(points), "limit": 20, "transforms": [transform_dict(point) for point in points[:20]]})
        if operation in ("blueprints.list", "actors.list"):
            fields(parameters, ("filter",))
            pattern = string(parameters.get("filter", "*"), "filter")
            if operation == "blueprints.list":
                return {"blueprints": [blueprint_dict(bp) for bp in self.world.get_blueprint_library().filter(pattern)]}
            return {"actors": [{"actor_id": actor.id, "type_id": actor.type_id, "attributes": dict(actor.attributes), "transform": transform_dict(actor.get_transform())} for actor in self.world.get_actors().filter(pattern)]}
        if operation == "sensors.describe":
            fields(parameters, ("blueprint",), ("blueprint",))
            blueprint = self.blueprint(parameters["blueprint"])
            if not blueprint.id.startswith("sensor."):
                fail("invalid_blueprint", "sensors.describe requires a sensor blueprint")
            return blueprint_dict(blueprint)
        shapes = {
            "session.open": (("fixed_delta_seconds", "expected_map"), ()),
            "session.close": (("session_id",), ("session_id",)),
            "actors.spawn": (("session_id", "blueprint", "spawn_index"), ("session_id", "blueprint")),
            "actors.destroy": (("session_id", "actor_id"), ("session_id", "actor_id")),
            "vehicle.control": (("session_id", "actor_id", "control"), ("session_id", "actor_id", "control")),
            "sensors.attach": (("session_id", "parent_id", "blueprint", "attributes", "transform"), ("session_id", "parent_id", "blueprint")),
            "world.tick": (("session_id", "frames"), ("session_id",)),
            "capture.run": (("recipe",), ("recipe",)),
        }
        if operation not in shapes:
            fail("unknown_operation", "unknown operation", operation=operation)
        fields(parameters, *shapes[operation])
        self.require_mutation()
        try:
            with self.locked(parameters.get("session_id")):
                if operation == "session.open":
                    return self.open_session(parameters)
                if operation == "session.close":
                    return self.close_session(parameters["session_id"])
                if operation == "capture.run":
                    return self.capture(parameters, output_dir)
                session = self.load_session(parameters["session_id"])
                if operation == "actors.spawn":
                    return self.spawn(session, parameters)
                if operation == "actors.destroy":
                    self.destroy(session, parameters["actor_id"])
                    return {"actor_id": parameters["actor_id"], "destroyed": True}
                if operation == "sensors.attach":
                    return self.attach(session, parameters)
                if operation == "vehicle.control":
                    return self.control(session, parameters)
                return self.tick(session, parameters.get("frames", 1))
        except BlockingIOError:
            fail("instance_busy", "another worker is mutating this instance")


def run_operation(request):
    fields(request, ("operation", "profile", "parameters", "output_dir"), ("operation", "profile", "parameters"))
    return Worker(request["profile"]).run(string(request["operation"], "operation"), request["parameters"], request.get("output_dir"))


def main():
    protocol_stream = sys.stdout
    try:
        stdout_fd = protocol_stream.fileno()
    except (AttributeError, OSError):
        stdout_fd = None
    if stdout_fd == 1:
        protocol_stream.flush()
        protocol_stream = os.fdopen(os.dup(1), "w", encoding="utf-8")
        # Keep fd1 redirected through native destructors and process atexit.
        os.dup2(2, 1)
    try:
        try:
            request = json.load(sys.stdin)
            with contextlib.redirect_stdout(sys.stderr):
                result = run_operation(request)
            response, status = {"ok": True, "result": result}, 0
        except BaseException as exc:
            if isinstance(exc, (SystemExit, GeneratorExit)):
                raise
            response = {"ok": False, "error": {"code": getattr(exc, "code", "worker_error"), "message": str(exc), "details": getattr(exc, "details", {})}}
            status = 1
        json.dump(response, protocol_stream, allow_nan=False)
        protocol_stream.write("\n")
        protocol_stream.flush()
        return status
    finally:
        if stdout_fd == 1:
            protocol_stream.close()


if __name__ == "__main__":
    sys.exit(main())
