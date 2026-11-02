---
name: carla-route-planning
description: 用 CARLA GlobalRoutePlanner 的 topology、采样图和 A* 生成 Waypoint/RoadOption 路径；用于起终点路线、道路分叉与换道连接，不直接驱动车辆。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 全局道路路线

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

需要匹配基线的 `PythonAPI/carla` agents 模块及其 numpy/networkx 依赖；先检查模块来源，避免混入别版本 `GlobalRoutePlannerDAO` 示例。

```python
from agents.navigation.global_route_planner import GlobalRoutePlanner
planner = GlobalRoutePlanner(world.get_map(), sampling_resolution_m)
route = planner.trace_route(origin_location, destination_location)
```

构造器已 `_build_topology/_build_graph/_find_loose_ends/_lane_change_link`，此版本不额外调用旧 `setup()`。输入米制正采样间隔、CARLA Location；输出 `list[(Waypoint,RoadOption)]`。保存 map/episode、起终点投影和完整道路/车道序列，以便解释 Left/Right/LANEFOLLOW/换道选项。

无 waypoint、图无路径、路网断开、依赖缺失应分别给原始失败，不回退直线轨迹。缩小采样间隔会增大图与耗时，不靠无限加密掩盖断路。换图重建 planner；route 仅是地图路径，既不保证动态无碰撞，也不直接等价 trajectory-control 或 TM 字符串 route。

## 交接与证据

[carla-map](../carla-map/SKILL.md)；[carla-navigation-agent](../carla-navigation-agent/SKILL.md)；[carla-traffic-manager](../carla-traffic-manager/SKILL.md)；[carla-trajectory-control](../carla-trajectory-control/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/agents/navigation/global_route_planner.py`、`PythonAPI/carla/agents/navigation/local_planner.py`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
