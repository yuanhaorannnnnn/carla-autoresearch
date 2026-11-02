---
name: carla-navigation-agent
description: 使用 BasicAgent、BehaviorAgent 或 ConstantVelocityAgent 的目的地、global plan、local planner/PID 进行有界客户端导航；不与 Traffic Manager 或手动控制同时接管车辆。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 客户端导航 Agent

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

在独立原生任务创建自有 vehicle，确认控制源唯一。先选择 agent：BasicAgent 的 target_speed 为 km/h；BehaviorAgent 的 behavior 取该版本支持的 cautious/normal/aggressive；ConstantVelocityAgent 有恒速与碰撞恢复逻辑，不能当动力学控制等价替代。

```python
from agents.navigation.basic_agent import BasicAgent
agent = BasicAgent(vehicle, target_speed=target_speed_kmh)
agent.set_destination(destination_location)
# 由唯一时钟 owner 的有界循环每步调用：
control = agent.run_step()
vehicle.apply_control(control)
finished = agent.done()
```

可用 `set_global_plan(plan,stop_waypoint_creation=True,clean_queue=True)` 输入 route-planning 返回的 `(Waypoint,RoadOption)`；LocalPlanner opt_dict 的 `dt`、PID/采样等按当前源核对。同步 tick 由 clock 统一协调，run_step 不等于 world 已推进。

保存每步 frame/control/位置、终止原因；达到 frame/wall 限额仍未 done 应报告未到达。初始化/地图规划失败不自动启用 TM。结束释放控制、停止本任务恒速/附属 sensor，再清理自有 vehicle；不宣称 done 证明所有导航场景安全。

## 交接与证据

[carla-route-planning](../carla-route-planning/SKILL.md)；[carla-vehicle-control](../carla-vehicle-control/SKILL.md)；[carla-clock](../carla-clock/SKILL.md)；[carla-traffic-manager](../carla-traffic-manager/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/agents/navigation/basic_agent.py`、`PythonAPI/carla/agents/navigation/behavior_agent.py`、`PythonAPI/carla/agents/navigation/constant_velocity_agent.py`、`PythonAPI/carla/agents/navigation/local_planner.py`、`PythonAPI/carla/agents/navigation/controller.py`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
