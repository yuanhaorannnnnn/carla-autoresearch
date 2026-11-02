---
name: carla-parameter-search
description: 按冻结计划编排 CARLA 有限参数候选、独立重复与确认、预算和停止恢复；用于已授权的 Auto Research。复用基础采集，不自动改源码、构建、发布或把获胜参数写为默认。
metadata:
  category: research
  execution: cli
  operations: research.validate,research.start,research.status,research.stop,research.resume,research.report
---

# 有限参数搜索

先由 [research-plan](../carla-research-plan/SKILL.md) 完成条件和预算，读[研究契约](../../references/carla-research.md)。当前只支持同一现成构建的 RayCast LiDAR 参数 tradeoff；不得改用 native sensor runner 扩大控制器覆盖范围。

先 `research validate --plan plan.json` 做离线检查。执行前用真实 profile 核对 exclusive、expected_server_version、server_pid、RPC 端口/进程身份、map、episode，确保没有其他实验/session。验证通过不自动授权开始；既有任务已授权实验时不逐轮重复询问。

```bash
carla-agent research start --plan plan.json
carla-agent research status --run /absolute/run
carla-agent research stop --run /absolute/run
carla-agent research resume --run /absolute/run --retry-interrupted
```

start 默认后台，返回 run 与启动状态，不等于完成；需要前台可显式加 `--foreground`。后台控制器通过相同 `bridge.invoke(capture.run)` 执行试验；不再手动创建车辆、重复采集或修改 metrics/state 文件。plan/profile 的源码和冻结副本、server/episode 变化都会影响恢复，不能修改记录绕过冲突。

候选仅改变 allowed_attributes，baseline/candidate 交错重复，选择后另做确认；失败轮次和未完成 trial 均保留。stop 是停止请求，当前有界 trial 与清理可能尚在执行；用 status 核对终态。resume 需要显式 retry 标记，未完成轮次用新目录重新采集，预算不重置。身份不明或旧 orphan 仍存活时保留证据，不杀端口、不接管另一实例。

终态使用 [compare](../carla-compare/SKILL.md) 只读复核，report 查看持久报告。没有合格候选、预算不足、质量未过或波动过大时如实给结论；不能删除失败只展示最佳一次。推荐配置保留为结果，应用配置、源码修改与发布是后续独立动作。

依据：`src/carla_agent/research.py` _prepare/_execute/_recover_trials/dispatch；底层操作 [benchmark](../carla-benchmark/SKILL.md)、[capture](../carla-capture/SKILL.md)。
