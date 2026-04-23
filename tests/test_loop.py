import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

from carla_autoresearch.controller import (
    BenchmarkMetrics,
    read_status_file,
    write_status_file,
)
from carla_autoresearch.loop import (
    AutoresearchLoop,
    Hypothesis,
    LoopBaseline,
    LoopBest,
    LoopConfig,
    LoopCurrent,
    LoopState,
    LoopStateData,
    LoopTermination,
    _deserialize_state,
)


class StateSerializationTest(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"

            loop = _make_test_loop()
            with mock.patch("carla_autoresearch.loop.STATE_FILE", state_file):
                loop.save()
                loaded = AutoresearchLoop.load(state_file)

            self.assertEqual(loaded.data.loop_id, loop.data.loop_id)
            self.assertEqual(loaded.data.state, loop.data.state)
            self.assertEqual(loaded.data.config.target, "RayCastMemsLidar")
            self.assertEqual(loaded.data.baseline.latency_ms, 50.0)
            self.assertEqual(len(loaded.data.hypotheses), 0)

    def test_load_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "nonexistent.yaml"
            with self.assertRaises(FileNotFoundError):
                AutoresearchLoop.load(missing)

    def test_yaml_structure_matches_expected_schema(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"
            loop = _make_test_loop()
            with mock.patch("carla_autoresearch.loop.STATE_FILE", state_file):
                loop.save()

            raw = yaml.safe_load(state_file.read_text(encoding="utf-8"))

            self.assertIn("loop_id", raw)
            self.assertIn("version", raw)
            self.assertIn("state", raw)
            self.assertIn("config", raw)
            self.assertIn("baseline", raw)
            self.assertIn("best", raw)
            self.assertIn("current", raw)
            self.assertIn("hypotheses", raw)
            self.assertIn("termination", raw)
            self.assertIsInstance(raw["hypotheses"], list)


class InitTest(unittest.TestCase):
    def test_init_creates_valid_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"

            with mock.patch("carla_autoresearch.loop.STATE_FILE", state_file):
                loop = AutoresearchLoop.init(
                    target="RayCastMemsLidar",
                    metric="scan_latency_ms_median",
                    dimensions=["model-logic"],
                    max_rounds=10,
                    max_duration_minutes=240,
                    baseline_latency_ms=50.0,
                    baseline_commit="abc1234",
                    baseline_metrics_path="runs/baseline/metrics.json",
                )

            self.assertTrue(loop.data.loop_id.startswith("arl-"))
            self.assertEqual(loop.data.state, LoopState.IDLE.value)
            self.assertEqual(loop.data.config.target, "RayCastMemsLidar")
            self.assertEqual(loop.data.config.max_rounds, 10)
            self.assertEqual(loop.data.baseline.latency_ms, 50.0)
            self.assertEqual(loop.data.best.latency_ms, 50.0)
            self.assertEqual(loop.data.current.round, 0)
            self.assertEqual(len(loop.data.hypotheses), 0)

            self.assertTrue(state_file.exists())


class TerminationTest(unittest.TestCase):
    def test_terminates_at_max_rounds(self):
        loop = _make_test_loop()
        loop.data.current.round = 10

        should, reason = loop.should_terminate()

        self.assertTrue(should)
        self.assertIn("max_rounds", reason)

    def test_does_not_terminate_before_max_rounds(self):
        loop = _make_test_loop()
        loop.data.current.round = 5

        should, reason = loop.should_terminate()

        self.assertFalse(should)
        self.assertIsNone(reason)

    def test_terminates_at_max_duration(self):
        loop = _make_test_loop()
        loop.data.termination.total_duration_minutes = 240

        should, reason = loop.should_terminate()

        self.assertTrue(should)
        self.assertIn("max_duration", reason)

    def test_terminates_at_no_improvement_streak(self):
        loop = _make_test_loop()
        loop.data.current.round = 3
        loop.data.termination.no_improvement_streak = 3

        should, reason = loop.should_terminate()

        self.assertTrue(should)
        self.assertIn("no_improvement_streak", reason)

    def test_no_improvement_streak_ignored_before_round_1(self):
        loop = _make_test_loop()
        loop.data.current.round = 0
        loop.data.termination.no_improvement_streak = 5

        should, reason = loop.should_terminate()

        self.assertFalse(should)


class RecordResultTest(unittest.TestCase):
    def test_keep_resets_streak(self):
        loop = _make_test_loop()
        loop.data.termination.no_improvement_streak = 2
        loop.data.hypotheses = [
            Hypothesis(id="h1", description="test", target_file="f.cpp", dimension="model-logic"),
        ]

        loop.record_result("h1", "keep", "def5678")

        self.assertEqual(loop.data.termination.no_improvement_streak, 0)
        self.assertEqual(loop.data.current.round, 1)
        self.assertEqual(loop.data.hypotheses[0].status, "tested")
        self.assertEqual(loop.data.hypotheses[0].result, "keep")

    def test_discard_increments_streak(self):
        loop = _make_test_loop()
        loop.data.termination.no_improvement_streak = 1
        loop.data.hypotheses = [
            Hypothesis(id="h1", description="test", target_file="f.cpp", dimension="model-logic"),
        ]

        loop.record_result("h1", "discard", "def5678")

        self.assertEqual(loop.data.termination.no_improvement_streak, 2)
        self.assertEqual(loop.data.current.round, 1)

    def test_update_best(self):
        loop = _make_test_loop()

        loop.update_best(latency_ms=45.0, commit="better123", round_num=3)

        self.assertEqual(loop.data.best.latency_ms, 45.0)
        self.assertEqual(loop.data.best.commit, "better123")
        self.assertEqual(loop.data.best.round, 3)

    def test_update_baseline(self):
        loop = _make_test_loop()

        loop.update_baseline(
            latency_ms=48.0,
            commit="newbase456",
            metrics_path="runs/new/metrics.json",
        )

        self.assertEqual(loop.data.baseline.latency_ms, 48.0)
        self.assertEqual(loop.data.baseline.commit, "newbase456")
        self.assertEqual(loop.data.baseline.metrics_path, "runs/new/metrics.json")


class HypothesisQueueTest(unittest.TestCase):
    def test_next_pending_returns_first_pending(self):
        loop = _make_test_loop()
        loop.data.hypotheses = [
            Hypothesis(id="h1", description="done", target_file="a.cpp", dimension="model-logic", status="tested", result="discard"),
            Hypothesis(id="h2", description="next", target_file="b.cpp", dimension="model-logic", status="pending"),
            Hypothesis(id="h3", description="later", target_file="c.cpp", dimension="model-logic", status="pending"),
        ]

        next_h = loop.next_pending_hypothesis()

        self.assertIsNotNone(next_h)
        self.assertEqual(next_h.id, "h2")

    def test_next_pending_returns_none_when_empty(self):
        loop = _make_test_loop()
        loop.data.hypotheses = [
            Hypothesis(id="h1", description="done", target_file="a.cpp", dimension="model-logic", status="tested", result="discard"),
        ]

        next_h = loop.next_pending_hypothesis()

        self.assertIsNone(next_h)


class DecideTest(unittest.TestCase):
    def test_decide_keep_when_improved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline_path = Path(tmpdir) / "baseline.json"
            candidate_path = Path(tmpdir) / "candidate.json"

            _write_metrics(baseline_path, scan_latency_ms_median=50.0, point_count_baseline=100000)
            _write_metrics(candidate_path, scan_latency_ms_median=45.0, point_count_baseline=100000)

            loop = _make_test_loop()
            loop.data.baseline.metrics_path = str(baseline_path)

            result = loop.decide(candidate_path)

            self.assertEqual(result["status"], "keep")
            self.assertIn("improved", result["reason"])
            self.assertEqual(result["candidate_latency_ms"], 45.0)

    def test_decide_discard_when_slower(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline_path = Path(tmpdir) / "baseline.json"
            candidate_path = Path(tmpdir) / "candidate.json"

            _write_metrics(baseline_path, scan_latency_ms_median=50.0, point_count_baseline=100000)
            _write_metrics(candidate_path, scan_latency_ms_median=55.0, point_count_baseline=100000)

            loop = _make_test_loop()
            loop.data.baseline.metrics_path = str(baseline_path)

            result = loop.decide(candidate_path)

            self.assertEqual(result["status"], "discard")

    def test_decide_discard_on_point_count_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline_path = Path(tmpdir) / "baseline.json"
            candidate_path = Path(tmpdir) / "candidate.json"

            _write_metrics(baseline_path, scan_latency_ms_median=50.0, point_count_baseline=100000)
            _write_metrics(candidate_path, scan_latency_ms_median=45.0, point_count_baseline=100000, point_count_all_equal=False)

            loop = _make_test_loop()
            loop.data.baseline.metrics_path = str(baseline_path)

            result = loop.decide(candidate_path)

            self.assertEqual(result["status"], "discard")
            self.assertIn("point count", result["reason"])


class SummaryTest(unittest.TestCase):
    def test_summary_contains_key_fields(self):
        loop = _make_test_loop()
        loop.data.hypotheses = [
            Hypothesis(id="h1", description="done", target_file="a.cpp", dimension="model-logic", status="tested"),
            Hypothesis(id="h2", description="todo", target_file="b.cpp", dimension="model-logic", status="pending"),
        ]

        summary = loop.to_summary()

        self.assertEqual(summary["loop_id"], loop.data.loop_id)
        self.assertEqual(summary["state"], "idle")
        self.assertEqual(summary["round"], 0)
        self.assertEqual(summary["best_latency_ms"], 50.0)
        self.assertEqual(summary["pending_hypotheses"], 1)
        self.assertEqual(summary["tested_hypotheses"], 1)


class StatusFileTest(unittest.TestCase):
    def test_write_and_read_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "status.json"

            write_status_file(path, "running_benchmark", "server ready", round=3)
            data = read_status_file(path)

            self.assertEqual(data["state"], "running_benchmark")
            self.assertEqual(data["reason"], "server ready")
            self.assertEqual(data["round"], 3)

    def test_read_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = read_status_file(Path(tmpdir) / "missing.json")
            self.assertIsNone(data)

    def test_read_invalid_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.json"
            path.write_text("not json{", encoding="utf-8")
            data = read_status_file(path)
            self.assertIsNone(data)


def _make_test_loop() -> AutoresearchLoop:
    config = LoopConfig(
        target="RayCastMemsLidar",
        metric="scan_latency_ms_median",
        dimensions=["model-logic"],
        max_rounds=10,
        max_duration_minutes=240,
    )
    baseline = LoopBaseline(latency_ms=50.0, commit="abc1234", metrics_path="runs/baseline/metrics.json")
    best = LoopBest(latency_ms=50.0, commit="abc1234", round=0)
    current = LoopCurrent(round=0, hypothesis_id=None, workspace="", status_file="")
    termination = LoopTermination(no_improvement_streak=0, total_duration_minutes=0.0, reason=None)
    data = LoopStateData(
        loop_id="arl-test-001",
        version=1,
        state=LoopState.IDLE.value,
        config=config,
        baseline=baseline,
        best=best,
        current=current,
        hypotheses=[],
        termination=termination,
    )
    return AutoresearchLoop(data)


def _write_metrics(path: Path, **overrides) -> None:
    payload = {
        "map": "Town05",
        "sensor_blueprint": "sensor.lidar.ray_cast_mems",
        "scan_latency_ms_median": "50.0",
        "scan_latency_ms_p95": "60.0",
        "point_count_baseline": "100000",
        "point_count_all_equal": "true",
        "warmup_scans": "20",
        "measured_scans": "100",
        "status": "keep",
    }
    for k, v in overrides.items():
        payload[k] = "true" if v is True else ("false" if v is False else str(v))
    path.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
