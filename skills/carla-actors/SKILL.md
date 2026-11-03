---
name: carla-actors
description: 查询 CARLA actor 身份与 alive/active/dormant，在自有 CLI session 中生成和销毁 actor；原生 parent/attachment 仅用于独立原生生命周期。控制与运动交专项。
metadata:
  category: runtime
  execution: cli
  operations: 'actors.list,actors.inspect,actors.spawn,actors.destroy'
---

# Actor 生命周期

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

指定对象详情先读 `carla-agent schema actors.inspect`，再 `carla-agent actors inspect --profile profile.json --params '{"actor_id":123}'`。123 为示例 ID，替换成真实整数；返回 type_id/transform/velocity/acceleration 与可选 bounding_box，不存在返回 actor_missing。查询外部 actor 不获得控制权。

每次调用前读目标 schema；先 `carla-agent actors list --profile profile.json --params '{"filter":"vehicle.*"}'`，只读列出真实 ID/type。

`actors.spawn` 参数 `session_id`、`blueprint`、`spawn_index`（默认 0）；从实际 blueprints 和 spawn points 选择，返回 ID 登记到原 session。`actors.destroy` 参数同一 `session_id`、自有 `actor_id`；失败不绕过 ownership。当前 CLI 不接受任意 transform、parent 或 attachment_type，不能将这些塞进 request。

需要原生父子安装时先按独立原生任务完整管理：`world.spawn_actor(bp,transform,attach_to=parent,attachment_type=carla.AttachmentType.Rigid)`；`try_spawn_actor` 碰撞失败可返回 None。附着 transform 是相对 parent 的安装位姿；SpringArm/SpringArmGhost 与刚性安装不同，不用于假装固定外参。读回 `id/type_id/parent/is_alive/is_active/is_dormant/actor_state`。

空查询不触发 spawn；dormant 不等于已销毁。生成结果不明先查状态，禁止循环刷位置。原生任务清理自有子 actor 后父 actor，CLI session 用其 close；换图 handle 失效不在新世界删同号对象。

## 交接与证据

[carla-session](../carla-session/SKILL.md)；[carla-blueprints](../carla-blueprints/SKILL.md)；[carla-actor-batch](../carla-actor-batch/SKILL.md)；[carla-actor-motion](../carla-actor-motion/SKILL.md)；[carla-sensor-rig](../carla-sensor-rig/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/World.cpp`、`PythonAPI/carla/src/Actor.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
