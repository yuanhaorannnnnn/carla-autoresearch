import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests.fake_carla import World, make_module


WORKER_PATH = Path(__file__).resolve().parents[1] / "src" / "carla_agent" / "worker.py"
spec = importlib.util.spec_from_file_location("isolated_worker", WORKER_PATH)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.world = World()
        self.module_patch = patch.dict(sys.modules, {"carla": make_module(self.world)})
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)
        self.environment_patch = patch.dict(os.environ, {"XDG_STATE_HOME": str(self.root / "state")})
        self.environment_patch.start()
        self.addCleanup(self.environment_patch.stop)
        self.profile = {"output_root": str(self.root / "out"), "session_policy": "exclusive", "expected_server_version": "sprint42", "timeout_seconds": 0.02}

    def run_op(self, operation, parameters=None, output=None, profile=None):
        return worker.run_operation({"operation": operation, "parameters": parameters or {}, "profile": profile or self.profile, "output_dir": str(output) if output else None})

    def assert_code(self, code, operation, parameters=None, **kwargs):
        with self.assertRaises(worker.WorkerError) as caught:
            self.run_op(operation, parameters, **kwargs)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def open(self):
        return self.run_op("session.open")["session_id"]

    def spawn(self, session_id):
        return self.run_op("actors.spawn", {"session_id": session_id, "blueprint": "vehicle.tesla.model3"})["actor_id"]

    def capture(self, sensor="sensor.camera.rgb", **recipe):
        parameters = {"map": "TownTest", "sensor_blueprint": sensor, "frames": 3, "warmup_frames": 0}
        parameters.update(recipe)
        return self.run_op("capture.run", {"recipe": parameters}, output=self.root / "out" / "capture")

    def test_diagnostics_and_read_only_operations_do_not_mutate(self):
        inspect = dict(self.profile, session_policy="inspect_only")
        self.assertEqual(self.run_op("connection.doctor", profile=inspect)["server_version"], "sprint42")
        self.assertEqual(self.run_op("world.inspect")["episode_id"], 42)
        points = self.run_op("world.inspect")["spawn_points"]
        self.assertEqual(points["total"], 1)
        self.assertEqual(points["transforms"][0]["location"]["z"], 100.0)
        self.assertEqual(len(self.run_op("blueprints.list")["blueprints"]), 3)
        self.assertEqual(self.run_op("actors.list")["actors"], [])
        self.assertIn("image_size_x", self.run_op("sensors.describe", {"blueprint": "sensor.camera.rgb"})["attributes"])
        self.assertFalse(self.world.settings.synchronous_mode)
        self.assert_code("policy_denied", "session.open", profile=inspect)

    def test_persistent_session_ownership_and_restore(self):
        stranger = self.world.spawn_actor(self.world.library.find("vehicle.tesla.model3"), None)
        session = self.open()
        vehicle = self.spawn(session)
        self.assertEqual(self.run_op("actors.list")["actors"][1]["transform"]["location"]["z"], 100.0)
        sensor = self.run_op("sensors.attach", {"session_id": session, "parent_id": vehicle, "blueprint": "sensor.camera.rgb"})["actor_id"]
        self.assertEqual(self.run_op("world.tick", {"session_id": session, "frames": 2})["frames"], [1, 2])
        self.assert_code("actor_not_owned", "actors.destroy", {"session_id": session, "actor_id": stranger.id})
        self.assert_code("actor_not_owned", "sensors.attach", {"session_id": session, "parent_id": stranger.id, "blueprint": "sensor.camera.rgb"})
        self.assertTrue(self.run_op("session.close", {"session_id": session})["settings_restored"])
        self.assertEqual(self.world.destroyed, [sensor, vehicle])
        self.assertEqual(self.world.physics_calls, [])
        self.assertIn(stranger.id, self.world.actors)
        self.assertFalse(self.world.settings.synchronous_mode)
        self.assertIsNone(self.world.settings.fixed_delta_seconds)

    def test_atomic_inspections_are_read_only_and_bounded(self):
        inspect = dict(self.profile, session_policy="inspect_only")
        actor = self.world.spawn_actor(self.world.library.find("vehicle.tesla.model3"), None)
        self.world.spawn_points *= 25
        self.world.weather.unknown_field = 999
        self.world.weather.fog_density = "not-numeric"
        points = self.run_op("map.inspect", profile=inspect)
        self.assertEqual(points["map"], "TownTest")
        self.assertEqual(points["spawn_points"]["total"], 25)
        self.assertEqual(len(points["spawn_points"]["points"]), 20)
        self.assertEqual(points["spawn_points"]["points"][1]["index"], 1)
        self.assertEqual(len(self.run_op("map.inspect", {"limit": 1})["spawn_points"]["points"]), 1)
        weather = self.run_op("weather.inspect", profile=inspect)["weather"]
        self.assertEqual(weather, {"cloudiness": 10.0, "snow_precipitation": 2.0,
                                   "snow_accumulation": 3.0, "environment_lighting_gain": 1.5})
        state = self.run_op("actors.inspect", {"actor_id": actor.id}, profile=inspect)
        self.assertEqual(state["velocity"], {"x": 0.0, "y": 0.0, "z": 0.0})
        self.assertEqual(state["acceleration"]["x"], 1.0)
        self.assertEqual(state["bounding_box"]["extent"]["x"], 2.0)
        self.assertEqual(self.run_op("spectator.inspect", profile=inspect)["transform"]["location"]["z"], 50)
        self.assertEqual(self.world.frame, 0)
        self.assertFalse(self.world.settings.synchronous_mode)
        self.assertEqual(self.world.control_calls, [])
        self.assertEqual(self.world.physics_calls, [])
        self.assertEqual(self.world.destroyed, [])
        self.assertEqual(list(self.world.actors), [actor.id])
        self.assertFalse((self.root / "out").exists())

    def test_inspection_invalid_missing_and_optional_actor_box(self):
        for parameters in ({"limit": 0}, {"limit": 501}, {"limit": True}, {"limit": 1.0}, {"limit": 10 ** 1000}):
            self.assert_code("invalid_parameters", "map.inspect", parameters)
        for parameters in ({}, {"actor_id": 0}, {"actor_id": True}, {"actor_id": 2 ** 32}):
            self.assert_code("invalid_parameters", "actors.inspect", parameters)
        self.assert_code("actor_missing", "actors.inspect", {"actor_id": 1})
        self.assert_code("invalid_parameters", "spectator.inspect", {"transform": {}})
        self.assert_code("invalid_parameters", "weather.inspect", {"weather": {}})
        actor = self.world.spawn_actor(self.world.library.find("sensor.camera.rgb"), None)
        self.assertNotIn("bounding_box", self.run_op("actors.inspect", {"actor_id": actor.id}))

    def test_inspections_report_missing_api_and_client_mismatch(self):
        for operation, name, parameters in (("map.inspect", "get_map", {}),
                                             ("weather.inspect", "get_weather", {}),
                                             ("spectator.inspect", "get_spectator", {}),
                                             ("actors.inspect", "get_actor", {"actor_id": 1})):
            with self.subTest(operation=operation), patch.object(self.world, name, None):
                self.assert_code("unsupported_capability", operation, parameters)
        actor = self.world.spawn_actor(self.world.library.find("vehicle.tesla.model3"), None)
        for name in ("get_transform", "get_velocity", "get_acceleration"):
            with self.subTest(name=name), patch.object(actor, name, None):
                self.assert_code("unsupported_capability", "actors.inspect", {"actor_id": actor.id})
        with patch.object(self.world, "get_map", return_value=object()):
            self.assert_code("unsupported_capability", "map.inspect")
        with patch.object(self.world, "get_weather", return_value=object()):
            self.assert_code("unsupported_capability", "weather.inspect")
        with patch.object(sys.modules["carla"].Client, "get_client_version", return_value="wrong"):
            for operation, parameters in (("map.inspect", {}), ("weather.inspect", {}),
                                          ("spectator.inspect", {}), ("actors.inspect", {"actor_id": actor.id})):
                self.assert_code("client_server_version_mismatch", operation, parameters)

    def test_vehicle_control_neutral_defaults_zero_and_boolean_values_without_tick(self):
        session = self.open()
        actor_id = self.spawn(session)
        result = self.run_op("vehicle.control", {"session_id": session, "actor_id": actor_id,
                                                 "control": {"throttle": 0, "steer": 0, "brake": 0,
                                                             "reverse": False, "hand_brake": True,
                                                             "manual_gear_shift": True, "gear": -1}})
        self.assertTrue(result["submitted"])
        self.assertEqual(result["control"]["throttle"], 0)
        self.assertIs(result["control"]["reverse"], False)
        self.assertIs(self.world.control_calls[0][1].hand_brake, True)
        self.assertEqual(self.world.control_calls[0][1].gear, -1)
        neutral = self.run_op("vehicle.control", {"session_id": session, "actor_id": actor_id, "control": {}})
        self.assertEqual(neutral["control"], {"throttle": 0, "steer": 0, "brake": 0, "gear": 0,
                                             "hand_brake": False, "reverse": False, "manual_gear_shift": False})
        self.assertEqual(self.world.frame, 0)
        self.assertEqual(self.world.physics_calls, [])

    def test_vehicle_control_requires_owned_vehicle_and_current_episode(self):
        stranger = self.world.spawn_actor(self.world.library.find("vehicle.tesla.model3"), None)
        session = self.open()
        actor_id = self.spawn(session)
        sensor = self.run_op("sensors.attach", {"session_id": session, "parent_id": actor_id,
                                                "blueprint": "sensor.camera.rgb"})["actor_id"]
        parameters = {"session_id": session, "actor_id": actor_id, "control": {"throttle": 0.5}}
        self.assert_code("actor_not_owned", "vehicle.control", dict(parameters, actor_id=stranger.id))
        self.assert_code("invalid_actor", "vehicle.control", dict(parameters, actor_id=sensor))
        with patch.object(self.world.actors[actor_id], "apply_control", None):
            self.assert_code("unsupported_capability", "vehicle.control", parameters)
        with patch.object(sys.modules["carla"], "VehicleControl", None):
            self.assert_code("unsupported_capability", "vehicle.control", parameters)
        with patch.object(sys.modules["carla"], "VehicleControl", return_value=object()):
            self.assert_code("unsupported_capability", "vehicle.control", parameters)
        self.assert_code("policy_denied", "vehicle.control", parameters,
                         profile=dict(self.profile, session_policy="inspect_only"))
        self.world.actors.pop(actor_id)
        self.assert_code("actor_missing", "vehicle.control", parameters)
        self.world.id += 1
        self.assert_code("episode_changed", "vehicle.control", parameters)
        self.assertEqual(self.world.control_calls, [])
        self.assertEqual(self.world.frame, 0)

    def test_vehicle_control_rejects_invalid_fields_before_control_rpc(self):
        session = self.open()
        actor_id = self.spawn(session)
        parameters = {"session_id": session, "actor_id": actor_id, "control": {}}
        for control in (None, [], {"throttle": True}, {"throttle": -0.01}, {"brake": 1.01},
                        {"steer": float("inf")}, {"steer": float("nan")}, {"steer": -1.1},
                        {"hand_brake": 1}, {"reverse": "false"}, {"manual_gear_shift": 0},
                        {"gear": True}, {"gear": 1.0}, {"gear": -2}, {"gear": 2 ** 31},
                        {"gear": 10 ** 1000}, {"autopilot": True}):
            with self.subTest(control=control):
                self.assert_code("invalid_parameters", "vehicle.control", dict(parameters, control=control))
        self.assert_code("invalid_parameters", "vehicle.control", {"session_id": session, "actor_id": actor_id})
        self.assertEqual(self.world.control_calls, [])
        self.assertEqual(self.world.frame, 0)

    def test_second_output_root_cannot_bypass_instance_lease(self):
        self.open()
        other = dict(self.profile, output_root=str(self.root / "other"))
        self.assert_code("instance_busy", "session.open", profile=other)

    def test_host_aliases_share_episode_lease(self):
        session = self.open()
        for alias in ("localhost", "127.0.0.1", "::1"):
            profile = dict(self.profile, host=alias)
            self.assert_code("instance_busy", "session.open", profile=profile)
        self.assertTrue(self.run_op("session.close", {"session_id": session}, profile=dict(self.profile, host="::1"))["closed"])

    def test_reloaded_episode_cannot_remove_original_or_other_lease(self):
        first = self.open()
        state = self.root / "state" / "carla-agent"
        original_lease = next(state.glob("*.lease.json"))
        original_bytes = original_lease.read_bytes()
        self.world.id += 1
        second = self.open()
        self.assert_code("episode_changed", "session.close", {"session_id": first})
        self.assertEqual(original_lease.read_bytes(), original_bytes)
        self.assertEqual(len(list(state.glob("*.lease.json"))), 2)
        self.run_op("session.close", {"session_id": second})
        self.assertEqual(original_lease.read_bytes(), original_bytes)

    def test_legacy_endpoint_lease_is_respected_and_explicitly_closable(self):
        session = self.open()
        state = self.root / "state" / "carla-agent"
        lease = next(state.glob("*.lease.json"))
        legacy = state / ("a" * 64 + ".lease.json")
        record = json.loads(lease.read_text())
        record.pop("identity")
        legacy.write_text(json.dumps(record))
        lease.unlink()
        self.assert_code("instance_busy", "session.open", profile=dict(self.profile, host="localhost"))
        self.assertTrue(legacy.exists())
        self.run_op("session.close", {"session_id": session})
        self.assertFalse(legacy.exists())

    def test_reload_after_flock_before_open_is_refused(self):
        original = worker.Worker.identity
        calls = []
        def identity(instance):
            calls.append(True)
            if len(calls) == 3:
                self.world.id += 1
            return original(instance)
        with patch.object(worker.Worker, "identity", identity):
            self.assert_code("episode_changed", "session.open")
        self.assertFalse(self.world.settings.synchronous_mode)
        self.assertEqual(list((self.root / "state" / "carla-agent").glob("*.lease.json")), [])

    def test_episode_change_prevents_tick_destroy_and_restore(self):
        session = self.open()
        vehicle = self.spawn(session)
        self.world.id += 1
        for operation, parameters in (("world.tick", {"session_id": session}), ("actors.destroy", {"session_id": session, "actor_id": vehicle}), ("session.close", {"session_id": session})):
            self.assert_code("episode_changed", operation, parameters)
        self.assertEqual(self.world.destroyed, [])
        self.assertTrue(self.world.settings.synchronous_mode)

    def test_settings_change_refuses_mutation_and_restore(self):
        session = self.open()
        self.world.settings.fixed_delta_seconds = 0.1
        self.assert_code("settings_changed", "world.tick", {"session_id": session})
        self.assert_code("settings_changed", "session.close", {"session_id": session})
        self.assertEqual(self.world.settings.fixed_delta_seconds, 0.1)

    def test_version_map_bounds_and_attributes_are_defended(self):
        self.assert_code("version_mismatch", "session.open", profile=dict(self.profile, expected_server_version="wrong"))
        self.assert_code("map_mismatch", "session.open", {"expected_map": "WrongTown"})
        session = self.open()
        vehicle = self.spawn(session)
        for attributes in ({"imaginary": "x"}, {"image_size_x": "-1"}, {"sensor_tick": []}):
            self.assert_code("invalid_attribute", "sensors.attach", {"session_id": session, "parent_id": vehicle, "blueprint": "sensor.camera.rgb", "attributes": attributes})
        self.assert_code("invalid_parameters", "world.tick", {"session_id": session, "frames": True})
        self.assert_code("invalid_parameters", "actors.spawn", {"session_id": session, "blueprint": "vehicle.tesla.model3", "spawn_index": 10})

    def test_rgb_capture_real_raw_bytes_and_timing(self):
        result = self.capture(warmup_frames=1)
        self.assertEqual([item["frame"] for item in result["frames"]], [2, 3, 4])
        self.assertEqual(result["metrics"]["raw_bytes"], 24)
        self.assertFalse(result["vehicle_physics"])
        self.assertEqual(self.world.physics_calls, [(1, False)])
        self.assertEqual(result["session_identity"], {"episode_id": 42, "map": "TownTest"})
        report = json.loads(Path(result["metadata"]).read_text())
        self.assertFalse(report["vehicle_physics"])
        for record in report["frames"]:
            self.assertEqual((Path(result["output_dir"]) / record["file"]).read_bytes(), b"\x00\x01\x02\xff" * 2)
            self.assertEqual(record["format"], "BGRA8")
            self.assertEqual(record["world"]["frame"], record["frame"])
            self.assertGreater(record["receive_wall_ns"], 0)
        self.assertEqual(self.world.actors, {})
        self.assertFalse(self.world.settings.synchronous_mode)

    def test_lidar_raw_and_out_of_order_matching(self):
        self.world.out_of_order = True
        result = self.capture("sensor.lidar.ray_cast")
        self.assertEqual([record["frame"] for record in result["frames"]], [1, 2, 3])
        self.assertEqual(result["metrics"]["discarded_old_frames"], 1)
        record = result["frames"][0]
        self.assertEqual(record["points"], 2)
        self.assertEqual(record["fields"], ["x", "y", "z", "intensity"])
        self.assertEqual((Path(result["output_dir"]) / record["file"]).read_bytes(), b"\x00" * 32)

    def test_rgb_two_tick_delayed_callback_uses_bounded_pipeline(self):
        self.world.callback_delay_ticks = 2
        result = self.capture(frames=1)
        self.assertEqual([record["frame"] for record in result["frames"]], [1])
        self.assertEqual(self.world.frame, 3)
        self.assertEqual(result["metrics"]["pipeline_drain_ticks"], 2)
        self.assertEqual(result["frames"][0]["world"]["frame"], 1)

    def test_warmup_missing_callbacks_are_not_measurement_failures(self):
        self.world.skip_sensor_until_frame = 3
        result = self.capture(warmup_frames=3, frames=2)
        self.assertEqual([record["frame"] for record in result["frames"]], [4, 5])
        self.assertEqual(result["metrics"]["pipeline_drain_ticks"], 0)

    def test_camera_callback_lag_beyond_two_ticks_drains_adaptively(self):
        self.world.callback_delay_ticks = 5
        result = self.capture(warmup_frames=3, frames=2)
        self.assertEqual([record["frame"] for record in result["frames"]], [4, 5])
        self.assertEqual(self.world.frame, 10)
        self.assertEqual(result["metrics"]["pipeline_drain_ticks"], 5)

    def test_missing_measurement_frame_is_not_replaced_by_later_frame(self):
        self.world.skip_sensor_until_frame = 4
        with self.assertRaises(worker.WorkerError) as caught:
            self.capture(warmup_frames=3, frames=2)
        self.assertEqual(caught.exception.code, "sensor_timeout")
        self.assertEqual(caught.exception.details["frame"], 4)
        self.assertLessEqual(self.world.frame, 37)
        self.assertEqual(self.world.actors, {})

    def test_sensor_timeout_keeps_failure_artifact_and_cleans(self):
        self.world.no_frames = True
        error = self.assert_code("sensor_timeout", "capture.run", {"recipe": {"map": "TownTest", "sensor_blueprint": "sensor.camera.rgb"}}, output=self.root / "out" / "capture")
        report = json.loads((Path(error.details["output_dir"]) / "capture.json").read_text())
        self.assertEqual(report["status"], "failed")
        self.assertTrue(report["cleanup"]["closed"])
        self.assertFalse(self.world.settings.synchronous_mode)
        self.assertEqual(self.world.actors, {})

    def test_tick_exception_cleans_and_reports_error(self):
        self.world.tick_error = True
        with self.assertRaises(worker.WorkerError) as caught:
            self.capture()
        self.assertEqual(caught.exception.code, "capture_failed")
        self.assertIn("tick timeout", str(caught.exception))
        self.assertEqual(self.world.actors, {})
        self.assertFalse(self.world.settings.synchronous_mode)

    def test_cleanup_failure_is_not_swallowed(self):
        self.world.destroy_error = True
        with self.assertRaises(worker.WorkerError) as caught:
            self.capture()
        self.assertEqual(caught.exception.code, "cleanup_failed")
        report = json.loads((self.root / "out" / "capture" / "capture.json").read_text())
        self.assertFalse(report["cleanup"]["ok"])
        self.assertTrue(self.world.settings.synchronous_mode)
        self.assertTrue(self.world.actors)

    def test_changed_episode_during_capture_does_not_claim_cleanup(self):
        self.world.change_episode = True
        with self.assertRaises(worker.WorkerError) as caught:
            self.capture()
        self.assertEqual(caught.exception.code, "episode_changed")
        self.assertEqual(caught.exception.details["cleanup"]["code"], "episode_changed")
        self.assertEqual(self.world.destroyed, [])

    def test_apply_timeout_after_apply_capture_still_cleans(self):
        self.world.apply_error = True
        with self.assertRaises(worker.WorkerError) as caught:
            self.capture()
        self.assertEqual(caught.exception.code, "settings_apply_failed")
        self.assertFalse(self.world.settings.synchronous_mode)
        self.assertTrue(caught.exception.details["session_id"])

    def test_unknown_sensor_and_recipe_field_do_not_create_session(self):
        with self.assertRaises(worker.WorkerError) as caught:
            self.capture("sensor.lidar.unknown")
        self.assertEqual(caught.exception.code, "unsupported_sensor")
        with self.assertRaises(worker.WorkerError) as caught:
            self.capture(shell="echo forbidden")
        self.assertEqual(caught.exception.code, "invalid_parameters")
        self.assertFalse(self.world.settings.synchronous_mode)

    def test_expired_lease_can_be_explicitly_closed_only(self):
        session = self.open()
        path = self.root / "out" / ".carla-agent" / (session + ".json")
        record = json.loads(path.read_text())
        record["lease_expires_at"] = 0
        path.write_text(json.dumps(record))
        self.assert_code("lease_expired", "world.tick", {"session_id": session})
        self.assertTrue(self.run_op("session.close", {"session_id": session})["closed"])

    def test_signal_interrupt_enters_cleanup_and_restores_handler(self):
        original_tick = self.world.tick
        old_handler = signal.getsignal(signal.SIGTERM)
        def interrupt_tick(timeout):
            signal.raise_signal(signal.SIGTERM)
            return original_tick(timeout)
        self.world.tick = interrupt_tick
        with self.assertRaises(worker.WorkerError) as caught:
            self.capture()
        self.assertEqual(caught.exception.code, "interrupted")
        self.assertEqual(self.world.actors, {})
        self.assertIs(signal.getsignal(signal.SIGTERM), old_handler)

    def test_main_emits_one_json_and_sends_python_diagnostics_to_stderr(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        def operation(request):
            print("CARLA diagnostic")
            return {"value": 1}
        with patch.object(worker, "run_operation", operation), patch.object(sys, "stdin", io.StringIO("{}")), patch.object(sys, "stdout", stdout), patch.object(sys, "stderr", stderr):
            self.assertEqual(worker.main(), 0)
        self.assertEqual(json.loads(stdout.getvalue()), {"ok": True, "result": {"value": 1}})
        self.assertEqual(stderr.getvalue(), "CARLA diagnostic\n")

    def test_subprocess_native_stdout_and_atexit_cannot_pollute_protocol(self):
        fake_directory = self.root / "subprocess-fake"
        fake_directory.mkdir()
        (fake_directory / "carla.py").write_text('''import atexit
import ctypes
import os
from types import SimpleNamespace
os.write(1, b"native import diagnostic\\n")
ctypes.CDLL(None).printf(b"native buffered C diagnostic\\n")
atexit.register(os.write, 1, b"native atexit diagnostic\\n")
class Client:
    def __init__(self, host, port): pass
    def set_timeout(self, timeout): pass
    def get_client_version(self): return "sprint42"
    def get_server_version(self): return "sprint42"
    def get_world(self):
        os.write(1, b"native RPC diagnostic\\n")
        return SimpleNamespace(id=42, get_map=lambda: SimpleNamespace(name="TownTest"))
    def __del__(self):
        os.write(1, b"native destructor diagnostic\\n")
''')
        environment = dict(os.environ, PYTHONPATH=str(fake_directory))
        for operation, expected_status in (("connection.doctor", 0), ("world.inspect", 1)):
            with self.subTest(operation=operation):
                request = {"operation": operation, "profile": self.profile, "parameters": {}}
                result = subprocess.run([sys.executable, str(WORKER_PATH)], input=json.dumps(request), text=True,
                                        capture_output=True, env=environment, timeout=10)
                self.assertEqual(result.returncode, expected_status, result.stderr)
                response = json.loads(result.stdout)
                self.assertEqual(response["ok"], expected_status == 0)
                self.assertEqual(len(result.stdout.splitlines()), 1)
                for marker in ("native import diagnostic", "native RPC diagnostic", "native destructor diagnostic", "native atexit diagnostic", "native buffered C diagnostic"):
                    self.assertIn(marker, result.stderr)

    def test_mismatched_client_never_calls_get_world(self):
        module = sys.modules["carla"]
        with patch.object(module.Client, "get_client_version", return_value="wrong-wheel"), patch.object(module.Client, "get_world", side_effect=AssertionError("unsafe get_world")) as get_world:
            doctor = self.run_op("connection.doctor")
            self.assertFalse(doctor["compatible"])
            self.assertNotIn("identity", doctor)
            self.assert_code("client_server_version_mismatch", "world.inspect")
            self.assert_code("client_server_version_mismatch", "session.open")
            get_world.assert_not_called()

    def test_early_capture_metadata_identifies_session_before_first_tick(self):
        original_tick = self.world.tick
        def tick(timeout):
            report = json.loads((self.root / "out" / "capture" / "capture.json").read_text())
            self.assertEqual(len(report["session_id"]), 32)
            self.assertEqual(report["frames"], [])
            return original_tick(timeout)
        self.world.tick = tick
        self.capture("sensor.lidar.ray_cast", frames=1)

    def test_queue_overflow_fails_and_cleans_owned_actors(self):
        self.world.burst_frames = 65
        with self.assertRaises(worker.WorkerError) as caught:
            self.capture("sensor.lidar.ray_cast")
        self.assertEqual(caught.exception.code, "sensor_queue_overflow")
        self.assertEqual(self.world.actors, {})
        self.assertFalse(self.world.settings.synchronous_mode)

    def test_attached_sensor_roles_are_unique_and_explicit_duplicates_refused(self):
        session = self.open()
        parent = self.spawn(session)
        parameters = {"session_id": session, "parent_id": parent, "blueprint": "sensor.camera.rgb"}
        first_result = self.run_op("sensors.attach", parameters)
        second_result = self.run_op("sensors.attach", parameters)
        first, second = first_result["actor_id"], second_result["actor_id"]
        roles = [self.world.actors[actor_id].attributes["role_name"] for actor_id in (first, second)]
        self.assertNotEqual(*roles)
        self.assertEqual(first_result["attributes"]["role_name"], roles[0])
        self.assertEqual(second_result["attributes"]["role_name"], roles[1])
        self.assertTrue(all(role.startswith(session + "-") for role in roles))
        explicit = dict(parameters, attributes={"role_name": "left-camera"})
        third = self.run_op("sensors.attach", explicit)["actor_id"]
        self.assertEqual(self.world.actors[third].attributes["role_name"], "left-camera")
        self.assert_code("sensor_role_in_use", "sensors.attach", explicit)
        self.assertEqual(len(self.world.actors), 4)

    def test_external_tick_jump_in_warmup_fails_and_preserves_evidence(self):
        self.world.tick_step = 2
        with self.assertRaises(worker.WorkerError) as caught:
            self.capture(warmup_frames=3)
        self.assertEqual(caught.exception.code, "external_tick_detected")
        self.assertEqual(caught.exception.details["expected_frame"], 3)
        self.assertEqual(caught.exception.details["actual_frame"], 4)
        report = json.loads((self.root / "out" / "capture" / "capture.json").read_text())
        self.assertEqual(report["tick_frames"], [2, 4])
        self.assertEqual(report["status"], "failed")
        self.assertTrue(report["cleanup"]["closed"])

    def test_external_tick_jump_in_camera_drain_is_rejected(self):
        self.world.callback_delay_ticks = 2
        original_tick = self.world.tick
        def tick(timeout):
            if self.world.frame:
                self.world.tick_step = 2
            return original_tick(timeout)
        self.world.tick = tick
        with self.assertRaises(worker.WorkerError) as caught:
            self.capture(frames=1)
        self.assertEqual(caught.exception.code, "external_tick_detected")
        self.assertEqual(self.world.actors, {})

    def test_known_sprint42_mems_attachment_requires_explicit_capability(self):
        blueprint = self.world.library.find("sensor.lidar.ray_cast")
        blueprint.id = "sensor.lidar.ray_cast_mems"
        self.world.library.items[blueprint.id] = blueprint
        session = self.open()
        parent = self.spawn(session)
        parameters = {"session_id": session, "parent_id": parent, "blueprint": blueprint.id}
        self.assert_code("capability_denied", "sensors.attach", parameters)
        result = self.run_op("sensors.attach", parameters, profile=dict(self.profile, capability_profile="custom-mems"))
        self.assertEqual(result["type_id"], blueprint.id)
        self.run_op("session.close", {"session_id": session})
        self.assert_code("unsupported_sensor", "capture.run", {"recipe": {"map": "TownTest", "sensor_blueprint": blueprint.id}},
                         output=self.root / "out" / "capture", profile=dict(self.profile, capability_profile="custom-mems"))


if __name__ == "__main__":
    unittest.main()
