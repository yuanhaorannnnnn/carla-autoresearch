---
name: carla-spectator
description: 读取或移动 CARLA spectator、配置 ego follow/role/reclaim 观察视角；不创建训练 camera sensor，显示器和 secondary viewport 配置交 display。
metadata:
  category: runtime
  execution: native-api
  operations: 'spectator.inspect'
---

# 观察视角与 ego follow

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

只查视角先读 `carla-agent schema spectator.inspect`，再 `carla-agent spectator inspect --profile profile.json --params '{}'`，返回 transform，不开启 session 或移动视角。变更使用下列独立原生流程。

只读 `spectator=world.get_spectator()`、`spectator.get_transform()`，记录 episode/frame。授权改变观察视角时在独立原生任务保存位姿后 `spectator.set_transform(carla.Transform(location,rotation))`；它是全局观察者，不因取到对象就有权移动他人的视角。

定制入口 `world.set_ego_role_name(new_ego_role_name)`、`follow_ego(view_mode_name)`、`force_reclaim_all_egos()` 会影响 ego 选择/回收；view_mode 的有效字符串按实际 server 实现/配置核对，不猜第三人称名称。reclaim 明确是全局副作用，不用来“找车”或无授权准备环境。

目标 role 不存在、多 ego 冲突、视角被 follow 覆盖分别诊断；移动 spectator 不等于 sensor 外参改变。结束在同一 episode 恢复保存的观察位姿；follow/role 缺完整 getter 或退出协议时不能承诺所有模式已恢复，应使用受控场景并说明限制。需要可保存的图像改用 camera/rig/capture。

## 交接与证据

[carla-display](../carla-display/SKILL.md)；[carla-camera-rgb](../carla-camera-rgb/SKILL.md)；[carla-sensor-rig](../carla-sensor-rig/SKILL.md)；[carla-actors](../carla-actors/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/World.cpp`、`PythonAPI/carla/src/Actor.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
