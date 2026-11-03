---
name: carla-session
description: 打开、关闭 CARLA Agent 独占 session，保存 settings、跟踪资源与 episode 并恢复；用于已授权多步操作的生命周期管理，不负责 server 进程或换图。
metadata:
  category: runtime
  execution: cli
  operations: 'session.open,session.close'
---

# 独占 Session

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

只读检查不必开 session。变更前核实用户授权、`exclusive` profile、预期 server version 与当前地图；逐个读 schema：

```bash
carla-agent schema session.open
carla-agent schema session.close
carla-agent session open --profile profile.json --params '{"fixed_delta_seconds":0.05,"expected_map":"实际地图名"}'
```

`fixed_delta_seconds` 是世界步长；`expected_map` 约束现图，不加载地图。保存真实返回 `session_id`；后续 mutation 传同一 ID。结束时 `carla-agent session close --profile profile.json --params '{"session_id":"实际ID"}'`。

open 会更改同步 settings 并记录原设置；close 只清理该 session actor，且 ownership/episode 匹配才恢复。超时或进程退出不能证明已释放 lease。重复 open 前查原记录并核对实际世界；close 拒绝或 episode 改变时保留错误，不修改所有权记录、不全量 destroy。原生脚本不能借用此 lease；独立原生任务另见原生约定。

## 交接与证据

[carla-connection](../carla-connection/SKILL.md)；[carla-clock](../carla-clock/SKILL.md)；[carla-actors](../carla-actors/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/World.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
