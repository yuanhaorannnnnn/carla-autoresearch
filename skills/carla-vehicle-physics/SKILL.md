---
name: carla-vehicle-physics
description: 读取和应用 CARLA Chaos 车辆 PhysicsControl、轮胎悬架传动与质心，查询轮角/RPM/failure/telemetry；不把默认模型参数强套 CarSim、Chrono 或 UDP 后端。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 车辆物理参数

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先确认车辆类型与默认 movement backend，读取 `before=vehicle.get_physics_control()`，复制需要改变的字段并记录原值。`VehiclePhysicsControl` 的 mass、center_of_mass、drag_coefficient、torque_curve、max_torque/max_rpm、gear ratios、steering_curve 与 wheels 是一套模型契约；质量 kg，质心/轮参数单位逐项核对，不把 UE cm 与 CARLA m 混写。

车轮是 `WheelPhysicsControl`，此基线为 Chaos 字段：wheel_radius/wheel_width/wheel_mass、cornering_stiffness/friction_force_multiplier、max_steer_angle、suspension_*、spring_rate、affected_by_*、max_brake_torque 等。取 `wheels=control.wheels` 改后必须赋回 `control.wheels=wheels` 再 `apply_physics_control(control)`；不要照旧版 tire_friction/damping_rate 字段。

读回 PhysicsControl；查询 `get_wheel_steer_angle(carla.VehicleWheelLocation.FL_Wheel)`、`get_engine_rotation_speed()`、`get_wheel_rotation_speed(index)`、`get_failure_state()`。`set_wheel_steer_direction(wheel_location,angle_in_deg)` 改轮视觉/转向状态，不等于整套控制。`show_debug_telemetry(True)` 是显示副作用，结束关闭。

非法轮索引、空 wheels、模型忽略参数、重心不稳分别报告；有界运行才评价效果。退出恢复 before 仅同模型/episode有效；外部后端恢复另走各专项，不以 apply_physics_control 充当后端切换。

## 交接与证据

[carla-vehicle-control](../carla-vehicle-control/SKILL.md)；[carla-carsim](../carla-carsim/SKILL.md)；[carla-chrono](../carla-chrono/SKILL.md)；[carla-perfect-control](../carla-perfect-control/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`、`PythonAPI/carla/src/Control.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
