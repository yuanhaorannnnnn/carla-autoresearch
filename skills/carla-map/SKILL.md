---
name: carla-map
description: 查询 CARLA spawn points、Waypoint、道路车道拓扑、junction、crosswalk 和地理坐标，导出 OpenDRIVE 或地图缓存；不控制车辆或信号相位。
metadata:
  category: runtime
  execution: native-api
  operations: 'map.inspect'
---

# 地图与 Waypoint

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先读 `carla-agent schema map.inspect`，再 `carla-agent map inspect --profile profile.json --params '{"limit":20}'`。`limit` 范围 1..500、默认 20；输出 map 与 spawn_points.total/limit/points，每点含 index/transform。只读查询无需 session，截断列表不能当作完整 spawn points。进一步道路查询使用下列原生接口。

取得 `m=world.get_map()`，记录 `m.name` 和 episode。按意图读取：`get_spawn_points()`→Transform 列表；`get_waypoint(location, project_to_road=True, lane_type=carla.LaneType.Driving)`；精确道路定位 `get_waypoint_xodr(road_id,lane_id,s)`。投影后的点不等于原位置在可行驶面上；需要检查原地归属时设 `project_to_road=False` 并处理 None。

Waypoint 输出 `road_id/section_id/lane_id/s/lane_width/lane_type/transform`，用 `next(distance)`/`previous(distance)`、`get_left_lane()`/`get_right_lane()`、`get_junction()` 扩展。`get_topology()` 是段端点对，`generate_waypoints(distance)` 是采样；距离为米，正值，分叉保留多个候选，不强取第一个。

`m.get_crosswalks()` 返回顶点序列；`transform_to_geolocation(location)` 依赖地图地理参考。`to_opendrive()` 返回字符串；`save_to_disk(path)` 和 `cook_in_memory_map(path)` 写客户端路径，先限定目标且不覆盖未知文件。空拓扑、None、断路分别保留；几何/语义成功不证明 navmesh、车辆可通行或地理标定准确。

## 交接与证据

[carla-world](../carla-world/SKILL.md)；[carla-map-landmarks](../carla-map-landmarks/SKILL.md)；[carla-route-planning](../carla-route-planning/SKILL.md)；[carla-tm-map-cache](../carla-tm-map-cache/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Map.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
