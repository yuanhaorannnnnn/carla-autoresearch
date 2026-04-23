from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import yaml

from carla_autoresearch.controller import (
    BenchmarkMetrics,
    CarlaPaths,
    ExperimentDecisionExtended,
    HeadlessBuildAdapter,
    read_status_file,
    write_status_file,
)


STATE_FILE = Path(".agent-state") / "autoresearch-loop-state.yaml"


class LoopState(Enum):
    IDLE = "idle"
    ANALYZING = "analyzing"
    PATCHING = "patching"
    BUILDING = "building"
    BENCHMARKING = "benchmarking"
    ANALYZING_RESULTS = "analyzing_results"
    DECIDING = "deciding"
    TERMINATED = "terminated"


@dataclass
class Hypothesis:
    id: str
    description: str
    target_file: str
    dimension: str
    status: str = "pending"
    result: str | None = None
    commit_hash: str | None = None


@dataclass
class LoopConfig:
    target: str
    metric: str
    dimensions: list[str]
    max_rounds: int
    max_duration_minutes: int


@dataclass
class LoopBaseline:
    latency_ms: float
    commit: str
    metrics_path: str


@dataclass
class LoopBest:
    latency_ms: float
    commit: str
    round: int


@dataclass
class LoopCurrent:
    round: int
    hypothesis_id: str | None
    workspace: str
    status_file: str


@dataclass
class LoopTermination:
    no_improvement_streak: int
    total_duration_minutes: float
    reason: str | None


@dataclass
class LoopStateData:
    loop_id: str
    version: int
    state: str
    config: LoopConfig
    baseline: LoopBaseline
    best: LoopBest
    current: LoopCurrent
    hypotheses: list[Hypothesis]
    termination: LoopTermination
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AutoresearchLoop:
    def __init__(self, data: LoopStateData):
        self.data = data

    @property
    def state_file(self) -> Path:
        return STATE_FILE

    def save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(self.data)
        payload["state"] = self.data.state
        self.state_file.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | None = None) -> "AutoresearchLoop":
        path = path or STATE_FILE
        if not path.exists():
            raise FileNotFoundError(f"State file not found: {path}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(_deserialize_state(raw))

    @classmethod
    def init(
        cls,
        target: str,
        metric: str,
        dimensions: list[str],
        max_rounds: int,
        max_duration_minutes: int,
        baseline_latency_ms: float,
        baseline_commit: str,
        baseline_metrics_path: str,
    ) -> "AutoresearchLoop":
        loop_id = f"arl-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"
        config = LoopConfig(
            target=target,
            metric=metric,
            dimensions=dimensions,
            max_rounds=max_rounds,
            max_duration_minutes=max_duration_minutes,
        )
        baseline = LoopBaseline(
            latency_ms=baseline_latency_ms,
            commit=baseline_commit,
            metrics_path=baseline_metrics_path,
        )
        best = LoopBest(
            latency_ms=baseline_latency_ms,
            commit=baseline_commit,
            round=0,
        )
        current = LoopCurrent(
            round=0,
            hypothesis_id=None,
            workspace="",
            status_file="",
        )
        termination = LoopTermination(
            no_improvement_streak=0,
            total_duration_minutes=0.0,
            reason=None,
        )
        data = LoopStateData(
            loop_id=loop_id,
            version=1,
            state=LoopState.IDLE.value,
            config=config,
            baseline=baseline,
            best=best,
            current=current,
            hypotheses=[],
            termination=termination,
        )
        loop = cls(data)
        loop.save()
        return loop

    def run_build(self, workspace: Path) -> bool:
        self.data.state = LoopState.BUILDING.value
        self.save()
        adapter = HeadlessBuildAdapter(CarlaPaths())
        log_path = workspace / "build.log"
        result = adapter.run_build_headless(log_path)
        return result.returncode == 0

    def launch_benchmark_external(self, workspace: Path, status_file: Path) -> None:
        self.data.state = LoopState.BENCHMARKING.value
        self.save()
        runner = Path(__file__).with_name("external_runner.sh")
        cmd = [
            "gnome-terminal", "--",
            "bash", str(runner),
            str(workspace),
            str(status_file),
        ]
        subprocess.run(cmd, check=False)

    def poll_benchmark_status(self, status_file: Path) -> dict | None:
        return read_status_file(status_file)

    def decide(self, candidate_path: Path) -> dict:
        self.data.state = LoopState.DECIDING.value
        self.save()
        baseline = BenchmarkMetrics.from_json(Path(self.data.baseline.metrics_path))
        candidate = BenchmarkMetrics.from_json(candidate_path)
        result = ExperimentDecisionExtended.compare_extended(
            baseline, candidate, metric=self.data.config.metric
        )
        return {
            "status": result.status,
            "reason": result.reason,
            "candidate_latency_ms": candidate.scan_latency_ms_median,
            "baseline_latency_ms": baseline.scan_latency_ms_median,
        }

    def should_terminate(self) -> tuple[bool, str | None]:
        cfg = self.data.config
        term = self.data.termination

        if self.data.current.round >= cfg.max_rounds:
            return True, f"max_rounds ({cfg.max_rounds}) reached"

        if term.total_duration_minutes >= cfg.max_duration_minutes:
            return True, f"max_duration ({cfg.max_duration_minutes}min) reached"

        # no_improvement_streak: 3 consecutive discards/crashes after round 1
        if self.data.current.round >= 1 and term.no_improvement_streak >= 3:
            return True, f"no_improvement_streak ({term.no_improvement_streak}) reached"

        return False, None

    def record_result(self, hypothesis_id: str, result_status: str, commit: str) -> None:
        for h in self.data.hypotheses:
            if h.id == hypothesis_id:
                h.status = "tested"
                h.result = result_status
                h.commit_hash = commit
                break

        if result_status == "keep":
            self.data.termination.no_improvement_streak = 0
            # best is updated by caller with actual latency
        else:
            self.data.termination.no_improvement_streak += 1

        self.data.current.round += 1
        self.save()

    def update_best(self, latency_ms: float, commit: str, round_num: int) -> None:
        self.data.best = LoopBest(
            latency_ms=latency_ms,
            commit=commit,
            round=round_num,
        )
        self.save()

    def update_baseline(self, latency_ms: float, commit: str, metrics_path: str) -> None:
        self.data.baseline = LoopBaseline(
            latency_ms=latency_ms,
            commit=commit,
            metrics_path=metrics_path,
        )
        self.save()

    def next_pending_hypothesis(self) -> Hypothesis | None:
        for h in self.data.hypotheses:
            if h.status == "pending":
                return h
        return None

    def to_summary(self) -> dict:
        return {
            "loop_id": self.data.loop_id,
            "state": self.data.state,
            "round": self.data.current.round,
            "best_latency_ms": self.data.best.latency_ms,
            "best_commit": self.data.best.commit,
            "baseline_latency_ms": self.data.baseline.latency_ms,
            "pending_hypotheses": sum(1 for h in self.data.hypotheses if h.status == "pending"),
            "tested_hypotheses": sum(1 for h in self.data.hypotheses if h.status == "tested"),
            "no_improvement_streak": self.data.termination.no_improvement_streak,
        }


def _deserialize_state(raw: dict) -> LoopStateData:
    """Reconstruct LoopStateData from deserialized YAML dict."""
    return LoopStateData(
        loop_id=raw["loop_id"],
        version=raw.get("version", 1),
        state=raw["state"],
        config=LoopConfig(**raw["config"]),
        baseline=LoopBaseline(**raw["baseline"]),
        best=LoopBest(**raw["best"]),
        current=LoopCurrent(**raw["current"]),
        hypotheses=[Hypothesis(**h) for h in raw.get("hypotheses", [])],
        termination=LoopTermination(**raw["termination"]),
        created_at=raw.get("created_at", datetime.now(timezone.utc).isoformat()),
    )


def _current_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def cmd_init(args: argparse.Namespace) -> None:
    loop = AutoresearchLoop.init(
        target=args.target,
        metric=args.metric,
        dimensions=args.dimensions.split(","),
        max_rounds=args.max_rounds,
        max_duration_minutes=args.max_duration,
        baseline_latency_ms=args.baseline_latency,
        baseline_commit=args.baseline_commit or _current_commit(),
        baseline_metrics_path=args.baseline_metrics,
    )
    print(json.dumps(loop.to_summary(), indent=2))


def cmd_build(args: argparse.Namespace) -> None:
    loop = AutoresearchLoop.load()
    ok = loop.run_build(Path(args.workspace))
    print(json.dumps({"build_ok": ok, "workspace": str(args.workspace)}, indent=2))


def cmd_benchmark_launch(args: argparse.Namespace) -> None:
    loop = AutoresearchLoop.load()
    workspace = Path(args.workspace)
    status_file = workspace / "status.json"
    loop.launch_benchmark_external(workspace, status_file)
    loop.data.current.workspace = str(workspace)
    loop.data.current.status_file = str(status_file)
    loop.save()
    print(json.dumps({"launched": True, "status_file": str(status_file)}, indent=2))


def cmd_benchmark_poll(args: argparse.Namespace) -> None:
    loop = AutoresearchLoop.load()
    status_file = Path(loop.data.current.status_file) if loop.data.current.status_file else Path(args.status_file)
    status = loop.poll_benchmark_status(status_file)
    print(json.dumps(status or {"state": "unknown"}, indent=2))


def cmd_decide(args: argparse.Namespace) -> None:
    loop = AutoresearchLoop.load()
    metrics_path = Path(args.metrics_path)
    result = loop.decide(metrics_path)
    print(json.dumps(result, indent=2))


def cmd_status(args: argparse.Namespace) -> None:
    loop = AutoresearchLoop.load()
    print(json.dumps(loop.to_summary(), indent=2))


def cmd_add_hypotheses(args: argparse.Namespace) -> None:
    loop = AutoresearchLoop.load()
    hypotheses = []
    for line in args.hypotheses.split(";"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(":", 2)
        if len(parts) < 2:
            continue
        hid = parts[0].strip()
        desc = parts[1].strip()
        dim = parts[2].strip() if len(parts) > 2 else "model-logic"
        hypotheses.append(Hypothesis(id=hid, description=desc, target_file="", dimension=dim))
    loop.data.hypotheses.extend(hypotheses)
    loop.save()
    print(json.dumps({"added": len(hypotheses), "total": len(loop.data.hypotheses)}, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Autoresearch loop controller")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # init
    p_init = subparsers.add_parser("init", help="Initialize a new loop")
    p_init.add_argument("--target", required=True)
    p_init.add_argument("--metric", default="scan_latency_ms_median")
    p_init.add_argument("--dimensions", default="model-logic")
    p_init.add_argument("--max-rounds", type=int, default=10)
    p_init.add_argument("--max-duration", type=int, default=240)
    p_init.add_argument("--baseline-latency", type=float, required=True)
    p_init.add_argument("--baseline-commit", default=None)
    p_init.add_argument("--baseline-metrics", required=True)
    p_init.set_defaults(func=cmd_init)

    # build
    p_build = subparsers.add_parser("build", help="Run headless build")
    p_build.add_argument("--workspace", type=Path, default=Path("runs") / "latest")
    p_build.set_defaults(func=cmd_build)

    # benchmark-launch
    p_blaunch = subparsers.add_parser("benchmark-launch", help="Launch external benchmark")
    p_blaunch.add_argument("--workspace", type=Path, default=Path("runs") / "latest")
    p_blaunch.set_defaults(func=cmd_benchmark_launch)

    # benchmark-poll
    p_bpoll = subparsers.add_parser("benchmark-poll", help="Poll benchmark status")
    p_bpoll.add_argument("--status-file", type=Path, default=None)
    p_bpoll.set_defaults(func=cmd_benchmark_poll)

    # decide
    p_decide = subparsers.add_parser("decide", help="Compare metrics and decide keep/discard")
    p_decide.add_argument("--metrics-path", type=Path, required=True)
    p_decide.set_defaults(func=cmd_decide)

    # status
    p_status = subparsers.add_parser("status", help="Show loop status")
    p_status.set_defaults(func=cmd_status)

    # add-hypotheses
    p_hypo = subparsers.add_parser("add-hypotheses", help="Add hypothesis queue")
    p_hypo.add_argument("--hypotheses", required=True, help='Format: "h1:desc1:dim1;h2:desc2:dim2"')
    p_hypo.set_defaults(func=cmd_add_hypotheses)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
