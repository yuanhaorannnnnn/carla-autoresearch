# autoresearch

This repo now acts as a CARLA LiDAR optimization control plane.

## Setup

Before running any experiment:

1. Work on a dedicated branch.
2. Read these files first:
   - `README.md`
   - `program.md`
   - `carla_autoresearch/controller.py`
   - `carla_autoresearch/benchmark_client.py`
3. Confirm the target codebase exists at `/media/yhr/2T/CarlaUE5`.
4. Confirm `/media/yhr/2T/CarlaUE5/package.sh` builds a Shipping package.
5. Confirm the packaged CARLA server can be launched from:
   - `/media/yhr/2T/CarlaUE5/Build/Package/Carla-0.10.0-Linux-Shipping/Linux`
6. Confirm the `py38` conda environment can import `carla`.
7. Keep `results.tsv` untracked.

## Experiment Target

The optimization target is not this repo's Python internals. The target is the external CARLA code under:

- `/media/yhr/2T/CarlaUE5/Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Sensor/RayCastLidar.cpp`
- `/media/yhr/2T/CarlaUE5/Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Sensor/RayCastLidar.h`
- `/media/yhr/2T/CarlaUE5/Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Sensor/RayCastSemanticLidar.cpp`
- `/media/yhr/2T/CarlaUE5/Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Sensor/RayCastSemanticLidar.h`
- `/media/yhr/2T/CarlaUE5/Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Sensor/LidarDescription.h`

Only touch `ActorBlueprintFunctionLibrary.cpp` when an additional lidar attribute must be surfaced explicitly.

## Fixed Benchmark Contract

- Map: `Town05`
- Sensor: `sensor.lidar.ray_cast`
- Mode: static ego + static lidar
- Metric: `scan_latency_ms_median`
- Correctness: all measured scans must have identical point counts, and that count must match the baseline

Use explicit lidar attributes instead of relying on blueprint defaults.

## Experiment Loop

1. Modify the target CARLA lidar code.
2. Run one experiment through:
   - `python3 -m carla_autoresearch.experiment --workspace runs/latest --description "<short note>"`
3. If this is the first run, treat the output `metrics.json` as baseline.
4. For candidate runs, pass `--baseline-metrics <path>`.
5. If you are doing manual validation and an active CarlaServer already exists, prefer reusing it instead of starting another one. For the controller entrypoint, use `--reuse-existing-server` only when you explicitly want that behavior.
6. Read the controller result:
   - `keep`: latency improved and point count stayed exactly valid
   - `discard`: run succeeded but no valid improvement
   - `crash`: build/run/metric extraction failed
7. Append all runs to `results.tsv`.
8. If the code changes touched `LibCarla`, `PythonAPI`, or any path that changes the generated Python wheel, then before starting the client you must:
   - activate `py38`
   - run:
     `pip install /media/yhr/2T/CarlaUE5/Build/PythonAPI/dist/carla-0.10.0-cp38-cp38-linux_x86_64.whl --force-reinstall`
   - only then launch the client script

## Guardrails

- Do not silently widen the optimization scope beyond the allowed CARLA files.
- Do not change map, benchmark shape, or correctness rules mid-loop.
- Do not accept a faster run if point count changed.
- Prefer simpler LiDAR code when gains are similar.
- Do not validate official workflow behavior with ad-hoc inline scripts that duplicate `benchmark_client.py`; if extra observation is needed, add it to the official path first.
- If the current change modifies `LibCarla` or Python bindings, do not reuse an old installed `carla` wheel when validating the client path.
