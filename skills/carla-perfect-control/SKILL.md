---
name: carla-perfect-control
description: 启用 CARLA perfect movement backend 及其 substep，执行定制状态/轨迹控制并检查默认后端恢复边界；不宣称该模型具有真实动力学。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# Perfect movement backend

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

独立原生任务创建可重建自有 vehicle，先记录默认后端和控制源，`vehicle.enable_perfect_control(max_substeps=n,max_substep_delta_time=dt)`。此 API 切 movement component，不自动生成路线；输入来自 trajectory-control 的 DriverControl/Trajectory 契约，禁止把 TM route 字符串直接送入。

正 substep 参数与 world 时钟协调，保留输入时序和后续 frame/位姿。组件中状态写入/控制消费可能绕过常规物理响应，只有轨迹执行证据时，不报告为车辆物理准确度或闭环性能。

无响应先查 user/local trajectory 模式、ValidFlag、控制输入是否真正送到该组件，再查 tick；不同时开恒速、TM 或外部后端。内部包含恢复默认组件路径，但 Python 无公开 `disable_perfect_control`；退出通过清理本任务车辆/重建默认车辆，或报告恢复缺口。不调用名称相近的内部 DisableCarsimUdpPhysics 作为 Python 方法。

## 交接与证据

[carla-trajectory-control](../carla-trajectory-control/SKILL.md)；[carla-vehicle-physics](../carla-vehicle-physics/SKILL.md)；[carla-clock](../carla-clock/SKILL.md)；[carla-actors](../carla-actors/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`、`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Vehicle/MovementComponents/PerfectControlMovementComponent.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
