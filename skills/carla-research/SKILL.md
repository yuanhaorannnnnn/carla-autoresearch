---
name: carla-research
description: 兼容旧 carla-research 入口，仅在显式指定旧名称或研究意图尚未细分时使用；按目标路由到实验设计、固定测量、只读比较或有限参数搜索。
metadata:
  category: compatibility
  execution: alias
  operations: ''
---

# 旧研究入口路由

- 设计假设、指标、质量/噪声阈值和预算 → [research-plan](../carla-research-plan/SKILL.md)。
- 固定配置的 baseline/candidate 测量 → [benchmark](../carla-benchmark/SKILL.md)。
- 查看已有结果、核对证据、离线比较 → [compare](../carla-compare/SKILL.md)。
- 有界候选探索、开始/停止/恢复 → [parameter-search](../carla-parameter-search/SKILL.md)。

原 `research start/status/stop/resume/report` 命令保留；新增 `research validate/compare` 区分离线准备和只读核验。读取[研究契约](../../references/carla-research.md)，不在此重复实现状态机或采集流程。不因用户问研究结果自动开启实验。
