# Conversation Recap - autoresearch

## Conversation Summary
当前对话已把 `autoresearch` 从 LLM 训练示例改造成面向 CARLA `ray_cast` LiDAR 的外部优化控制器，并完成了控制器、benchmark client、实验入口与规则文档的第一版实现。随后完成了真实联调、点云点数一致性复测、CARLA 流程 guardrail 记录，以及第一轮性能优化补丁在 `CarlaUE5` 独立分支上的落地。

## Current Objective
在 `CarlaUE5` 的 `feature/carla-lidar-optimization` 分支上继续推进 LiDAR 性能优化；本轮由用户手动执行 `package`，完成后由助手接手服务端/客户端测试与 benchmark。

## Key Decisions
- 目标 codebase 是 `/media/yhr/2T/CarlaUE5`，控制器仓库仍是 `/media/yhr/2T/autoresearch`。
- 固定 benchmark 合同：`Town05`、`sensor.lidar.ray_cast`、静态 ego + 静态 lidar、主指标 `scan_latency_ms_median`。
- 当前优化范围先限制在 `RayCastLidar*`、`RayCastSemanticLidar*`、`LidarDescription.h`。
- 真实联调时，服务端和客户端都优先在真正的新桌面终端里运行；客户端必须先激活 `py38`。
- 当前已有活跃 `CarlaServer` 时优先复用，不重复启动第二个实例。
- 若未来修改范围扩大到 `LibCarla` 或 `PythonAPI`，则每次 `package` 后客户端启动前必须在 `py38` 里 `pip install ...carla-0.10.0-cp38-cp38-linux_x86_64.whl --force-reinstall`。
- 当前第一轮性能优化补丁是把 `RayCastSemanticLidar::SimulateLidar` 中每条射线重复读取的 `GetTransform()/Rotator()/Range` 提到外层，只保留 trace 本身。
- `CarlaUE5` 中这轮优化改动落在分支 `feature/carla-lidar-optimization`，不再继续落在 `wheeled_robot`。

## Constraints
- 当前用户要求本轮先手动执行 `package`，自动化 `package` 流程先记住但暂不用于本轮。
- 不要用临时内联脚本绕过正式入口来验证正式工作流行为。
- 自动化 `package` 通过 `gnome-terminal` 直接传长 payload 不稳定；当前已实现 launcher `.sh` 方案，但本轮先不启用。
- 任何性能优化都不能破坏点云点数一致性或 benchmark 合同。

## Open Questions
- 当前没有新的产品/范围问题；下一步取决于用户何时完成手动 `package` 并交还测试阶段。

## Pending Follow-Ups
- 等用户手动完成 `package` 后，运行正式测试链路：复用现有 `CarlaServer` 或按正确方式启动服务端，再在新桌面终端激活 `py38` 运行正式 `benchmark_client.py`。
- 取得第一轮最小优化补丁的正式 benchmark 结果，再决定是否继续叠加第二个优化点。
- 如果自动化 `package` 之后还要继续使用，需要继续排查 `gnome-terminal` 从 Python 直接执行 payload 的不稳定问题；当前推荐方向是 workspace launcher `.sh`。

## Known Issues
- 自动化 `package` 的“Python 直接拉起 `gnome-terminal` 并传 payload”路径不稳定，表现为新终端一闪而过且不生成 `build.log/build.exitcode`。
- 之前完整实验曾因活跃 `UnrealBuildTool` 冲突失败；当前已确认冲突实例可清理，但后续仍需注意。
- `CarlaUE5` 工作树里除当前两处 LiDAR 修改外，还存在其他与本任务无关的未跟踪文件和目录。

## Key Context
- 当前控制器仓库分支：`feature/carla-lidar-autoresearch`。
- 当前目标仓库分支：`feature/carla-lidar-optimization`。
- 会话存档名和 planning 名统一使用 `autoresearch`。
- 当前有价值的规则文档：
  - `docs/agent-system/mistake-patterns.md`
  - `.agent-state/rules/mistakes.md`
- 当前点数一致性复测结果曾在正式 `benchmark_client.py` 路径下验证通过，`point_count_all_equal=true`。
