"""Injected capture facts test controller invariants, not CARLA runtime behavior."""

import copy
from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
import math
import os
from pathlib import Path
import struct
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from carla_agent import research
from carla_agent.protocol import AgentError, atomic_json, read_json

IDENTITY = {"pid": 123, "start_ticks": "321", "port": 2000, "executable": "/fake/server", "executable_sha256": "binary"}
WORLD = {"episode_id": 7, "map": "Town01"}


class ResearchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.p_state = patch.dict(os.environ, {"XDG_STATE_HOME": str(self.root / "state")})
        self.p_state.start()
        self.addCleanup(self.p_state.stop)
        self.profile_path = self.root / "profile.json"
        atomic_json(self.profile_path, {"schema_version": 1, "client_python": sys.executable, "output_root": str(self.root), "session_policy": "exclusive", "expected_server_version": "test", "server_pid": 123})
        self.plan = {"schema_version": 1, "profile": "profile.json", "workload": {"map": "Town01", "sensor_blueprint": "sensor.lidar.ray_cast", "sensor_attributes": {"channels": "32"}, "frames": 2, "warmup_frames": 1, "fixed_delta_seconds": 0.05},
                     "allowed_attributes": ["channels"], "candidates": [{"id": "lower", "sensor_attributes": {"channels": "16"}}],
                     "objective": {"metric": "tick_to_sensor_callback_ms", "unit": "ms", "direction": "minimize"},
                     "validity_contract": {"mode": "tradeoff", "min_points_per_frame": 2, "require_finite_points": True, "threshold_source": "test task quality requirement"},
                     "comparison_policy": {"repeats": 2, "min_improvement_fraction": 0.1, "max_pair_relative_spread": 0.05, "threshold_source": "test fixture noise requirement"},
                     "confirmation": {"repeats": 2}, "budget": {"max_trials": 20, "max_seconds": 120, "trial_timeout_seconds": 5}}
        self.plan_path = self.root / "plan.json"
        self.calls, self.inspections = [], 0
        self.baseline_ms, self.candidate_ms = 10, 7
        self.bad = None
        self.failure_at = None
        self.stop_at = None
        self.identity = copy.deepcopy(IDENTITY)
        self.world = copy.deepcopy(WORLD)
        self.close_calls = []
        self.p_identity = patch.object(research.bridge, "server_identity", side_effect=lambda p: copy.deepcopy(self.identity))
        self.p_capture = patch.object(research.bridge, "invoke", side_effect=self.capture)
        self.p_identity.start()
        self.p_capture.start()
        self.addCleanup(self.p_identity.stop)
        self.addCleanup(self.p_capture.stop)

    def prepare(self):
        atomic_json(self.plan_path, self.plan)
        return research._prepare(self.plan_path)

    def snapshot_files(self):
        return {str(path.relative_to(self.root)): (path.read_bytes(), path.stat().st_mtime_ns) if path.is_file() else None
                for path in self.root.rglob("*")}

    def capture(self, profile, operation, parameters, output_dir=None, timeout_seconds=None):
        if operation == "world.inspect":
            self.inspections += 1
            return {**self.world, "settings": {}, "snapshot": {}}
        if operation == "session.close":
            self.close_calls.append(parameters["session_id"])
            return {"closed": True, "settings_restored": True}
        self.assertEqual(operation, "capture.run")
        output = Path(output_dir)
        self.assertFalse(output.exists(), "research must never reuse a capture directory")
        self.assertGreater(timeout_seconds, 0)
        self.assertLessEqual(timeout_seconds, self.plan["budget"]["trial_timeout_seconds"])
        output.mkdir()
        recipe = copy.deepcopy(parameters["recipe"])
        self.calls.append((output, recipe))
        if self.failure_at == len(self.calls):
            atomic_json(output / "capture.json", {"status": "failed", "recipe": recipe, "session_id": "owned-session", "session_identity": WORLD})
            raise KeyboardInterrupt()
        metric = self.baseline_ms if recipe["sensor_attributes"]["channels"] == "32" else self.candidate_ms
        if callable(metric):
            metric = metric(len(self.calls))
        frames = []
        for i in range(recipe["frames"]):
            frame = 100 + i
            stamp = frame * 0.05
            filename = f"{frame}.f32"
            coords = (float("nan"), 0, 0, 1) if self.bad == "nan" else (1, 2, 3, 0.5)
            raw = struct.pack("<ffff", *coords) * (1 if self.bad == "floor" else 2)
            (output / filename).write_bytes(raw)
            frames.append({"frame": frame, "sensor_timestamp": stamp,
                           "world": {"frame": frame, "timestamp": {"elapsed_seconds": stamp}},
                           "tick_start_monotonic_ns": 1000000000, "receive_monotonic_ns": 1000000000 + int(metric * 1e6),
                           "file": filename, "bytes": len(raw), "format": "float32", "byte_order": "little", "fields": ["x", "y", "z", "intensity"], "points": len(raw) // 16})
        if self.bad == "duplicate":
            frames[1]["frame"] = frames[0]["frame"]
        if self.bad == "timestamp":
            frames[1]["sensor_timestamp"] += 0.1
        if self.bad == "stale":
            frames = []
        capture = {"status": "complete", "recipe": recipe, "frames": frames, "session_identity": copy.deepcopy(self.world)}
        atomic_json(output / "capture.json", capture)
        result = {"frames": frames, "metadata": str(output / "capture.json"), "artifact_dir": str(output), "session_identity": copy.deepcopy(self.world),
                  "cleanup": {"closed": True, "settings_restored": True}, "metrics": {"tick_to_sensor_callback_ms": 0.01, "captured_frames": 999}}
        atomic_json(output / "result.json", result)
        if self.stop_at == len(self.calls):
            atomic_json(output.parents[2] / "stop-request.json", {"requested_at": time.time()})
        return result

    def execute(self, **kwargs):
        run = self.prepare()
        return run, research._execute(run, **kwargs)

    def test_normal_keep_needs_paired_search_and_independent_confirmation(self):
        run, result = self.execute()
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["verdict"], "keep")
        self.assertEqual(result["validity"], "valid")
        self.assertEqual(len(self.calls), 8)
        self.assertEqual([c[1]["sensor_attributes"]["channels"] for c in self.calls], ["32", "16", "16", "32"] * 2)
        state = read_json(run / "state.json")
        self.assertEqual({t["stage"] for t in state["trials"][:4]}, {"selection"})
        self.assertEqual({t["stage"] for t in state["trials"][4:]}, {"confirmation"})
        self.assertTrue(all(t["summary"]["metric"] in (7, 10) for t in state["trials"]))
        self.assertTrue((run / "report.md").exists())
        self.assertIn("no geometric equivalence", result["conclusion_scope"])

    def test_validate_request_is_offline_and_does_not_create_or_change_files(self):
        atomic_json(self.plan_path, self.plan)
        before = self.snapshot_files()
        with patch.object(research.bridge, "invoke", side_effect=AssertionError("offline validation")), \
                patch.object(research.bridge, "server_identity", side_effect=AssertionError("offline validation")):
            result = research.dispatch(SimpleNamespace(action="validate", plan=str(self.plan_path)))
        self.assertTrue(result["valid"])
        self.assertEqual(result["validation_scope"], "plan_and_profile_only")
        self.assertIs(result["simulator_checked"], False)
        self.assertEqual(result["plan"]["profile"], str(self.profile_path))
        self.assertEqual(result["planned_selection_trials"], 4)
        self.assertEqual(result["planned_confirmation_trials"], 4)
        self.assertEqual(result["worst_case_trials"], 8)
        self.assertTrue(result["budget_sufficient"])
        self.assertEqual(before, self.snapshot_files())

    def test_validate_request_preserves_insufficient_budget_and_thresholds(self):
        self.plan["candidates"].append({"id": "lower2", "sensor_attributes": {"channels": "8"}})
        self.plan["budget"]["max_trials"] = 1
        atomic_json(self.plan_path, self.plan)
        before = self.snapshot_files()
        with patch.object(research.bridge, "invoke", side_effect=AssertionError("offline validation")), \
                patch.object(research.bridge, "server_identity", side_effect=AssertionError("offline validation")):
            result = research.validate_request(self.plan_path)
        self.assertFalse(result["budget_sufficient"])
        self.assertEqual(result["planned_selection_trials"], 8)
        self.assertEqual(result["worst_case_trials"], 12)
        self.assertEqual(result["plan"]["budget"]["max_trials"], 1)
        self.assertEqual(result["plan"]["comparison_policy"], self.plan["comparison_policy"])
        self.assertEqual(before, self.snapshot_files())

    def test_validate_request_rejects_unknown_plan_and_invalid_research_profile(self):
        invalid_plan = {**self.plan, "unknown": True}
        atomic_json(self.plan_path, invalid_plan)
        with self.assertRaises(AgentError):
            research.validate_request(self.plan_path)
        invalid_plan = copy.deepcopy(self.plan)
        invalid_plan["budget"]["max_trials"] = 10 ** 1000
        atomic_json(self.plan_path, invalid_plan)
        with self.assertRaises(AgentError):
            research.validate_request(self.plan_path)
        atomic_json(self.plan_path, self.plan)
        original = read_json(self.profile_path)
        invalid_profiles = [{**original, "unknown": 1}, {**original, "server_pid": True},
                            {**original, "session_policy": "inspect_only"}]
        for missing in ("server_pid", "expected_server_version"):
            invalid_profiles.append({k: v for k, v in original.items() if k != missing})
        for profile in invalid_profiles:
            atomic_json(self.profile_path, profile)
            before = self.snapshot_files()
            with self.subTest(profile=profile), \
                    patch.object(research.bridge, "invoke", side_effect=AssertionError("offline validation")), \
                    patch.object(research.bridge, "server_identity", side_effect=AssertionError("offline validation")), \
                    self.assertRaises(AgentError) as error:
                research.validate_request(self.plan_path)
            self.assertEqual(error.exception.code, "invalid_profile")
            self.assertEqual(before, self.snapshot_files())

    def test_compare_completed_run_is_offline_and_strictly_read_only(self):
        run, expected = self.execute()
        self.plan_path.unlink()
        self.profile_path.unlink()
        before = self.snapshot_files()
        with patch.object(research.bridge, "invoke", side_effect=AssertionError("server unavailable")), \
                patch.object(research.bridge, "server_identity", side_effect=AssertionError("server unavailable")), \
                patch.object(research, "_lock", side_effect=AssertionError("compare cannot create a lock")), \
                patch.object(research, "_save", side_effect=AssertionError("compare cannot save")), \
                patch.object(research, "_event", side_effect=AssertionError("compare cannot emit events")):
            result = research.dispatch(SimpleNamespace(action="compare", run=str(run)))
        self.assertTrue(result["read_only"])
        self.assertFalse(result["incomplete"])
        self.assertEqual(result["verdict"], "keep")
        for key, value in expected.items():
            self.assertEqual(result[key], value)
        self.assertEqual(before, self.snapshot_files())

    def test_compare_refuses_raw_trial_and_frozen_input_tampering(self):
        for target in ("raw", "trial", "duplicate_id", "verdict", "plan", "profile"):
            with self.subTest(target=target):
                run, _ = self.execute()
                if target == "raw":
                    next((run / "trials").glob("*/capture/*.f32")).write_bytes(b"changed")
                elif target == "trial":
                    path = next((run / "trials").glob("*/trial.json"))
                    trial = read_json(path)
                    trial["finished_at"] += 1
                    atomic_json(path, trial)
                elif target == "duplicate_id":
                    state = read_json(run / "state.json")
                    state["trials"][1]["id"] = state["trials"][0]["id"]
                    atomic_json(run / "state.json", state)
                elif target == "verdict":
                    state = read_json(run / "state.json")
                    state["verdict"] = "discard"
                    atomic_json(run / "state.json", state)
                else:
                    path = run / (target + ".json")
                    value = read_json(path)
                    if target == "plan":
                        value["budget"]["max_trials"] += 1
                    else:
                        value["port"] = 2001
                    atomic_json(path, value)
                before = self.snapshot_files()
                with self.assertRaises(AgentError) as error:
                    research.compare(run)
                self.assertEqual(error.exception.code, "recovery_conflict")
                self.assertEqual(before, self.snapshot_files())

    def test_compare_partial_terminal_run_never_promotes_complete_subset_to_keep(self):
        self.plan["budget"]["max_trials"] = 4
        run, _ = self.execute()
        before = self.snapshot_files()
        result = research.compare(run)
        self.assertTrue(result["incomplete"])
        self.assertEqual(result["execution_status"], "budget_exhausted")
        self.assertEqual(result["validity"], "incomplete")
        self.assertEqual(result["verdict"], "not_evaluated")
        self.assertEqual(result["comparisons"]["lower"]["verdict"], "eligible")
        self.assertEqual(result["confirmation"]["validity"], "incomplete")
        self.assertEqual(before, self.snapshot_files())
        self.plan["budget"]["max_trials"] = 20
        run, _ = self.execute()
        state = read_json(run / "state.json")
        state.update(status="FAILED", execution_status="failed")
        atomic_json(run / "state.json", state)
        self.assertEqual(research._decision(state, research.validate_plan(self.plan, self.root))["verdict"], "keep")
        result = research.compare(run)
        self.assertEqual(result["verdict"], "not_evaluated")
        self.assertEqual(result["execution_status"], "failed")
        self.assertTrue(result["incomplete"])

    def test_compare_refuses_active_state_active_writer_and_missing_lock(self):
        run, _ = self.execute()
        before = self.snapshot_files()
        with (run / "writer.lock").open("r") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(AgentError) as error:
                research.compare(run)
            self.assertEqual(error.exception.code, "run_busy")
        self.assertEqual(before, self.snapshot_files())
        state = read_json(run / "state.json")
        state.update(status="RUNNING", execution_status="running")
        atomic_json(run / "state.json", state)
        before = self.snapshot_files()
        with self.assertRaises(AgentError) as error:
            research.compare(run)
        self.assertEqual(error.exception.code, "run_busy")
        self.assertEqual(before, self.snapshot_files())
        state.update(status="COMPLETED", execution_status="complete")
        atomic_json(run / "state.json", state)
        (run / "writer.lock").unlink()
        before = self.snapshot_files()
        with self.assertRaises(AgentError) as error:
            research.compare(run)
        self.assertEqual(error.exception.code, "invalid_run")
        self.assertEqual(before, self.snapshot_files())

    def test_equal_or_slower_discards_without_confirmation(self):
        for metric in (10, 11):
            with self.subTest(metric=metric):
                self.calls.clear()
                self.candidate_ms = metric
                run, result = self.execute()
                self.assertEqual(result["verdict"], "discard")
                self.assertIsNone(result["confirmation"])
                self.assertEqual(len(self.calls), 4)

    def test_confirmation_cannot_reuse_selection(self):
        self.candidate_ms = lambda n: 7 if n <= 4 else 11
        _, result = self.execute()
        self.assertEqual(result["verdict"], "discard")
        self.assertEqual(len(self.calls), 8)
        self.assertEqual(result["comparisons"]["lower"]["verdict"], "eligible")

    def test_pair_noise_is_inconclusive(self):
        self.candidate_ms = lambda n: 7 if n == 2 else 9
        _, result = self.execute()
        self.assertEqual(result["verdict"], "inconclusive")
        self.assertEqual(len(self.calls), 4)

    def test_invalid_raw_nan_floor_frames_and_stale_metrics_never_keep(self):
        for bad in ("nan", "floor", "duplicate", "timestamp", "stale"):
            with self.subTest(bad=bad):
                self.calls.clear()
                self.bad = bad
                _, result = self.execute()
                self.assertEqual(result["verdict"], "not_evaluated")
                self.assertEqual(result["validity"], "invalid")
                self.assertEqual(result["comparisons"]["lower"]["verdict"], "not_evaluated")

    def test_frozen_plan_rejects_unknown_undeclared_and_semantic_claim(self):
        invalid = []
        plan = copy.deepcopy(self.plan)
        plan["candidates"][0]["sensor_attributes"]["rotation_frequency"] = "20"
        invalid.append(plan)
        plan = copy.deepcopy(self.plan)
        plan["validity_contract"]["mode"] = "semantic_preserving"
        invalid.append(plan)
        plan = copy.deepcopy(self.plan)
        del plan["comparison_policy"]["min_improvement_fraction"]
        invalid.append(plan)
        plan = copy.deepcopy(self.plan)
        plan["budget"]["max_seconds"] = float("nan")
        invalid.append(plan)
        plan = copy.deepcopy(self.plan)
        plan["shell"] = "touch anything"
        invalid.append(plan)
        for plan in invalid:
            with self.subTest(plan=plan), self.assertRaises((AgentError, ValueError)):
                research.validate_plan(plan, self.root)
        self.assertFalse((self.root / "runs").exists())

    def test_trial_budget_stops_before_confirmation_and_counts_attempts(self):
        self.plan["budget"]["max_trials"] = 4
        _, result = self.execute()
        self.assertEqual(result["status"], "BUDGET_EXHAUSTED")
        self.assertEqual(result["verdict"], "not_evaluated")
        self.assertEqual(len(self.calls), 4)

    def test_time_budget_is_not_reset_on_recovery(self):
        run = self.prepare()
        state = read_json(run / "state.json")
        state["active_seconds"] = self.plan["budget"]["max_seconds"]
        atomic_json(run / "state.json", state)
        result = research._execute(run, recovering=True)
        self.assertEqual(result["status"], "BUDGET_EXHAUSTED")
        self.assertFalse(self.calls)

    def test_stop_finishes_current_capture_and_prevents_next(self):
        self.stop_at = 1
        _, result = self.execute()
        self.assertEqual(result["status"], "STOPPED")
        self.assertEqual(result["verdict"], "not_evaluated")
        self.assertEqual(len(self.calls), 1)

    def test_identity_change_before_and_during_trial_never_keep(self):
        run = self.prepare()
        self.identity["start_ticks"] = "reused-pid"
        with self.assertRaises(AgentError) as error:
            research._execute(run)
        self.assertEqual(error.exception.code, "identity_changed")
        self.identity = copy.deepcopy(IDENTITY)
        original = self.capture
        def changed(*args, **kwargs):
            result = original(*args, **kwargs)
            if args[1] == "capture.run":
                self.identity["executable_sha256"] = "other-build"
            return result
        with patch.object(research.bridge, "invoke", side_effect=changed):
            result = research._execute(run)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["verdict"], "not_evaluated")
        self.assertEqual(result["error"]["code"], "identity_changed")

    def test_episode_change_rejects_recovery_even_on_same_binary(self):
        run = self.prepare()
        self.world["episode_id"] += 1
        with self.assertRaises(AgentError) as error:
            research._execute(run, recovering=True)
        self.assertEqual(error.exception.code, "identity_changed")

    def test_recovery_preserves_completed_and_restarts_partial_in_fresh_dir(self):
        self.failure_at = 3
        run, result = self.execute()
        self.assertEqual(result["status"], "INTERRUPTED")
        state = read_json(run / "state.json")
        first = copy.deepcopy(state["trials"][:2])
        partial = state["trials"][2]["id"]
        self.failure_at = None
        result = research._execute(run, recovering=True)
        self.assertEqual(result["verdict"], "keep")
        state = read_json(run / "state.json")
        self.assertEqual(first, state["trials"][:2])
        self.assertEqual(state["trials"][2]["id"], partial)
        self.assertEqual(state["trials"][2]["status"], "INTERRUPTED")
        self.assertEqual(state["trials"][3]["key"], state["trials"][2]["key"])
        self.assertNotEqual(state["trials"][3]["id"], partial)
        self.assertEqual(len(state["trials"]), 9)
        self.assertEqual(self.close_calls, ["owned-session"])

    def test_recovery_rejects_completed_artifact_tampering(self):
        self.failure_at = 3
        run, _ = self.execute()
        raw = next((run / "trials").glob("*/capture/*.f32"))
        raw.write_bytes(b"changed")
        self.failure_at = None
        with self.assertRaises(AgentError) as error:
            research._execute(run, recovering=True)
        self.assertEqual(error.exception.code, "recovery_conflict")

    def test_frozen_or_source_plan_profile_change_rejects_recovery(self):
        for target in ("plan", "profile"):
            with self.subTest(target=target):
                run = self.prepare()
                if target == "plan":
                    changed = read_json(self.plan_path)
                    changed["budget"]["max_trials"] += 1
                    atomic_json(self.plan_path, changed)
                else:
                    changed = read_json(self.profile_path)
                    changed["port"] = 2001
                    atomic_json(self.profile_path, changed)
                with self.assertRaises(AgentError) as error:
                    research._execute(run, recovering=True)
                self.assertEqual(error.exception.code, "recovery_conflict")

    def test_live_controller_pid_start_identity_and_flock_block_resume(self):
        run = self.prepare()
        state = read_json(run / "state.json")
        state["worker"] = research._process(os.getpid())
        atomic_json(run / "state.json", state)
        with self.assertRaises(AgentError) as error:
            research._launch(run, recovering=True)
        self.assertEqual(error.exception.code, "run_busy")
        with (run / "writer.lock").open("a") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(AgentError) as error:
                research._execute(run)
        self.assertEqual(error.exception.code, "run_busy")
        stale = {**state["worker"], "start_ticks": "not-the-current-process"}
        self.assertFalse(research._alive(stale))

    def test_status_detects_dead_worker_and_resume_requires_explicit_retry(self):
        run = self.prepare()
        result = research.status(run)
        self.assertEqual(result["status"], "INTERRUPTED")
        self.assertTrue(result["recovery_required"])
        args = SimpleNamespace(action="resume", run=str(run), retry_interrupted=False, foreground=True)
        with self.assertRaises(AgentError) as error:
            research.dispatch(args)
        self.assertEqual(error.exception.code, "retry_required")

    def test_status_rejects_forged_complete_and_changed_finished_artifacts(self):
        run = self.prepare()
        state = read_json(run / "state.json")
        state.update(status="COMPLETED", execution_status="complete", verdict="keep", validity="valid")
        atomic_json(run / "state.json", state)
        with self.assertRaises(AgentError) as error:
            research.status(run)
        self.assertEqual(error.exception.code, "recovery_conflict")
        run, result = self.execute()
        self.assertEqual(research.status(run)["verdict"], "keep")
        first_raw = next((run / "trials").glob("*/capture/*.f32"))
        first_raw.write_bytes(b"altered")
        with self.assertRaises(AgentError) as error:
            research.status(run)
        self.assertEqual(error.exception.code, "recovery_conflict")

    def test_surviving_orphan_execution_process_blocks_resume(self):
        run = self.prepare()
        with patch.object(research, "_alive", return_value=False), patch.object(research, "_orphaned", return_value=True):
            with self.assertRaises(AgentError) as error:
                research._launch(run, recovering=True)
        self.assertEqual(error.exception.code, "run_busy")
        self.assertFalse(self.calls)

    def test_unproven_interrupted_ownership_refuses_cleanup_and_retry(self):
        self.failure_at = 1
        run, _ = self.execute()
        metadata = next((run / "trials").glob("*/capture/capture.json"))
        metadata.unlink()
        self.failure_at = None
        result = research._execute(run, recovering=True)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["code"], "cleanup_required")
        self.assertFalse(self.close_calls)
        self.assertEqual(len(self.calls), 1)

    def test_spawned_worker_waits_for_parent_launch_record_lock(self):
        run = self.prepare()
        state = read_json(run / "state.json")
        state["worker"] = research._process(os.getpid())
        state["status"] = "STARTING"
        atomic_json(run / "state.json", state)
        with ThreadPoolExecutor(max_workers=1) as pool:
            with research._lock(run):
                future = pool.submit(research._execute, run, False, True)
                time.sleep(0.01)
                self.assertFalse(future.done())
            result = future.result(timeout=5)
        self.assertEqual(result["verdict"], "keep")

    def test_instance_lock_serializes_runs_but_distinct_processes_do_not_conflict(self):
        first, second = self.prepare(), self.prepare()
        with research._instance_lock(first, IDENTITY):
            with self.assertRaises(AgentError) as error:
                research._execute(second)
            self.assertEqual(error.exception.code, "run_busy")
            self.assertTrue(Path(error.exception.details["lock_file"]).is_file())
            different = {**IDENTITY, "start_ticks": "other-process-start"}
            with research._instance_lock(second, different):
                pass
            with self.assertRaises(AgentError) as error:
                research._launch(second)
            self.assertEqual(error.exception.code, "run_busy")
        self.assertFalse(self.calls)
        result = research._execute(second)
        self.assertEqual(result["verdict"], "keep")
        events = [json.loads(line) for line in (second / "events.jsonl").read_text().splitlines()]
        self.assertIn("research_lock_acquired", [e["event"] for e in events])
        self.assertIn("research_lock_released", [e["event"] for e in events])

    def test_relative_xdg_state_is_rejected_before_creating_cwd_dependent_locks(self):
        run = self.prepare()
        with patch.dict(os.environ, {"XDG_STATE_HOME": "relative-state"}):
            with self.assertRaises(AgentError) as error:
                with research._instance_lock(run, IDENTITY):
                    self.fail("relative XDG directory must not be used")
        self.assertEqual(error.exception.code, "invalid_environment")

    def test_background_worker_preserves_source_import_path_and_detaches(self):
        run = self.prepare()
        fake = SimpleNamespace(pid=os.getpid(), wait=lambda: None)
        with patch.object(research.subprocess, "Popen", return_value=fake) as spawned:
            result = research._launch(run)
        argv = spawned.call_args.args[0]
        opts = spawned.call_args.kwargs
        self.assertEqual(argv[:3], [sys.executable, "-m", "carla_agent.research"])
        self.assertTrue(opts["start_new_session"])
        self.assertIn(str(Path(research.__file__).resolve().parent.parent), opts["env"]["PYTHONPATH"].split(os.pathsep))
        self.assertEqual(opts["cwd"], str(run))


if __name__ == "__main__":
    unittest.main()
