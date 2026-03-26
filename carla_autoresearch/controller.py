from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median


RESULTS_HEADER = (
    "commit\tscan_latency_ms_median\tscan_latency_ms_p95\tpoint_count_ok\tstatus\tdescription"
)

DEFAULT_LIDAR_ATTRIBUTES = {
    "range": "200",
    "simu_brdf": "true",
    "channels": "64",
    "points_per_second": "1600000",
    "horizontal_fov": "120.0",
    "rotation_frequency": "10.0",
    "upper_fov": "10.0",
    "lower_fov": "-30.0",
    "noise_seed": "0",
    "noise_stddev": "0.0",
    "dropoff_general_rate": "0.0",
    "dropoff_zero_intensity": "0.0",
    "dropoff_intensity_limit": "1.0",
}


@dataclass(frozen=True)
class CarlaPaths:
    project_dir: Path = Path("/media/yhr/2T/CarlaUE5")
    package_script: Path = Path("/media/yhr/2T/CarlaUE5/package.sh")
    server_script: Path = Path(
        "/media/yhr/2T/CarlaUE5/Build/Package/"
        "Carla-0.10.0-Linux-Shipping/Linux/CarlaUnreal.sh"
    )
    default_client_script: Path = field(
        default_factory=lambda: Path(__file__).with_name("benchmark_client.py")
    )
    client_conda_env: str = "py38"
    host: str = "127.0.0.1"
    port: int = 2000
    town: str = "Town05"
    warmup_scans: int = 20
    measured_scans: int = 100
    build_timeout_seconds: int = 45 * 60
    server_start_timeout_seconds: int = 60
    client_timeout_seconds: int = 180


@dataclass(frozen=True)
class BenchmarkMetrics:
    map_name: str
    sensor_blueprint: str
    scan_latency_ms_median: float
    scan_latency_ms_p95: float
    point_count_baseline: int
    point_count_all_equal: bool
    warmup_scans: int
    measured_scans: int
    status: str

    @classmethod
    def from_json(cls, path: Path) -> "BenchmarkMetrics":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            map_name=payload["map"],
            sensor_blueprint=payload["sensor_blueprint"],
            scan_latency_ms_median=float(payload["scan_latency_ms_median"]),
            scan_latency_ms_p95=float(payload["scan_latency_ms_p95"]),
            point_count_baseline=int(payload["point_count_baseline"]),
            point_count_all_equal=bool(payload["point_count_all_equal"]),
            warmup_scans=int(payload["warmup_scans"]),
            measured_scans=int(payload["measured_scans"]),
            status=payload["status"],
        )


@dataclass(frozen=True)
class DecisionResult:
    status: str
    reason: str


class ExperimentDecision:
    @staticmethod
    def compare(
        baseline: BenchmarkMetrics,
        candidate: BenchmarkMetrics,
    ) -> DecisionResult:
        if not candidate.point_count_all_equal:
            return DecisionResult("discard", "point count mismatch across scans")
        if candidate.point_count_baseline != baseline.point_count_baseline:
            return DecisionResult("discard", "point count baseline changed")
        if candidate.scan_latency_ms_median < baseline.scan_latency_ms_median:
            return DecisionResult("keep", "median latency improved")
        return DecisionResult("discard", "median latency did not improve")


class CarlaTargetAdapter:
    def __init__(self, paths: CarlaPaths):
        self.paths = paths

    def build_command(self) -> list[str]:
        return ["./package.sh"]

    def server_command(self) -> list[str]:
        return ["sh", self.paths.server_script.name]

    def server_terminal_command(self, log_path: Path) -> list[str]:
        script = (
            f"cd {shlex.quote(str(self.paths.server_script.parent))} && "
            f"{' '.join(shlex.quote(part) for part in self.server_command())} "
            f"> {shlex.quote(str(log_path))} 2>&1"
        )
        return ["gnome-terminal", "--", "bash", "-lc", script]

    def find_running_server_pids(self) -> list[int]:
        result = subprocess.run(
            ["pgrep", "-af", "CarlaUnreal-Linux-Shipping CarlaUnreal"],
            check=False,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            return []
        pids = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            pid_text = line.split(maxsplit=1)[0]
            try:
                pids.append(int(pid_text))
            except ValueError:
                continue
        return pids

    def benchmark_command(
        self,
        output_path: Path,
        client_script: Path | None = None,
    ) -> list[str]:
        script = client_script or self.paths.default_client_script
        command = [
            "conda",
            "run",
            "-n",
            self.paths.client_conda_env,
            "python",
            str(script),
            "--host",
            self.paths.host,
            "--port",
            str(self.paths.port),
            "--map",
            self.paths.town,
            "--warmup-scans",
            str(self.paths.warmup_scans),
            "--measured-scans",
            str(self.paths.measured_scans),
            "--output",
            str(output_path),
        ]
        for key, value in DEFAULT_LIDAR_ATTRIBUTES.items():
            command.extend(["--lidar-attr", f"{key}={value}"])
        return command

    def benchmark_terminal_command(
        self,
        output_path: Path,
        log_path: Path,
        client_script: Path | None = None,
    ) -> list[str]:
        benchmark_cmd = " ".join(
            shlex.quote(part) for part in self.benchmark_command(output_path, client_script)
        )
        script = (
            'source "$(conda info --base)/etc/profile.d/conda.sh" && '
            f"conda activate {shlex.quote(self.paths.client_conda_env)} && "
            f"cd {shlex.quote(str(self.paths.default_client_script.parent.parent))} && "
            f"{benchmark_cmd} > {shlex.quote(str(log_path))} 2>&1"
        )
        return ["gnome-terminal", "--", "bash", "-lc", script]

    def run_build(self, log_path: Path) -> subprocess.CompletedProcess[str]:
        with log_path.open("w", encoding="utf-8") as log_file:
            return subprocess.run(
                self.build_command(),
                cwd=self.paths.project_dir,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=self.paths.build_timeout_seconds,
                check=False,
            )

    def launch_server(self, log_path: Path) -> list[int]:
        existing_pids = set(self.find_running_server_pids())
        subprocess.run(
            self.server_terminal_command(log_path),
            check=False,
            text=True,
        )
        deadline = time.time() + self.paths.server_start_timeout_seconds
        while time.time() < deadline:
            current_pids = set(self.find_running_server_pids())
            new_pids = sorted(current_pids - existing_pids)
            if new_pids:
                return new_pids
            time.sleep(1)
        return []

    def stop_server(self, process: list[int] | None) -> None:
        if not process:
            return
        for pid in process:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                continue

    def run_benchmark(self, output_path: Path, log_path: Path) -> subprocess.CompletedProcess[str]:
        launch = subprocess.run(
            self.benchmark_terminal_command(output_path, log_path),
            check=False,
            text=True,
        )
        if launch.returncode != 0:
            return launch

        deadline = time.time() + self.paths.client_timeout_seconds
        while time.time() < deadline:
            if output_path.exists():
                return subprocess.CompletedProcess(
                    args=launch.args,
                    returncode=0,
                )
            time.sleep(1)

        return subprocess.CompletedProcess(
            args=launch.args,
            returncode=1,
        )


class ExperimentController:
    def __init__(self, adapter: CarlaTargetAdapter):
        self.adapter = adapter

    def run_once(
        self,
        workspace: Path,
        baseline_metrics_path: Path | None = None,
        reuse_existing_server: bool = False,
    ) -> tuple[BenchmarkMetrics, DecisionResult]:
        workspace.mkdir(parents=True, exist_ok=True)
        build_log = workspace / "build.log"
        server_log = workspace / "server.log"
        benchmark_log = workspace / "benchmark.log"
        metrics_path = workspace / "metrics.json"

        build_result = self.adapter.run_build(build_log)
        if build_result.returncode != 0:
            metrics = BenchmarkMetrics(
                map_name=self.adapter.paths.town,
                sensor_blueprint="sensor.lidar.ray_cast",
                scan_latency_ms_median=0.0,
                scan_latency_ms_p95=0.0,
                point_count_baseline=0,
                point_count_all_equal=False,
                warmup_scans=self.adapter.paths.warmup_scans,
                measured_scans=self.adapter.paths.measured_scans,
                status="crash",
            )
            return metrics, DecisionResult("crash", "build failed")

        server_process = None
        reused_existing_server = False
        if reuse_existing_server and self.adapter.find_running_server_pids():
            reused_existing_server = True
        else:
            server_process = self.adapter.launch_server(server_log)
        try:
            benchmark_result = self.adapter.run_benchmark(metrics_path, benchmark_log)
        finally:
            if not reused_existing_server:
                self.adapter.stop_server(server_process)

        if benchmark_result.returncode != 0 or not metrics_path.exists():
            metrics = BenchmarkMetrics(
                map_name=self.adapter.paths.town,
                sensor_blueprint="sensor.lidar.ray_cast",
                scan_latency_ms_median=0.0,
                scan_latency_ms_p95=0.0,
                point_count_baseline=0,
                point_count_all_equal=False,
                warmup_scans=self.adapter.paths.warmup_scans,
                measured_scans=self.adapter.paths.measured_scans,
                status="crash",
            )
            return metrics, DecisionResult("crash", "benchmark failed")

        metrics = BenchmarkMetrics.from_json(metrics_path)
        if baseline_metrics_path is None:
            return metrics, DecisionResult("keep", "baseline recorded")
        baseline = BenchmarkMetrics.from_json(baseline_metrics_path)
        return metrics, ExperimentDecision.compare(baseline, metrics)


def percentile_95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * 0.95)))
    return ordered[index]


def build_metrics(
    latencies_ms: list[float],
    point_counts: list[int],
    map_name: str,
    sensor_blueprint: str,
    warmup_scans: int,
    measured_scans: int,
) -> BenchmarkMetrics:
    baseline_count = point_counts[0] if point_counts else 0
    return BenchmarkMetrics(
        map_name=map_name,
        sensor_blueprint=sensor_blueprint,
        scan_latency_ms_median=median(latencies_ms) if latencies_ms else 0.0,
        scan_latency_ms_p95=percentile_95(latencies_ms),
        point_count_baseline=baseline_count,
        point_count_all_equal=all(count == baseline_count for count in point_counts),
        warmup_scans=warmup_scans,
        measured_scans=measured_scans,
        status="keep",
    )


def write_results_row(
    path: Path,
    commit: str,
    metrics: BenchmarkMetrics,
    status: str,
    description: str,
) -> None:
    lines = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        lines.append(RESULTS_HEADER)
    lines.append(
        "\t".join(
            [
                commit,
                f"{metrics.scan_latency_ms_median:.6f}",
                f"{metrics.scan_latency_ms_p95:.6f}",
                "true" if metrics.point_count_all_equal else "false",
                status,
                description,
            ]
        )
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
