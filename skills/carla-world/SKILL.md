---
name: carla-world
description: 查询 CARLA 当前世界、可用地图，或按授权 load/reload/unload 地图、地图层并检查加载状态；OpenDRIVE 生成和时钟策略分别交对应专项。
metadata:
  category: runtime
  execution: native-api
  operations: 'world.inspect'
---

# 世界加载与地图层

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

只读概况先读 `carla-agent schema world.inspect`，执行 `carla-agent world inspect --profile profile.json --params '{}'`。地图列表原生 `client.get_available_maps()` 返回实际名称，不从文件夹猜可加载地图。

加载采用独立原生任务，先结束旧 actor/session：`client.load_world(map_name, reset_settings=True, map_layers=carla.MapLayer.All)`；重载 `client.reload_world(reset_settings=True)`；卸载 `client.unload_world()`。记录原 map/settings，但不能承诺重建旧动态世界。load/reload 返回新 World 后重新取 map、settings、snapshot，核对 `world.id`，用 `world.get_load_episode_status()` 的实际值判断状态，不猜完成枚举。

层操作 `world.load_map_layer(layer)` / `unload_map_layer(layer)` 输入 `carla.MapLayer`，改变场景资产。只对支持分层的地图使用；无视觉变化需检查地图能力、层名与加载状态。换图使旧 actor、sensor、回调和地图 handle 失效；timeout 后先重新查询世界，不盲目再次 load。`reset_settings=False` 也不保留 actor。

## 交接与证据

[carla-session](../carla-session/SKILL.md)；[carla-clock](../carla-clock/SKILL.md)；[carla-map](../carla-map/SKILL.md)；[carla-opendrive-world](../carla-opendrive-world/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Client.cpp`、`PythonAPI/carla/src/World.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
