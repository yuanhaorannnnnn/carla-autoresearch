# Conversation Recap - autoresearch

## Conversation Summary
当前对话已把 `autoresearch` 改造成面向 CARLA LiDAR 的外部优化控制器，并完成了控制器、benchmark client、实验入口、planning 迁移和 harness state 跟踪。`ray_cast` 主线已完成三轮尝试，其中 `opt1`、`opt2` 有效并已提交到 `CarlaUE5`，`opt3` 因点数一致性失守被判 discard；当前主线已切到 `RayCastMemsLidar + AT128`，并已完成新基线建立及前两轮优化验证。

## Current Objective
在 `CarlaUE5` 的 `feature/carla-lidar-optimization` 分支上，继续推进 `RayCastMemsLidar + AT128` 主线的后续性能优化。

## Key Decisions
- 目标 codebase 是 `/media/yhr/2T/CarlaUE5`，控制器仓库仍是 `/media/yhr/2T/autoresearch`。
- 当前固定 benchmark 合同仍是 `Town05`、静态 ego + 静态 lidar、主指标 `scan_latency_ms_median`。
- 当前新主线的默认测试目标已切到 `sensor.lidar.ray_cast_mems`，模式固定为 `AT128`，并显式设置 `scanning_patterns=AT128`、`beams_num=153600`。
- 在 `ray_cast` 主线中：
  - `opt1` 已提交：`e3c58fed7`
  - `opt2` 已提交：`8d1ef242e`
  - `opt3` 已验证并判定为 `discard`
- 在 `ray_cast_mems + AT128` 主线中：
  - 基线已建立，点数基准约为 `121535`
  - `mems-opt1` 已验证并判定为 `discard`
  - `mems-opt2` 已验证并可判定为 `keep`
- 真实联调时，服务端和客户端都优先在真正的新桌面终端里运行；客户端必须先激活 `py38`。
- 当前已有活跃 `CarlaServer` 时优先复用，不重复启动第二个实例。
- 若未来修改范围扩大到 `LibCarla` 或 `PythonAPI`，则每次 `package` 后客户端启动前必须在 `py38` 里 `pip install ...carla-0.10.0-cp38-cp38-linux_x86_64.whl --force-reinstall`。
- `CarlaUE5` 中所有 LiDAR 优化改动落在分支 `feature/carla-lidar-optimization`，不再继续落在 `wheeled_robot`。

## Constraints
- 不要用临时内联脚本绕过正式入口来验证正式工作流行为。
- 自动化 `package` 现在通过 launcher `.sh` 方案执行；`conda.sh` 使用固定绝对路径，且 launcher 头部为 `set -eo pipefail`。
- 任何性能优化都不能破坏点云点数一致性或 benchmark 合同。

## Open Questions
- 当前没有新的产品/范围问题；下一步是决定 `mems-opt2` 是否提交，并选择下一轮 `ray_cast_mems + AT128` 优化点。

## Pending Follow-Ups
- 提交 `mems-opt2` 到 `CarlaUE5` 分支。
- 在 `ray_cast_mems + AT128` 主线上选择并验证下一轮优化点。
- 继续保证每一轮优化无论成功失败都写回 planning 文档与必要的 harness state。

## Known Issues
- `opt3` 虽然性能更好，但破坏了点云一致性，当前不应保留为有效结果。
- 之前完整实验曾因活跃 `UnrealBuildTool` 冲突失败；当前已确认冲突实例可清理，但后续仍需注意。
- `CarlaUE5` 工作树里除当前两处 LiDAR 修改外，还存在其他与本任务无关的未跟踪文件和目录。

## Key Context
- 当前控制器仓库分支：`feature/carla-lidar-autoresearch`。
- 当前目标仓库分支：`feature/carla-lidar-optimization`。
- 会话存档名和 planning 名统一使用 `autoresearch`。
- 当前有价值的规则文档：
  - `docs/agent-system/mistake-patterns.md`
  - `.agent-state/rules/mistakes.md`
- `ray_cast` 主线最新可保留结果是 `opt2`：`38.51826800382696 ms`，`point_count_all_equal=true`
- `ray_cast_mems + AT128` 当前基线约为 `50.217416000123194 ms`
- `mems-opt2` 当前结果：`48.598930499792914 ms`，在 `±1` 点容差口径下 `point_count_all_equal=true`
