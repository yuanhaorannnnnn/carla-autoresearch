# autoresearch

这个仓库现在作为一个外部实验控制器，驱动 `/media/yhr/2T/CarlaUE5` 中的 `CARLA` `ray_cast` LiDAR 代码做自动 benchmark 和 keep/discard 优化，而不是直接承载被优化的 Unreal 代码。

## What This Repo Does

当前实现聚焦于 `sensor.lidar.ray_cast` 的第一版自动实验闭环：

- 构建目标工程：调用 `/media/yhr/2T/CarlaUE5/package.sh`
- 启动 Shipping 服务端：
  `/media/yhr/2T/CarlaUE5/Build/Package/Carla-0.10.0-Linux-Shipping/Linux/CarlaUnreal.sh`
- 运行非交互 benchmark client
- 收集固定 benchmark 指标
- 基于单扫描延迟和点数完整性做 `keep/discard/crash`

## Fixed Benchmark Decisions

- Map: `Town05`
- Sensor blueprint: `sensor.lidar.ray_cast`
- Runtime: Shipping package + headless server
- Benchmark shape: static ego + static lidar
- Primary metric: `scan_latency_ms_median`
- Correctness rule: every measured scan must have the same point count as the baseline

## Project Structure

```text
carla_autoresearch/controller.py      - CARLA path config, command adapter, decision logic
carla_autoresearch/benchmark_client.py - non-interactive CARLA benchmark client
carla_autoresearch/experiment.py      - one-shot experiment entrypoint
program.md                            - agent instructions for this CARLA workflow
tests/test_carla_controller.py        - controller-level tests
```

## Quick Start

先确保：

- `/media/yhr/2T/CarlaUE5` 可以执行 `./package.sh`
- Shipping 包已经能正常启动
- `py38` conda 环境里可以导入 `carla`

然后在本仓库中运行：

```bash
# 1. 运行测试
python3 -m unittest tests.test_carla_controller

# 2. 执行一次基线或候选实验
python3 -m carla_autoresearch.experiment \
  --workspace runs/latest \
  --description "manual baseline"
```

如果已有基线指标文件，再传入：

```bash
python3 -m carla_autoresearch.experiment \
  --workspace runs/latest \
  --baseline-metrics runs/baseline/metrics.json \
  --description "candidate change"
```

如果当前已经有活跃的 `CarlaServer` 在运行，并且你确认要复用它，而不是拉起新的实例，可以改用：

```bash
python3 -m carla_autoresearch.experiment \
  --workspace runs/latest \
  --baseline-metrics runs/baseline/metrics.json \
  --reuse-existing-server \
  --description "candidate change"
```

## Target Code Scope

第一版优化默认只面向以下目标代码区域：

- `RayCastLidar.cpp/.h`
- `RayCastSemanticLidar.cpp/.h`
- `LidarDescription.h`

如果需要暴露额外参数，才最小化触碰 `ActorBlueprintFunctionLibrary.cpp`。

## Notes

- 这个仓库不会自动修改 `/media/yhr/2T/CarlaUE5` 之外的 Unreal 工程组织结构。
- 第一版 benchmark 不覆盖动态轨迹、多地图或 GPU LiDAR 路径。
- `runs/` 和 `results.tsv` 默认作为实验产物，不进版本控制。
- 真实联调时，服务端和客户端都优先在真正的新桌面终端里运行；客户端先激活 `py38` 再执行。
- 如果当前已有活跃 `CarlaServer`，手动验证和 smoke test 优先复用，不要重复拉起第二个实例。
- 验证正式流程时，不要用临时内联脚本复制 `benchmark_client.py` 逻辑。
