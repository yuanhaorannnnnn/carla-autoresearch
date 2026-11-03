---
name: carla-benchmark
description: 在固定 CARLA workload 下执行基准或候选测量，保留配置、原始帧和观测口径；baseline/candidate 是试验角色，不自动搜索参数或宣布最优结果。
metadata:
  category: research
  execution: workflow
  operations: capture.run,research.status
---

# 固定条件测量

读[共享规则](../../references/carla-agent-shared.md)与[研究契约](../../references/carla-research.md)。明确本次是单配置采样还是正式研究中的 trial，避免把两类产物混为一套证据。

**单配置测量：**按 [capture](../carla-capture/SKILL.md) 检查实际 map、vehicle、sensor、attributes、步长、warmup、帧数，再运行 `capture.run`。在独立说明中记录 baseline/candidate 角色和配置来源，不编辑 capture 原始 manifest/metrics。当前 capture 只封装 RGB/RayCast；RGB 不自动具备研究控制器的 LiDAR 有效性评价。采集自管 session，不能先开手工 session。

**正式配对试验：**由 [parameter-search](../carla-parameter-search/SKILL.md) 启动的控制器安排 baseline/candidate 顺序、独立重复与确认。本 skill 解释并核验 trial，不直接调用私有 `_execute`、伪造 trial.json 或在运行中的研究旁追加采集。当前没有独立 `benchmark run` CLI；正式 trial 的唯一写入者仍为控制器。

逐轮保留：profile/二进制与 episode 身份、map、完整 recipe、角色、采集错误、原始文件、frame/timestamp、指标单位和清理结果。固定输入一致也不能自动证明天气/scene/seed 已完整受控；缺少的 provenance 显式列出。warmup 不计入正式帧；同轮相邻帧可能相关，不能冒充独立样本。

`tick_to_sensor_callback_ms` 是本机 tick 起点到相应 callback 的软件路径延迟；不是 GPU kernel 时间或物理传感器延迟。点数下降可能带来 tradeoff，不能靠“更快”断言质量保持。单次采集仅交付测量，不给 keep；正式 run 的比较转 [compare](../carla-compare/SKILL.md)。

依据：`src/carla_agent/worker.py` capture；`src/carla_agent/research.py` _specs/_validate_capture/_execute。
