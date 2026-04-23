# Task Plan

## Goal

实现并稳定运行一个可用的 CARLA LiDAR 自动实验控制面，同时在 `CarlaUE5` 的独立优化分支上推进 LiDAR 模型性能优化，并把每一轮结果沉淀到 planning 文档。

## Phases

- [completed] Phase 1: 确认目标代码位置、构建方式、运行方式和 benchmark 决策
- [completed] Phase 2: 为控制器核心行为编写失败测试
- [completed] Phase 3: 实现 `carla_autoresearch` 控制器与 benchmark client
- [completed] Phase 4: 改写 `README.md` 和 `program.md` 以切换到 CARLA 工作流
- [completed] Phase 5: 跑通真实联调、修正自动化流程问题，并完成 `ray_cast` 主线的前两轮有效优化
- [completed] Phase 6: 在 `CarlaUE5` 独立分支上提交 `opt1` 与 `opt2`
- [completed] Phase 7: 验证 `opt3` 并判定为 discard
- [completed] Phase 8: 切换到 `RayCastMemsLidar + AT128` 新主线，建立新基线
- [completed] Phase 9: 在 `ray_cast_mems + AT128` 新主线上完成第一轮优化与验证（`mems-opt1 discard`）
- [completed] Phase 10: 完成第二轮优化与验证（`mems-opt2 keep`，已提交 `bba122da`）
- [completed] Phase 11: 完成第三轮优化与验证（`mems-opt3 discard`）
- [completed] Phase 12: 设计并实现 `autoresearch-loop` skill（Step 1-6）
  - Step 1: `controller.py` — 添加 `HeadlessBuildAdapter`、`write/read_status_file`、`ExperimentDecisionExtended`
  - Step 2: `experiment.py` — 添加 `--status-file` 和 `--headless-build` CLI flags
  - Step 3: `external_runner.sh` — 创建 async server+benchmark launcher
  - Step 4: `loop.py` — 创建状态机 + 循环控制器 + CLI（init/build/benchmark-launch/benchmark-poll/decide/status）
  - Step 5: `autoresearch-loop/SKILL.md` — skill 定义（项目级，软链接到 `.claude/skills/`）
  - Step 6: `tests/test_loop.py` — 22 个单元测试全部通过
- [pending] Phase 13: Step 7 Validation — dry-run + 真实 end-to-end 循环验证

## Notes

- Conversation identifier fixed as `autoresearch`
- 会话存档名与 planning 目录统一使用 `autoresearch`
- 根目录 legacy planning files 已删除；后续只更新此目录
- `CarlaUE5` 当前优化分支：`feature/carla-lidar-optimization`
- `autoresearch` 当前控制器分支：`feature/carla-lidar-autoresearch`
- 当前工作方式已恢复为全自动流程：自动 `package`、自动起服务端、自动跑客户端；但如果流程异常，允许临时切回手动接管测试阶段
