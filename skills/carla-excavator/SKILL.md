---
name: carla-excavator
description: 配置 CARLA Excavator bucket/load、挖点卸点和装载速度，启动停止作业并绑定自有 MiningTruck；不替代矿卡行驶或完整土壤物理模拟。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 挖掘机装载作业

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

确认 `carla.Excavator` 资产与自有矿卡在同一原生任务/episode。`get_config()` 提供 model/bucket_capacity/bucket_loading_duration/truck_loading_duration/loading_speed_calculate_method/max_loading_speed/turning_radius/rear_overhang/safe_distance；保存后改副本 `set_config(config)`，枚举/单位按消费实现核对，不猜装载吨数。

`bind_mining_truck(mining_truck)` 输入 MiningTruck 对象，随后 `start(excavate_point,dump_point)`；两点均为世界坐标 `carla.Location`（米），不能把 Waypoint/Trajectory 直接传入。`get_state()` 返回 state/current_load/current_loading_progress/current_loading_num；跟踪目标矿卡 load 与作业状态，采用有界 frame/wall timeout。

超时、无法到达卸点、矿卡状态冲突、错误 actor 类型分别保留，不反复 start 重置进度。结束 `stop()`，`unbind_mining_truck()`，再清理自有对象；即使作业失败也报告解绑/清理结果。载荷状态变化不证明土壤体积守恒或挖掘物理准确。

## 交接与证据

[carla-mining-truck](../carla-mining-truck/SKILL.md)；[carla-actors](../carla-actors/SKILL.md)；[carla-clock](../carla-clock/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`、`LibCarla/source/carla/client/Excavator.h`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
