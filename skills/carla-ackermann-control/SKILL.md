---
name: carla-ackermann-control
description: 对 CARLA 自有车辆应用 Ackermann 转角、速度、加速度、jerk 与横纵分控，配置速度/加速度 PID；不把归一化方向盘输入当 Ackermann 转角。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# Ackermann 控制

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

本任务先创建车辆并确认唯一控制源。`carla.VehicleAckermannControl(steer,steer_speed,speed,acceleration,jerk)` 表示车轮转角/转角速度及纵向请求；steer 单位 rad，speed m/s。不要复用 VehicleControl 的 [-1,1] steer 缩放。

```python
before = vehicle.get_ackermann_controller_settings()
vehicle.apply_ackermann_control(carla.VehicleAckermannControl(
    steer=steer_rad, speed=speed_mps, acceleration=accel_mps2))
```

横纵分控入口分别为 `apply_ackermann_lateral_control(control)`、`apply_ackermann_longitudinal_control(control)`，仍输入 VehicleAckermannControl；未使用字段需按具体实现解释。PID 设置先读 `get_ackermann_controller_settings()`，在副本上修改 `speed_kp/ki/kd`、`accel_kp/ki/kd` 后 `apply_ackermann_controller_settings(settings)`，读回值并保存。

稳定性结论需有界轨迹/速度观测；控制回读 `get_control()` 是最终踏板值，不是原 Ackermann 请求回显。速度抖动、转向饱和先查 step/PID dt、模型/轮角限制与其他源，不无限扩大增益。结束撤销本任务控制并恢复 PID 或销毁自有 actor；更换外部 physics 后不能假设同一 PID 仍有效。

## 交接与证据

[carla-vehicle-control](../carla-vehicle-control/SKILL.md)；[carla-vehicle-physics](../carla-vehicle-physics/SKILL.md)；[carla-clock](../carla-clock/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`、`PythonAPI/carla/src/Control.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
