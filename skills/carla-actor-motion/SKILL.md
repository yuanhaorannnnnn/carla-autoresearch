---
name: carla-actor-motion
description: 读取 CARLA actor transform、速度与加速度，设置目标运动、恒速/恒加速度、力冲量以及重力/碰撞/物理开关；车辆动力学参数交 vehicle-physics。
metadata:
  category: runtime
  execution: native-api
  operations: 'actors.inspect'
---

# Actor 运动与力

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

只读 pose/线速度/加速度优先读 `carla-agent schema actors.inspect`，再 `carla-agent actors inspect --profile profile.json --params '{"actor_id":123}'`，123 替换真实 ID。角速度或本领域变更未封装时按下列原生接口处理。

只读可观察指定 actor 的 `get_transform/get_velocity/get_angular_velocity/get_acceleration`，带 snapshot frame 解释缓存；所有 setter 限独立原生任务自有 actor。

| 操作 | 契约与副作用 |
|---|---|
| `set_transform(Transform)` / `set_location(Location)` | 直接移动/传送，不是避障路径 |
| `set_target_velocity(Vector3D)` / `set_target_angular_velocity(Vector3D)` | 目标线/角速度，不能等价力驱动 |
| `enable_constant_velocity(Vector3D)` / `disable_constant_velocity()` | 恒速向量按 actor local frame；会压过正常运动控制 |
| `enable_constant_acceleration(acceleration,reverse=False)` / disable | 定制标量恒加速度；acceleration 为 float，先核对源码约定，不与普通踏板并用 |
| `add_force/add_impulse/add_torque/add_angular_impulse(Vector3D)` | 一次性力/冲量/扭矩；分别记录单位和 tick |
| `set_simulate_physics/set_collisions/set_enable_gravity(enabled)` | 改物理/碰撞/重力，可能失去地面接触 |

CARLA Location/线速度采用米、米/秒；角速度 API 与 UE/车辆转角单位可能不同，查实际消费实现，不能一律乘弧度。力的单位与后端有关，未确认时不做定量动力学结论。保存可读初始状态；无开关 getter 不能承诺完整恢复，优先自有可重建 actor。无运动先检查物理开关、dormancy、tick 和其他控制源，不连续增大力。

## 交接与证据

[carla-actors](../carla-actors/SKILL.md)；[carla-vehicle-control](../carla-vehicle-control/SKILL.md)；[carla-vehicle-physics](../carla-vehicle-physics/SKILL.md)；[carla-clock](../carla-clock/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`、`LibCarla/source/carla/client/Actor.h`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
