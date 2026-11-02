---
name: carla-semi-truck
description: 识别 CARLA 半挂车辆、读取 trailer transform 与 articulation angle，绑定自有 sensor 到拖车；车辆行驶交通用控制，不承诺任意拖车创建/连接接口。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 半挂与拖车

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先只读 `vehicle.is_semi_truck()`，为真后读取 `get_trailer_transform()`、`get_articulation_angle()`；保存主车与拖车坐标关系和 frame。普通 vehicle 不能因方法存在就当作半挂资产，缺 trailer 不伪造 transform。

拖车 sensor 安装使用独立原生生命周期内自有 vehicle/sensor：`vehicle.bind_sensor_to_trailer(sensor)`；组件安装另有 `attach_sensor_to_component(sensor_id)`，类型/ID 参数不同，不互换。先检查资产的 trailer/component 与生成 sensor 的 ownership，再调用并观察后续 sensor pose，不能沿用绑定前父车外参。

行驶仍用 vehicle-control；拖车运动/铰接角的单位和有效轴按对应实现核对，未确认时只报告原值。基线未暴露通用“创建/挂接任意 trailer” Python API，不编造 attach_trailer。退出先 stop/destroy 自有 sensor 再主车；绑定失败不销毁外部车辆或扫描清理拖车。

## 交接与证据

[carla-vehicle-control](../carla-vehicle-control/SKILL.md)；[carla-sensor-rig](../carla-sensor-rig/SKILL.md)；[carla-actors](../carla-actors/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
