---
name: carla-map-landmarks
description: 按 CARLA OpenDRIVE 标志 ID、类型、方向、有效车道或 Waypoint 距离查询 landmark 并映射运行时标志；动态灯态与相位归 traffic-signals。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 道路标志语义

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

从当前 `world.get_map()` 调 `get_all_landmarks()`、`get_all_landmarks_from_id(opendrive_id)`、`get_all_landmarks_of_type(type)` 或 `get_landmark_group(landmark)`。沿道路用 `waypoint.get_landmarks(distance, stop_at_junction=True)`，按类型用 `get_landmarks_of_type(distance,type,stop_at_junction=True)`；距离米，类型采用真实地图记录而非猜国家标准编码。

逐项保存 landmark 的 `id/type/name/road_id/s/orientation/transform`，`get_lane_validities()` 给有效车道范围；方向结合道路和车道理解，不把 world yaw 当道路有效方向。ID 可以对应多个 landmark，不能静默去重丢车道。

`world.get_traffic_sign(landmark)` / `get_traffic_light(landmark)` 映射到运行时 actor；未加载或缺 actor 时允许 None，保留静态记录与缺口，不自行 spawn 标志。世界换图后重取 landmark。道路标志查询不授权控制现有 signal actor，也不证明标志视觉资产存在。

## 交接与证据

[carla-map](../carla-map/SKILL.md)；[carla-traffic-signals](../carla-traffic-signals/SKILL.md)；[carla-scene-objects](../carla-scene-objects/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Map.cpp`、`PythonAPI/carla/src/World.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
