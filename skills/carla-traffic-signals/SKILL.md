---
name: carla-traffic-signals
description: 查询 CARLA 交通灯的路口/ODR ID、灯态、倒计时、cycle、影响车道和 stop waypoints，管理定制相位组、冻结与 reset；单灯 freeze 在此基线影响全世界。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 交通信号与相位

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先只读定位：`world.get_traffic_light_from_opendrive_id(id)`、`get_traffic_lights_in_junction(junction_id)`、`get_traffic_lights_from_waypoint(waypoint,distance)`。每灯 `get_state/get_type/get_junction_id/get_countdown/get_cycle/get_elapsed_time/get_opendrive_id/get_affected_lane_waypoints/get_stop_waypoints/get_light_boxes`；None/空列表不证明地图无信号。

此基线没有 Python `set_state/set_red_time/set_green_time` 绑定，不套用上游教程。全局信号变更需明确授权与独占，不能以 actor 可见当自有资源。`light.freeze(True)` 实际调用 **FreezeAllTrafficLights**；优先显式 `world.freeze_all_traffic_lights(frozen)` 表示范围；`reset_all_traffic_lights()` 同样全局。

相位采用 `world.get_traffic_light_group(junction_id)` 读 `TrafficLightGroupPhase` 的 enabled/junction_id/cycle/time/lights；每个 TrafficLightPhaseTable 是 light_id+phases，每个 Phase 是 state+duration。改完整副本后 `world.set_traffic_light_group(group)`，核对灯 ID 属该路口、周期/各阶段时长一致；不要把 runtime actor ID 当 ODR light_id。

记录原组表/冻结状态与 frame，变更后观察整个受影响组；无法完整读取原始全局状态时不能保证恢复。reset 不等于恢复历史相位，单灯读回不证明全局冻结恢复。

## 交接与证据

[carla-map-landmarks](../carla-map-landmarks/SKILL.md)；[carla-traffic-manager](../carla-traffic-manager/SKILL.md)；[carla-clock](../carla-clock/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`、`PythonAPI/carla/src/Client.cpp`、`PythonAPI/carla/src/World.cpp`、`LibCarla/source/carla/client/TrafficLight.cpp`、`LibCarla/source/carla/rpc/TrafficLightGroupPhase.h`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
