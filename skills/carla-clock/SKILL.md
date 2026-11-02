---
name: carla-clock
description: 管理 CARLA 同步/异步、固定步长、物理 substep、有界 tick 和回调，以及定制 pause/free tick；用于帧不推进、步长不一致或双 tick owner 问题。
metadata:
  category: runtime
  execution: cli
  operations: 'world.tick'
---

# 时钟与推进

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

CLI 手工推进先读 `carla-agent schema world.tick`；参数 `session_id`、有界 `frames`，返回以实际 schema/result 为准：

```bash
carla-agent world tick --profile profile.json --params '{"session_id":"实际ID","frames":1}'
```

CLI session 内不旁路改 settings 或发送第二路 tick。原生独立任务保存 `world.get_settings()`，修改副本的 `synchronous_mode`、`fixed_delta_seconds`、`substepping`、`max_substep_delta_time`、`max_substeps`，`world.apply_settings(settings)` 后读回；固定步长不能超过 substep 容量。异步观测用 `wait_for_tick(seconds)`；同步唯一 owner 用 `tick(seconds)` 返回 frame。有界 `on_tick(callback)` 返回 callback ID，退出 `remove_on_tick(id)`。

定制绑定大小写必须保留：`PauseWorld()`、`ResumeWorld()`、`debug_step(seconds)`、`SendTickMsg(seconds)`、`WaitServerTick(seconds)`；客户端 `set_free_tick_count(count)`、`set_secondary_free_tick_count(secondary_id,count)` 会影响主/次服推进，不与普通 tick 混用。此处无通用 CLI 封装。

同步等待超时先查是否没有 tick owner、TM 同步不匹配或回调队列堵塞，不提高无限等待。帧跳变不能直接当丢 sensor 帧；先排除另一个推进者。退出恢复 settings 仅限同一 episode；与 TM owner 协调恢复同步状态。

## 交接与证据

[carla-session](../carla-session/SKILL.md)；[carla-traffic-manager](../carla-traffic-manager/SKILL.md)；[carla-capture](../carla-capture/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/World.cpp`、`PythonAPI/carla/src/Client.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
