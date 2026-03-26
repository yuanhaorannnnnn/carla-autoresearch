# Task Plan

## Goal

实现一个可运行的 CARLA LiDAR 自动实验控制面，包括构建/运行适配器、benchmark client、指标判定、结果记录，以及与当前仓库入口文档的对齐。

## Phases

- [completed] Phase 1: 确认目标代码位置、构建方式、运行方式和 benchmark 决策
- [completed] Phase 2: 为控制器核心行为编写失败测试
- [completed] Phase 3: 实现 `carla_autoresearch` 控制器与 benchmark client
- [completed] Phase 4: 改写 `README.md` 和 `program.md` 以切换到 CARLA 工作流
- [in_progress] Phase 5: 运行真实联调、修正流程问题，并开始第一轮性能优化验证
- [pending] Phase 6: 在 `CarlaUE5` 的独立优化分支上获得第一轮性能补丁的正式 benchmark 结果

## Notes

- Conversation identifier fixed as `autoresearch`
- 会话存档名与 planning 目录统一使用 `autoresearch`
- 根目录 legacy planning files 已删除；后续只更新此目录
- 当前轮次由用户手动执行 `package`，助手在其后接手服务端/客户端测试与 benchmark
