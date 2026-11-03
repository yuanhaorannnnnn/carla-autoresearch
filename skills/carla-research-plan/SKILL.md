---
name: carla-research-plan
description: 把 CARLA 实验问题转成冻结 workload、允许变量、有效性与比较条件、独立确认和预算，并离线校验计划；不因设计实验自动启动仿真。执行和候选搜索交 benchmark/parameter-search。
metadata:
  category: research
  execution: cli
  operations: research.validate
---

# 定义可比较的实验

先读[研究契约](../../references/carla-research.md)。从用户实际问题定义观测量、变化项与保持项；使用来源明确的质量底线、改善阈值和噪声范围，不能倒推最容易通过的条件。缺少这些决定时先给出可核对方案，尚未有依据的字段不能填成“默认5%”。

当前控制器仅支持 `sensor.lidar.ray_cast` 的有限属性候选与 `tick_to_sensor_callback_ms`、`tradeoff` 有效性。其他 sensor、GPU 内核时间、几何语义保持、跨构建比较不能用改字符串假装接通。

读取 `carla-agent schema research.validate` 后写 plan JSON。`profile` 相对 plan 文件解析；workload 含当前 map、明确 sensor 属性、frames/warmup/fixed delta；allowed_attributes 必须已在 baseline 中出现，候选只覆盖这些字段。质量和比较阈值都保留 threshold_source。独立 trial 才是统计重复单位，连续帧不是重复实验。

```bash
carla-agent research validate --plan plan.json
```

该命令只校验 plan/profile 与预算数量，不连接 CARLA、不创建 run、不冻结文件。`simulator_checked:false` 必须如实保留；valid 不证明 blueprint、地图、进程或包版本实际支持。预算不足时按返回的选择/确认轮数说明差额，不能擅自减少重复或跳过确认。

计划获准执行后转 [parameter-search](../carla-parameter-search/SKILL.md)；只做固定配置测量转 [benchmark](../carla-benchmark/SKILL.md)。正式 start 时控制器冻结 plan/profile 与实例身份；之后变更条件应建新研究，不能原地改已有 run 的冻结输入。

依据：`src/carla_agent/research.py` 的 validate_plan/validate_request/plan_schema/_prepare；[基础采集](../carla-capture/SKILL.md)。
