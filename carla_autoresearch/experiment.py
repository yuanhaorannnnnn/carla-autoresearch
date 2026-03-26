from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from carla_autoresearch.controller import (
    CarlaPaths,
    CarlaTargetAdapter,
    ExperimentController,
    write_results_row,
)


def current_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one CARLA LiDAR optimization experiment.")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path("runs") / "latest",
        help="Directory for build/server/benchmark logs and metrics",
    )
    parser.add_argument(
        "--baseline-metrics",
        type=Path,
        default=None,
        help="Existing baseline metrics.json. If omitted, current run becomes the baseline.",
    )
    parser.add_argument(
        "--results-file",
        type=Path,
        default=Path("results.tsv"),
        help="TSV ledger for experiment results",
    )
    parser.add_argument(
        "--description",
        default="manual run",
        help="Short description recorded in results.tsv",
    )
    parser.add_argument(
        "--reuse-existing-server",
        action="store_true",
        help="Reuse an already running CarlaServer instead of launching a new one",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    adapter = CarlaTargetAdapter(CarlaPaths())
    controller = ExperimentController(adapter)
    metrics, decision = controller.run_once(
        workspace=args.workspace,
        baseline_metrics_path=args.baseline_metrics,
        reuse_existing_server=args.reuse_existing_server,
    )

    metrics_path = args.workspace / "metrics.json"
    write_results_row(
        path=args.results_file,
        commit=current_commit(),
        metrics=metrics,
        status=decision.status,
        description=args.description,
    )
    print(f"status: {decision.status}")
    print(f"reason: {decision.reason}")
    print(f"metrics: {metrics_path}")


if __name__ == "__main__":
    main()
