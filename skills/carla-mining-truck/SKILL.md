---
name: carla-mining-truck
description: 读取和配置 CARLA MiningTruck 容量、载荷、举升/下降耗时及 bucket/overall/driving state，执行 lift/lower；道路行驶与挖掘机联动作业分流。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 矿卡装载与举升

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先确认返回 actor 真是 `carla.MiningTruck` 与资产支持，不对普通 vehicle 调 lift。只读 `get_config()` 返回 capacity/lift_duration/lower_duration；`get_state()` 返回 overall_state/driving_state/bucket_state/current_load/current_loading_progress/current_loading_num。

独立原生任务自有矿卡先保存 config；修改副本后 `set_config(config)`。`set_current_load(current_load)` 改载荷状态，不能当真实装载测量；capacity/载荷的实际单位由实现/资产确认，数值先要求有限、非负并符合模型范围。`lift()`、`lower()` 启动作业，调用返回不代表耗时结束。

在有界世界帧内跟踪 bucket/overall 状态与 elapsed time，报告完成、仍进行或超时；不要瞬间 lift/lower 互发。行驶状态与举斗条件冲突时停止定位，不绕过资产状态机。结束撤销本任务作业、恢复 config 或销毁自有矿卡；挖机绑定需另一专项协调解绑，不能单独删被外部作业使用的车辆。

## 交接与证据

[carla-excavator](../carla-excavator/SKILL.md)；[carla-vehicle-control](../carla-vehicle-control/SKILL.md)；[carla-actors](../carla-actors/SKILL.md)；[carla-clock](../carla-clock/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
