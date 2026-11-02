---
name: carla-vehicle-accessories
description: 控制 CARLA 自有车辆灯光、车门、后视镜与方向盘视觉角，读取车辆灯态；道路交通灯和场景照明交各自专项。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 车辆灯门与镜面

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

读取 `vehicle.get_light_state()`、`get_mirror_state()`、`get_steering_wheel_angle()`，世界级 `get_vehicles_light_states()` 返回 actor ID→light state。变更只作用于独立原生任务自有车辆。

灯态用 `set_light_state(carla.VehicleLightState.LowBeam | carla.VehicleLightState.Position)`；是 bitmask，赋值会替换整组，保留需延续的位。门用 `open_door(carla.VehicleDoor.FL)` / `close_door(...)`，All 影响全门。镜面用 `set_mirror_state(carla.VehicleMirrorState.LeftMirror)` 等；视觉方向盘 `set_steering_wheel_angle(angle)`，不要把视觉角当轮胎 steer 或动力学输入。

先保存可读灯/镜/方向盘状态；门没有此处通用状态 getter，优先使用可重建自有 actor。车辆资产未实现车门/镜面时，绑定存在也可能无可见效果；实际显示验证与 API 回执分开。TM 的 `update_vehicle_lights` 可能覆盖手动灯态，先解决控制权。结束恢复本任务改变且可读的状态，不全世界统一关灯。

## 交接与证据

[carla-vehicle-control](../carla-vehicle-control/SKILL.md)；[carla-scene-lights](../carla-scene-lights/SKILL.md)；[carla-traffic-signals](../carla-traffic-signals/SKILL.md)；[carla-traffic-manager](../carla-traffic-manager/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`、`PythonAPI/carla/src/World.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
