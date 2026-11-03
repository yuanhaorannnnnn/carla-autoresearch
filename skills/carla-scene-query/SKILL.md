---
name: carla-scene-query
description: 使用 CARLA cast_ray、project_point、ground_projection 查询带标签几何命中；用于位置投影与可见几何检查，不替代真实 sensor 数据或道路 Waypoint 语义。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 场景射线与投影

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

几何查询只读无需 session，但要记录 episode/frame 与场景/碰撞条件：

```python
hits = world.cast_ray(initial_location, final_location)
hit = world.project_point(location, direction, search_distance=100.0)
ground = world.ground_projection(location, search_distance=100.0)
```

输入 CARLA Location/Vector3D，距离米；输出 cast_ray 为 LabelledPoint 列表，project/ground 为可选 LabelledPoint，字段 `location/label`。方向向量按目标 API 约定提供，距离有界；不要把无命中 None 解引用或当作 (0,0,0)。

逐项保留命中顺序和标签，确认是否包含目标碰撞层/几何；空列表可能是起终点、方向、距离、加载或无碰撞 mesh 的问题。地图世界加载变化后旧点坐标也需核对。射线命中不包含 LiDAR/radar 的噪声、强度、多径和 sensor 调度，不用于声称传感器精度；道路投影和可通行性交 map。

## 交接与证据

[carla-map](../carla-map/SKILL.md)；[carla-scene-objects](../carla-scene-objects/SKILL.md)；[carla-ground-truth](../carla-ground-truth/SKILL.md)；[carla-lidar-raycast](../carla-lidar-raycast/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/World.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
