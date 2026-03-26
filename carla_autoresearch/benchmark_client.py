from __future__ import annotations

import argparse
import json
import queue
import statistics
import time
from pathlib import Path

from carla_autoresearch.controller import build_metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a fixed CARLA LiDAR benchmark.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--map", dest="map_name", default="Town05")
    parser.add_argument("--warmup-scans", type=int, default=20)
    parser.add_argument("--measured-scans", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--lidar-attr",
        action="append",
        default=[],
        help="key=value sensor attribute, may be repeated",
    )
    return parser.parse_args()


def parse_lidar_attributes(items: list[str]) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep:
            raise ValueError(f"Invalid lidar attribute: {item}")
        attrs[key] = value
    return attrs


def import_carla():
    try:
        import carla  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only in real CARLA env
        raise SystemExit(
            "Failed to import carla. Run this script inside the packaged Python API "
            "environment or a conda env that exposes the CARLA Python module."
        ) from exc
    return carla


def pick_vehicle_blueprint(blueprints):
    preferred = blueprints.filter("vehicle.synkrotron.democar")
    if preferred:
        return preferred[0]
    vehicles = blueprints.filter("vehicle.*")
    if not vehicles:
        raise RuntimeError("No vehicle blueprint available for LiDAR attachment")
    return vehicles[0]


def benchmark(args: argparse.Namespace) -> dict[str, object]:
    carla = import_carla()
    client = carla.Client(args.host, args.port)
    client.set_timeout(20.0)
    world = client.load_world(args.map_name)

    original_settings = world.get_settings()
    blueprint_library = world.get_blueprint_library()
    vehicle = None
    lidar = None

    try:
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = 0.1
        world.apply_settings(settings)

        spawn_points = world.get_map().get_spawn_points()
        if not spawn_points:
            raise RuntimeError("No spawn points available in selected map")

        vehicle_bp = pick_vehicle_blueprint(blueprint_library)
        vehicle = world.spawn_actor(vehicle_bp, spawn_points[0])
        vehicle.set_simulate_physics(False)

        lidar_bp = blueprint_library.find("sensor.lidar.ray_cast")
        for key, value in parse_lidar_attributes(args.lidar_attr).items():
            lidar_bp.set_attribute(key, value)
        lidar_transform = carla.Transform(carla.Location(x=0.0, z=2.5))
        lidar = world.spawn_actor(lidar_bp, lidar_transform, attach_to=vehicle)

        scan_queue: queue.Queue[tuple[float, int]] = queue.Queue()

        def on_scan(point_cloud):
            point_count = len(point_cloud)
            scan_queue.put((time.perf_counter(), point_count))

        lidar.listen(on_scan)

        for _ in range(args.warmup_scans):
            world.tick()
            scan_queue.get(timeout=5.0)

        latencies_ms = []
        point_counts = []
        for _ in range(args.measured_scans):
            start = time.perf_counter()
            world.tick()
            received_at, point_count = scan_queue.get(timeout=5.0)
            latencies_ms.append((received_at - start) * 1000.0)
            point_counts.append(point_count)

        metrics = build_metrics(
            latencies_ms=latencies_ms,
            point_counts=point_counts,
            map_name=args.map_name,
            sensor_blueprint="sensor.lidar.ray_cast",
            warmup_scans=args.warmup_scans,
            measured_scans=args.measured_scans,
        )
        return {
            "map": metrics.map_name,
            "sensor_blueprint": metrics.sensor_blueprint,
            "scan_latency_ms_median": metrics.scan_latency_ms_median,
            "scan_latency_ms_p95": metrics.scan_latency_ms_p95,
            "point_count_baseline": metrics.point_count_baseline,
            "point_count_all_equal": metrics.point_count_all_equal,
            "warmup_scans": metrics.warmup_scans,
            "measured_scans": metrics.measured_scans,
            "status": metrics.status,
            "scan_latency_ms_mean": statistics.fmean(latencies_ms),
        }
    finally:
        if lidar is not None:
            lidar.stop()
            lidar.destroy()
        if vehicle is not None:
            vehicle.destroy()
        world.apply_settings(original_settings)


def main() -> None:
    args = parse_args()
    result = benchmark(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
