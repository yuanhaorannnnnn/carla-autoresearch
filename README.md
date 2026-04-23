# autoresearch

这个仓库现在作为一个外部实验控制器，驱动 `/media/yhr/2T/CarlaUE5` 中的 `CARLA` LiDAR 代码做自动 benchmark 和 keep/discard 优化，而不是直接承载被优化的 Unreal 代码。当前支持 `sensor.lidar.ray_cast` 和 `sensor.lidar.ray_cast_mems` 两条主线。

## What This Repo Does

当前实现支持两种工作模式：

1. **手动单轮实验**（`experiment.py`）：一次 build + benchmark + decision
2. **自动优化闭环**（`autoresearch-loop` skill）：AI 生成假设 → 自动 patch → build → benchmark → keep/discard → 迭代

两种模式共享同一套底层组件（build adapter、benchmark client、decision logic）。

```
┌──────────────────────────────────────────────────────────────────────────┐
│  User: provides optimization config (target, metric, dimensions)         │
└─────────────────────────────┬────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  autoresearch-loop skill (AI layer)                                      │
│  - Analyzes target code, generates hypothesis queue                      │
│  - Applies patches with Write/Edit tools                                 │
│  - Coordinates loop via loop.py CLI actions                              │
│  - Makes keep/discard decisions                                          │
└─────────────────────────────┬────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  carla_autoresearch/loop.py (mechanical layer)                           │
│  State machine: ANALYZING → PATCHING → BUILDING → BENCHMARKING          │
│  → ANALYZING_RESULTS → DECIDING → (loop or TERMINATED)                  │
│  - Persists state to .agent-state/autoresearch-loop-state.yaml          │
└─────────────┬───────────────┬───────────────┬────────────────────────────┘
              │               │               │
              ▼               ▼               ▼
┌─────────────────┐  ┌──────────────┐  ┌──────────────────────┐
│  HeadlessBuild  │  │ external_    │  │ ExperimentDecision   │
│  Adapter        │  │ runner.sh    │  │ (compare to baseline)│
│  - package.sh   │  │ - gnome-term │  │ - keep / discard     │
│    in subprocess│  │ - server +   │  │   / crash            │
│    (~10 min)    │  │   benchmark  │  │                      │
│                 │  │ - status.json│  │                      │
└─────────────────┘  └──────────────┘  └──────────────────────┘
```

## Fixed Benchmark Decisions

- Map: `Town05`
- Sensor blueprint: `sensor.lidar.ray_cast_mems`（当前主线，固定 AT128 模式）
- Runtime: Shipping package + headless server
- Benchmark shape: static ego + static lidar
- Primary metric: `scan_latency_ms_median`
- Correctness rule: every measured scan must have the same point count as the baseline
  （`ray_cast_mems` 容差 ±1 点，`ray_cast` 要求完全相等）

## Project Structure

```text
carla_autoresearch/controller.py         - CARLA path config, command adapter, decision logic,
                                           HeadlessBuildAdapter, ExperimentDecisionExtended,
                                           status file I/O
carla_autoresearch/benchmark_client.py   - non-interactive CARLA benchmark client
carla_autoresearch/experiment.py         - one-shot experiment entrypoint (--headless-build,
                                           --status-file flags)
carla_autoresearch/loop.py               - state machine, loop controller, CLI for
                                           init/build/benchmark-launch/benchmark-poll/decide/status
carla_autoresearch/external_runner.sh    - async server+benchmark launcher (gnome-terminal)
.claude/skills/autoresearch-loop/        - skill definition (symlink to agent-skills repo)
program.md                               - agent instructions for this CARLA workflow
tests/test_carla_controller.py           - controller-level tests
tests/test_loop.py                       - loop state machine and decision tests
```

## Quick Start

### Manual Single Experiment

先确保：

- `/media/yhr/2T/CarlaUE5` 可以执行 `./package.sh`
- Shipping 包已经能正常启动
- `py38` conda 环境里可以导入 `carla`

```bash
# 运行所有测试
python3 -m pytest tests/

# 执行一次基线实验
python3 -m carla_autoresearch.experiment \
  --workspace runs/latest \
  --description "manual baseline"

# 候选实验（对比基线）
python3 -m carla_autoresearch.experiment \
  --workspace runs/latest \
  --baseline-metrics runs/baseline/metrics.json \
  --description "candidate change"

# 复用已有 CarlaServer
python3 -m carla_autoresearch.experiment \
  --workspace runs/latest \
  --baseline-metrics runs/baseline/metrics.json \
  --reuse-existing-server \
  --description "candidate change"
```

### Automated Loop (autoresearch-loop skill)

触发词：`/autoresearch-loop` 或自然语言请求自动优化循环。

Loop CLI 命令参考：

```bash
# 初始化 loop
python3 -m carla_autoresearch.loop init \
  --target RayCastMemsLidar \
  --metric scan_latency_ms_median \
  --dimensions model-logic \
  --max-rounds 10 \
  --max-duration 240 \
  --baseline-latency 50.0 \
  --baseline-commit abc1234 \
  --baseline-metrics runs/baseline/metrics.json

# 添加假设队列
python3 -m carla_autoresearch.loop add-hypotheses \
  --hypotheses "h1:batch rays:model-logic;h2:reduce atomics:model-logic"

# 运行 build（阻塞，~10 min）
python3 -m carla_autoresearch.loop build --workspace runs/arl-xxx/r001

# 启动外部 benchmark（非阻塞）
python3 -m carla_autoresearch.loop benchmark-launch --workspace runs/arl-xxx/r001

# 轮询 benchmark 状态
python3 -m carla_autoresearch.loop benchmark-poll

# 做决策
python3 -m carla_autoresearch.loop decide --metrics-path runs/arl-xxx/r001/metrics.json

# 查看当前状态
python3 -m carla_autoresearch.loop status
```

## Target Code Scope

优化面向以下目标代码区域：

- `RayCastLidar.cpp/.h`
- `RayCastSemanticLidar.cpp/.h`
- `RayCastMemsLidar.cpp/.h`
- `LidarDescription.h`

如果需要暴露额外参数，才最小化触碰 `ActorBlueprintFunctionLibrary.cpp`。

## Notes

- 这个仓库不会自动修改 `/media/yhr/2T/CarlaUE5` 之外的 Unreal 工程组织结构。
- benchmark 不覆盖动态轨迹、多地图或 GPU LiDAR 路径。
- `runs/` 和 `results.tsv` 默认作为实验产物，不进版本控制。
- 真实联调时，服务端和客户端都优先在真正的新桌面终端里运行；客户端先激活 `py38` 再执行。
- 如果当前已有活跃 `CarlaServer`，手动验证和 smoke test 优先复用，不要重复拉起第二个实例。
- 验证正式流程时，不要用临时内联脚本复制 `benchmark_client.py` 逻辑。
- 如果后续改动范围扩大到 `LibCarla`、`PythonAPI` 或任何会改变 Python wheel 的代码，`package` 完成后启动客户端前必须先在 `py38` 环境里执行：
  `pip install /media/yhr/2T/CarlaUE5/Build/PythonAPI/dist/carla-0.10.0-cp38-cp38-linux_x86_64.whl --force-reinstall`
- 自动 loop 模式下，build 在 AI 进程中直接运行（headless，~10 min）；server + benchmark 在外部 gnome-terminal 中异步运行，AI 通过 `status.json` 轮询获取结果。
