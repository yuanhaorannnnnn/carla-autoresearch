---
name: carla-traffic-manager
description: 配置 CARLA TM port/autopilot、sync/seed/hybrid/dormant respawn、速度距离换道碰撞规则及 path/route/action buffer；不做地图路线搜索或交通灯相位控制。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# Traffic Manager

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

使用独立原生任务自有 vehicle，先核对 TM 是否独占；`tm=client.get_trafficmanager(tm_port)`，以 `tm.get_port()` 绑定 `vehicle.set_autopilot(True,tm_port)`。端口相同会共享 TM，不能擅自 `shut_down()` 或改全局行为。

与唯一 tick owner 协调 `tm.set_synchronous_mode(True)`，记录 `set_random_device_seed(seed)`、`set_hybrid_physics_mode(enabled)`/radius、`set_respawn_dormant_vehicles(bool)` 与 `set_boundaries_respawn_dormant_vehicles(lower,upper)`。这些全局 setter 无完整 getter，不能承诺还原借用 TM，优先专用端口/受控任务。

单车 `vehicle_percentage_speed_difference(vehicle,percentage)` 相对限速，正值减速；`set_desired_speed(vehicle,speed)` 为绝对目标，二者覆盖彼此配置。距离/偏移为米：distance_to_leading_vehicle、vehicle_lane_offset。auto/force_lane_change、collision_detection(reference,other,bool)、ignore_*_percentage、随机换道概率、update_vehicle_lights 分别按实际签名与 [0,100] 概率解释，ignore 不是确定遵守。

`set_path(vehicle,list[Location],empty_buffer=True)` 是几何点；`set_route(vehicle,list[str],empty_buffer=True)` 是 Left/Right/Straight/LaneFollow/ChangeLaneLeft/ChangeLaneRight/RoadEnd 等选择，不接 Waypoint tuples。`get_next_action/get_all_actions` 返回动作与 waypoint；记录 buffer 是否替换。

不动先查 autopilot port、sync、路网和 active/dormant，禁止第二控制源同时写。退出只对自有车 set_autopilot(False,tm_port)，恢复本任务 TM 状态/关闭专用 TM；不停止共享服务。

## 交接与证据

[carla-clock](../carla-clock/SKILL.md)；[carla-route-planning](../carla-route-planning/SKILL.md)；[carla-vehicle-control](../carla-vehicle-control/SKILL.md)；[carla-traffic-signals](../carla-traffic-signals/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/TrafficManager.cpp`、`PythonAPI/carla/src/Actor.cpp`、`PythonAPI/carla/src/Client.cpp`、`LibCarla/source/carla/trafficmanager/Parameters.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
