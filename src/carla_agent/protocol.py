"""Small, inspectable operation contracts shared by CLI and research."""

import json
import math
from pathlib import Path


class AgentError(Exception):
    def __init__(self, code, message, exit_code=4, details=None):
        super().__init__(message)
        self.code, self.message = code, message
        self.exit_code, self.details = exit_code, details or {}

    def as_dict(self):
        return {"code": self.code, "message": self.message, "details": self.details}


# Required fields are suffixed !. Domain operations remain independently callable.
OPERATIONS = {
    "connection.doctor": {},
    "world.inspect": {},
    "map.inspect": {"limit": "integer"},
    "weather.inspect": {},
    "actors.inspect": {"actor_id!": "integer"},
    "spectator.inspect": {},
    "blueprints.list": {"filter": "string"},
    "actors.list": {"filter": "string"},
    "sensors.describe": {"blueprint!": "string"},
    "session.open": {"fixed_delta_seconds": "number", "expected_map": "string"},
    "session.close": {"session_id!": "string"},
    "actors.spawn": {"session_id!": "string", "blueprint!": "string", "spawn_index": "integer"},
    "actors.destroy": {"session_id!": "string", "actor_id!": "integer"},
    "vehicle.control": {"session_id!": "string", "actor_id!": "integer", "control!": "object"},
    "sensors.attach": {"session_id!": "string", "parent_id!": "integer", "blueprint!": "string", "attributes": "object", "transform": "object"},
    "world.tick": {"session_id!": "string", "frames": "integer"},
    "capture.run": {"recipe!": "object"},
}
READ_ONLY = {"connection.doctor", "world.inspect", "map.inspect", "weather.inspect", "actors.inspect", "spectator.inspect", "blueprints.list", "actors.list", "sensors.describe"}
PROFILE_FIELDS = {
    "schema_version", "client_python", "host", "port", "timeout_seconds", "output_root",
    "session_policy", "expected_server_version", "capability_profile", "server_pid",
}


def read_json(path):
    try:
        return json.loads(Path(path).read_text(), parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
    except (OSError, ValueError) as exc:
        raise AgentError("invalid_json", str(exc), 2) from exc


def atomic_json(path, value):
    import os
    import tempfile
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".write-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as out:
            json.dump(value, out, ensure_ascii=False, indent=2, allow_nan=False)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def validate_parameters(operation, parameters):
    if operation not in OPERATIONS:
        raise AgentError("unknown_operation", operation, 2)
    if not isinstance(parameters, dict):
        raise AgentError("invalid_parameters", "parameters must be an object", 2)
    spec = OPERATIONS[operation]
    allowed = {key.rstrip("!") for key in spec}
    if parameters.keys() - allowed:
        raise AgentError("unknown_parameter", ", ".join(sorted(parameters.keys() - allowed)), 2)
    types = {"string": str, "integer": int, "number": (int, float), "object": dict}
    for key, kind in spec.items():
        name = key.rstrip("!")
        if key.endswith("!") and name not in parameters:
            raise AgentError("missing_parameter", name, 2)
        if name not in parameters:
            continue
        value = parameters[name]
        if not isinstance(value, types[kind]) or (kind in ("number", "integer") and isinstance(value, bool)):
            raise AgentError("invalid_parameter", f"{name} must be {kind}", 2)
        if kind == "string" and not value:
            raise AgentError("invalid_parameter", f"{name} must not be empty", 2)
        if kind == "number" and isinstance(value, float) and not math.isfinite(value):
            raise AgentError("invalid_parameter", f"{name} must be finite", 2)
    if operation == "map.inspect" and not 1 <= parameters.get("limit", 20) <= 500:
        raise AgentError("invalid_parameter", "limit must be from 1 to 500", 2)
    if operation in ("actors.inspect", "vehicle.control") and not 1 <= parameters["actor_id"] <= 2 ** 32 - 1:
        raise AgentError("invalid_parameter", "actor_id must be from 1 to 4294967295", 2)
    if operation == "vehicle.control":
        controls = parameters["control"]
        properties = schema(operation)["parameters"]["properties"]["control"]["properties"]
        if controls.keys() - properties.keys():
            raise AgentError("invalid_parameter", "control contains unknown fields", 2)
        for name, value in controls.items():
            rule = properties[name]
            kind = rule["type"]
            if kind == "boolean":
                valid = type(value) is bool
            else:
                valid = (type(value) in ((int,) if kind == "integer" else (int, float))
                         and (not isinstance(value, float) or math.isfinite(value))
                         and rule["minimum"] <= value <= rule["maximum"])
            if not valid:
                raise AgentError("invalid_parameter", "invalid control field: " + name, 2)


def load_profile(path):
    data = read_json(path)
    if not isinstance(data, dict) or data.keys() - PROFILE_FIELDS:
        raise AgentError("invalid_profile", "Expected an object containing documented profile fields only", 2)
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise AgentError("unsupported_schema", "Profile schema_version must be 1", 2)
    for key in ("client_python", "output_root"):
        if not isinstance(data.get(key), str) or not Path(data[key]).is_absolute():
            raise AgentError("invalid_profile", f"{key} must be an absolute path", 2)
    defaults = {"host": "127.0.0.1", "port": 2000, "timeout_seconds": 10,
                "session_policy": "inspect_only", "capability_profile": "standard"}
    result = {**defaults, **data}
    if not isinstance(result["host"], str) or not result["host"].strip():
        raise AgentError("invalid_profile", "host must be a nonempty string", 2)
    if result["host"].lower() == "localhost":
        result["host"] = "127.0.0.1"
    if type(result["port"]) is not int or not 1 <= result["port"] <= 65535:
        raise AgentError("invalid_profile", "port must be an integer from 1 to 65535", 2)
    timeout = result["timeout_seconds"]
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0.01 <= timeout <= 120:
        raise AgentError("invalid_profile", "timeout_seconds must be finite, from 0.01 to 120", 2)
    if result["session_policy"] not in ("inspect_only", "exclusive"):
        raise AgentError("invalid_profile", "session_policy must be inspect_only or exclusive", 2)
    if result["capability_profile"] not in ("standard", "custom-mems"):
        raise AgentError("invalid_profile", "capability_profile must be standard or custom-mems", 2)
    if "server_pid" in result and (type(result["server_pid"]) is not int or result["server_pid"] <= 0):
        raise AgentError("invalid_profile", "server_pid must be a positive integer", 2)
    if "expected_server_version" in result and (not isinstance(result["expected_server_version"], str) or not result["expected_server_version"]):
        raise AgentError("invalid_profile", "expected_server_version must be a nonempty string", 2)
    return result


def schema(operation):
    if operation not in OPERATIONS:
        raise AgentError("unknown_operation", operation, 2)
    spec = OPERATIONS[operation]
    result = {"operation": operation, "mutates_world": operation not in READ_ONLY,
            "parameters": {"type": "object", "additionalProperties": False,
                           "required": [k[:-1] for k in spec if k.endswith("!")],
                           "properties": {k.rstrip("!"): {"type": v} for k, v in spec.items()}}}
    if operation == "map.inspect":
        result["parameters"]["properties"]["limit"].update(minimum=1, maximum=500, default=20)
    if operation in ("actors.inspect", "vehicle.control"):
        result["parameters"]["properties"]["actor_id"].update(minimum=1, maximum=2 ** 32 - 1)
    if operation == "vehicle.control":
        result["parameters"]["properties"]["control"] = {
            "type": "object", "additionalProperties": False,
            "properties": {
                "throttle": {"type": "number", "minimum": 0, "maximum": 1, "default": 0},
                "steer": {"type": "number", "minimum": -1, "maximum": 1, "default": 0},
                "brake": {"type": "number", "minimum": 0, "maximum": 1, "default": 0},
                "hand_brake": {"type": "boolean", "default": False},
                "reverse": {"type": "boolean", "default": False},
                "manual_gear_shift": {"type": "boolean", "default": False},
                "gear": {"type": "integer", "minimum": -1, "maximum": 2 ** 31 - 1, "default": 0},
            },
        }
    if operation == "capture.run":
        result["parameters"]["properties"]["recipe"] = {
            "type": "object", "additionalProperties": False,
            "required": ["map", "sensor_blueprint"],
            "properties": {
                "map": {"type": "string", "description": "Existing exact map name; no load_world"},
                "sensor_blueprint": {"enum": ["sensor.camera.rgb", "sensor.lidar.ray_cast"]},
                "sensor_attributes": {"type": "object"},
                "vehicle_blueprint": {"type": "string", "default": "vehicle.tesla.model3"},
                "spawn_index": {"type": "integer", "minimum": 0, "default": 0},
                "frames": {"type": "integer", "minimum": 1, "maximum": 10000, "default": 10},
                "warmup_frames": {"type": "integer", "minimum": 0, "maximum": 1000, "default": 2},
                "fixed_delta_seconds": {"type": "number", "default": 0.05},
            },
        }
    return result
