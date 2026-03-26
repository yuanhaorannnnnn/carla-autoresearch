import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from carla_autoresearch.controller import (
    BenchmarkMetrics,
    CarlaPaths,
    CarlaTargetAdapter,
    ExperimentController,
    ExperimentDecision,
    write_results_row,
)


class CarlaPathsTest(unittest.TestCase):
    def test_default_paths_match_carla_layout(self):
        paths = CarlaPaths()

        self.assertEqual(paths.project_dir, Path("/media/yhr/2T/CarlaUE5"))
        self.assertEqual(paths.package_script, Path("/media/yhr/2T/CarlaUE5/package.sh"))
        self.assertEqual(
            paths.server_script,
            Path(
                "/media/yhr/2T/CarlaUE5/Build/Package/"
                "Carla-0.10.0-Linux-Shipping/Linux/CarlaUnreal.sh"
            ),
        )
        self.assertEqual(
            paths.default_client_script,
            Path("/media/yhr/2T/autoresearch/carla_autoresearch/benchmark_client.py"),
        )


class CarlaTargetAdapterTest(unittest.TestCase):
    def test_build_command_uses_package_script(self):
        adapter = CarlaTargetAdapter(CarlaPaths())

        self.assertEqual(adapter.build_command(), ["bash", "./package.sh"])

    def test_build_terminal_command_uses_gnome_terminal_and_py38(self):
        adapter = CarlaTargetAdapter(CarlaPaths())

        command = adapter.build_terminal_command(
            launcher_path=Path("/tmp/build-launcher.sh"),
            log_path=Path("/tmp/build.log"),
            exit_code_path=Path("/tmp/build.exitcode"),
        )
        joined = " ".join(command)

        self.assertEqual(command[0], "gnome-terminal")
        self.assertIn("/tmp/build-launcher.sh", joined)

    def test_build_launcher_script_contains_conda_and_exitcode_logic(self):
        adapter = CarlaTargetAdapter(CarlaPaths())

        content = adapter.build_launcher_script_content(
            log_path=Path("/tmp/build.log"),
            exit_code_path=Path("/tmp/build.exitcode"),
        )

        self.assertIn("conda activate py38", content)
        self.assertIn("bash ./package.sh", content)
        self.assertIn("/tmp/build.log", content)
        self.assertIn("/tmp/build.exitcode", content)

    def test_server_command_uses_default_launch(self):
        adapter = CarlaTargetAdapter(CarlaPaths())

        self.assertEqual(
            adapter.server_command(),
            ["sh", "CarlaUnreal.sh"],
        )

    def test_benchmark_command_targets_town05_static_sensor(self):
        adapter = CarlaTargetAdapter(CarlaPaths())

        command = adapter.benchmark_command(Path("/tmp/out.json"))

        self.assertIn("Town05", command)
        self.assertIn("--output", command)
        self.assertIn("/tmp/out.json", command)

    def test_server_terminal_command_uses_gnome_terminal(self):
        adapter = CarlaTargetAdapter(CarlaPaths())

        command = adapter.server_terminal_command(Path("/tmp/server.log"))

        self.assertEqual(command[0], "gnome-terminal")
        self.assertIn("CarlaUnreal.sh", " ".join(command))
        self.assertIn("/tmp/server.log", " ".join(command))

    def test_benchmark_terminal_command_activates_conda_in_new_terminal(self):
        adapter = CarlaTargetAdapter(CarlaPaths())

        command = adapter.benchmark_terminal_command(
            output_path=Path("/tmp/metrics.json"),
            log_path=Path("/tmp/client.log"),
        )
        joined = " ".join(command)

        self.assertEqual(command[0], "gnome-terminal")
        self.assertIn("conda activate py38", joined)
        self.assertIn("python3 -m carla_autoresearch.benchmark_client", joined)
        self.assertIn("/tmp/metrics.json", joined)
        self.assertIn("/tmp/client.log", joined)

    def test_server_log_ready_requires_initialized_and_loadmap(self):
        adapter = CarlaTargetAdapter(CarlaPaths())

        not_ready = (
            "[time] LogCarlaServer: Initialized CarlaServer: Ports(rpc=2000, streaming=2001, secondary=2002)\n"
        )
        ready = (
            "[time] LogCarlaServer: Initialized CarlaServer: Ports(rpc=2000, streaming=2001, secondary=2002)\n"
            "[time] LogGlobalStatus: LoadMap Load map complete /Game/Carla/Maps/EmptyGround/EmptyGround\n"
        )

        self.assertFalse(adapter.server_log_indicates_ready(not_ready))
        self.assertTrue(adapter.server_log_indicates_ready(ready))

    @mock.patch("carla_autoresearch.controller.subprocess.run")
    def test_find_running_server_pids_parses_pgrep_output(self, run_mock):
        run_mock.return_value = mock.Mock(
            returncode=0,
            stdout="123 /path/CarlaUnreal\n456 /path/CarlaUnreal\n",
        )
        adapter = CarlaTargetAdapter(CarlaPaths())

        pids = adapter.find_running_server_pids()

        self.assertEqual(pids, [123, 456])


class ExperimentControllerReuseTest(unittest.TestCase):
    class FakeAdapter:
        def __init__(self, active_pids):
            self.paths = CarlaPaths(
                town="Town05",
                warmup_scans=2,
                measured_scans=5,
            )
            self.active_pids = active_pids
            self.launch_calls = 0
            self.stop_calls = 0

        def run_build(self, log_path):
            return mock.Mock(returncode=0)

        def find_running_server_pids(self):
            return list(self.active_pids)

        def launch_server(self, log_path):
            self.launch_calls += 1
            return mock.Mock()

        def stop_server(self, process):
            self.stop_calls += 1

        def run_benchmark(self, output_path, log_path):
            payload = {
                "map": "Town05",
                "sensor_blueprint": "sensor.lidar.ray_cast",
                "scan_latency_ms_median": 9.5,
                "scan_latency_ms_p95": 10.8,
                "point_count_baseline": 1024,
                "point_count_all_equal": True,
                "warmup_scans": 2,
                "measured_scans": 5,
                "status": "keep",
            }
            output_path.write_text(json.dumps(payload), encoding="utf-8")
            return mock.Mock(returncode=0)

    def test_run_once_reuses_existing_server_when_requested(self):
        adapter = self.FakeAdapter(active_pids=[12345])
        controller = ExperimentController(adapter)

        with tempfile.TemporaryDirectory() as tmpdir:
            metrics, decision = controller.run_once(
                workspace=Path(tmpdir),
                reuse_existing_server=True,
            )

        self.assertEqual(metrics.map_name, "Town05")
        self.assertEqual(decision.status, "keep")
        self.assertEqual(adapter.launch_calls, 0)
        self.assertEqual(adapter.stop_calls, 0)

    def test_run_once_starts_server_when_reuse_requested_but_no_active_server(self):
        adapter = self.FakeAdapter(active_pids=[])
        controller = ExperimentController(adapter)

        with tempfile.TemporaryDirectory() as tmpdir:
            controller.run_once(
                workspace=Path(tmpdir),
                reuse_existing_server=True,
            )

        self.assertEqual(adapter.launch_calls, 1)
        self.assertEqual(adapter.stop_calls, 1)


class DecisionLogicTest(unittest.TestCase):
    def test_keep_when_latency_improves_and_point_count_matches(self):
        baseline = BenchmarkMetrics(
            map_name="Town05",
            sensor_blueprint="sensor.lidar.ray_cast",
            scan_latency_ms_median=10.0,
            scan_latency_ms_p95=11.0,
            point_count_baseline=1024,
            point_count_all_equal=True,
            warmup_scans=20,
            measured_scans=100,
            status="keep",
        )
        candidate = BenchmarkMetrics(
            map_name="Town05",
            sensor_blueprint="sensor.lidar.ray_cast",
            scan_latency_ms_median=9.5,
            scan_latency_ms_p95=10.8,
            point_count_baseline=1024,
            point_count_all_equal=True,
            warmup_scans=20,
            measured_scans=100,
            status="keep",
        )

        decision = ExperimentDecision.compare(baseline, candidate)

        self.assertEqual(decision.status, "keep")

    def test_discard_when_point_count_does_not_match(self):
        baseline = BenchmarkMetrics(
            map_name="Town05",
            sensor_blueprint="sensor.lidar.ray_cast",
            scan_latency_ms_median=10.0,
            scan_latency_ms_p95=11.0,
            point_count_baseline=1024,
            point_count_all_equal=True,
            warmup_scans=20,
            measured_scans=100,
            status="keep",
        )
        candidate = BenchmarkMetrics(
            map_name="Town05",
            sensor_blueprint="sensor.lidar.ray_cast",
            scan_latency_ms_median=8.0,
            scan_latency_ms_p95=9.0,
            point_count_baseline=1023,
            point_count_all_equal=False,
            warmup_scans=20,
            measured_scans=100,
            status="keep",
        )

        decision = ExperimentDecision.compare(baseline, candidate)

        self.assertEqual(decision.status, "discard")
        self.assertIn("point count", decision.reason)


class ResultsFileTest(unittest.TestCase):
    def test_write_results_row_creates_header_once(self):
        metrics = BenchmarkMetrics(
            map_name="Town05",
            sensor_blueprint="sensor.lidar.ray_cast",
            scan_latency_ms_median=9.5,
            scan_latency_ms_p95=10.8,
            point_count_baseline=1024,
            point_count_all_equal=True,
            warmup_scans=20,
            measured_scans=100,
            status="keep",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "results.tsv"
            write_results_row(path, "abc1234", metrics, "keep", "baseline")
            write_results_row(path, "def5678", metrics, "discard", "slower")

            content = path.read_text(encoding="utf-8").strip().splitlines()

        self.assertEqual(
            content[0],
            "commit\tscan_latency_ms_median\tscan_latency_ms_p95\tpoint_count_ok\tstatus\tdescription",
        )
        self.assertEqual(len(content), 3)

    def test_metrics_roundtrip_from_json(self):
        payload = {
            "map": "Town05",
            "sensor_blueprint": "sensor.lidar.ray_cast",
            "scan_latency_ms_median": 9.5,
            "scan_latency_ms_p95": 10.8,
            "point_count_baseline": 1024,
            "point_count_all_equal": True,
            "warmup_scans": 20,
            "measured_scans": 100,
            "status": "keep",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_path = Path(tmpdir) / "metrics.json"
            metrics_path.write_text(json.dumps(payload), encoding="utf-8")

            metrics = BenchmarkMetrics.from_json(metrics_path)

        self.assertEqual(metrics.map_name, "Town05")
        self.assertTrue(metrics.point_count_all_equal)


if __name__ == "__main__":
    unittest.main()
