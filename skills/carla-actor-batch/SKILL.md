---
name: carla-actor-batch
description: 使用 CARLA apply_batch/apply_batch_sync、SpawnActor.then 和 FutureActor，逐项处理 Response/error；用于独立原生任务批处理，不把批操作当原子事务。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 批量 Actor 命令

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先完成自有对象/蓝图、位置和预期副作用清单；CLI session actor 不转交原生 batch。`client.apply_batch(commands,do_tick=False)` 不提供逐项同步结果；需要证据时用 `apply_batch_sync(commands,do_tick=False)`。

```python
cmd = carla.command.SpawnActor(bp, transform).then(
    carla.command.SetAutopilot(carla.command.FutureActor, True, tm_port))
responses = client.apply_batch_sync([cmd], do_tick=False)
for response in responses:
    if response.has_error():
        errors.append(response.error)
    else:
        owned_ids.append(response.actor_id)
```

`FutureActor` 只在 then 链中指该新 actor，不是现有 ID 占位符。DestroyActor/ApplyVehicleControl 等命令仍需本任务 ownership。`do_tick=True` 只有确认唯一 tick owner 且与 clock 协调才使用，不能因方便偷偷推进世界。

按输入索引关联每个 response；部分成功只清理已确认自有资源，不重试整个 batch。网络异常导致结果不明应查询新增对象身份，不能重复创建。batch 成功不证明 then 后 TM 行为或下一帧运动结果；保留控制回读/帧证据。

## 交接与证据

[carla-actors](../carla-actors/SKILL.md)；[carla-clock](../carla-clock/SKILL.md)；[carla-traffic-manager](../carla-traffic-manager/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Commands.cpp`、`PythonAPI/carla/src/Client.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
