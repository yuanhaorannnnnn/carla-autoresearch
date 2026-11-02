---
name: carla-trajectory-control
description: 使用 sprint42 DriverControl/ValidFlag、Trajectory 点列、plan points、user trajectory 与车辆 body parameter；不与导航 Waypoint 路径、TM route 或 perfect movement backend 混用。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 定制轨迹与 DriverControl

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先确认独立原生任务车辆、唯一控制源、轨迹坐标/时间基准与有界执行窗口。此基线有三种不同输入：

| API | 输入类型 |
|---|---|
| `vehicle.send_trajectory(points)` / `send_user_trajectory(points)` | `list[carla.Trajectory]`；字段 x/y/z/v/a/t/theta/kappa/s |
| `vehicle.update_plan_points(points)` | `list[carla.Location]` |
| `vehicle.apply_driver_control(control)` / `send_trajectory_control(control)` / `send_user_trajectory_control(control)` | `carla.DriverControl` |
| `world.send_trajectory_batch(controls)` | `dict[int,carla.DriverControl]`，key 为自有 actor ID |
| `vehicle.update_vehicle_parameter(body_parameters)` | `carla.VehicleBodyParameter` |

`DriverControl` 有踏板、steer_speed/speed/acceleration/jerk、`valid_flag` 及 x/y/yaw/current_speed/clear_flag/use_control/enable_const_speed；flag 用实际 `carla.ValidFlag` 语义，不能因默认 0 推断所有字段生效。`VehicleBodyParameter` Python 字段是 **`vehicle_witdh`**，另有 vehicle_length/wheel_base/steering_ratio/center_of_vehicle；不能擅自纠正拼写。

user 路径有 `enable_user_trajectory()` / `disable_user_trajectory()`，与 user control 分开。先用少量合法时序点检查返回、后续 frame/位姿；重复点、逆序 t、角度/坐标不符先定位数据，不换协议。绑定未解释全部时间/角度单位，执行前核对消费实现。退出关闭本任务模式；批量发送逐车记账，不触及外部 actor。

## 交接与证据

[carla-route-planning](../carla-route-planning/SKILL.md)；[carla-vehicle-control](../carla-vehicle-control/SKILL.md)；[carla-perfect-control](../carla-perfect-control/SKILL.md)；[carla-actor-batch](../carla-actor-batch/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`、`PythonAPI/carla/src/Control.cpp`、`PythonAPI/carla/src/World.cpp`、`LibCarla/source/carla/rpc/trajectory.h`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
