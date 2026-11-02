---
name: carla-vehicle-control
description: 提交与回读 CARLA VehicleControl 的油门、制动、转向、档位和 user/local control；用于自有车辆手动控制，Ackermann、轨迹、TM 与外部模型各有独立接管权。
metadata:
  category: runtime
  execution: cli
  operations: 'vehicle.control'
---

# 车辆踏板控制

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

已有普通踏板控制优先走 CLI，先读 `carla-agent schema vehicle.control`。参数 `session_id`、自有 `actor_id`、`control` 对象；例如 `control: {"throttle":0.2,"steer":0,"brake":0}`，用 `carla-agent vehicle control --profile profile.json --request control.json` 发送完整参数对象。缺省字段归中性值，gear 最低 -1；未知字段拒绝。返回 submitted:true 表示提交成功，**不 tick**，不证明已移动。只对同一 session 拥有的 vehicle 生效；ownership/类型拒绝不能改用原生 API 绕过。进一步用 actors.inspect/显式 world.tick 观察，tick 仍受授权与唯一推进者约束。user/local control 目前无 CLI 封装，必须另起完整独立原生生命周期。

控制前记录自有 vehicle 与控制源，关闭本任务已启用的 autopilot/其他控制，不能接管 CLI lease actor。原生 `vehicle.apply_control(carla.VehicleControl(throttle=...,steer=...,brake=...))`；throttle/brake 为 [0,1]、steer 为 [-1,1]，hand_brake/reverse/manual_gear_shift 为 bool，gear 为 int。完整 VehicleControl 默认未提供字段为中性值，单独 `apply_throttle_control/apply_brake_control/apply_steer_control` 是不同部分控制入口。

`get_control()` 回读控制值；无异常不证明车辆已运动，结合后续 frame、velocity、位置和 failure state。设置 reverse 与手动 gear 时核对模型实际档位，不能仅凭 speed 正负判断。

定制 user control 采用 `enable_user_control()`、`apply_user_control(control)`、`disable_user_control()`；`start_local_control(enabled=True)` 是另一接管模式。其优先级需按 server 消费实现确认，不默认与 apply_control 可叠加。结束显式撤销本任务模式、提交合适中性/制动状态后清理自有车辆；episode 变化不复用旧对象。无响应先查 tick、hand brake、物理后端和控制竞争，不提高油门掩盖问题。

## 交接与证据

[carla-actors](../carla-actors/SKILL.md)；[carla-ackermann-control](../carla-ackermann-control/SKILL.md)；[carla-trajectory-control](../carla-trajectory-control/SKILL.md)；[carla-traffic-manager](../carla-traffic-manager/SKILL.md)；[carla-clock](../carla-clock/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`、`PythonAPI/carla/src/Control.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
