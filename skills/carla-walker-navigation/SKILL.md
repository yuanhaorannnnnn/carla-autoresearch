---
name: carla-walker-navigation
description: 使用 CARLA WalkerControl 或 WalkerAIController 的目标/速度、随机导航点、过街比例与 seed；用于行人移动，骨骼姿态交 walker-pose。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 行人导航

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

直接控制与 AI 控制选择一个。独立原生任务用真实 walker blueprint 创建自有 walker；AI 需 `controller.ai.walker` blueprint，`world.spawn_actor(controller_bp,carla.Transform(),attach_to=walker)`，登记子 controller。

AI 操作 `controller.start()`→`go_to_location(destination)`→`set_max_speed(speed_mps)`；目标采用 `world.get_random_location_from_navigation()` 或已确认 navmesh 点，None 是无有效导航点，不是 Location(0,0,0)。直接控制 `walker.apply_control(carla.WalkerControl(direction=vector,speed=speed_mps,jump=False))`，direction 方向向量与速度分开。

`world.set_pedestrians_cross_factor(percentage)` 为 [0,1] 比例，`set_pedestrians_seed(seed)` 改全局行人导航随机源；不是 TM seed，须授权全局变化且保存实验输入。不存在对应 getter 时不承诺恢复原随机序列。

有界观察位置/速度、控制状态；站立不动先检查 navmesh、目标点、controller 绑定、start/tick，不自动重建道路或调高速度。退出先 controller.stop()，再 destroy controller，最后 walker；不能把其他客户端行人纳入清理。

## 交接与证据

[carla-actors](../carla-actors/SKILL.md)；[carla-walker-pose](../carla-walker-pose/SKILL.md)；[carla-navmesh](../carla-navmesh/SKILL.md)；[carla-clock](../carla-clock/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`、`PythonAPI/carla/src/Control.cpp`、`PythonAPI/carla/src/World.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
