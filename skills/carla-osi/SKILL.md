---
name: carla-osi
description: 配置 CARLA OSI GroundTruth/TrafficUpdate 的对象、道路、逻辑车道与环境映射，核对 protobuf 版本和外部接收边界；不假定所有 OSI 字段完整或 ROS2 已连通。
metadata:
  category: runtime
  execution: conditional
  operations: ''
---

# OSI 真值发布

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先核对 server 的 OSI/OASIS 发布组件、protobuf 定义版本、receiver 解码器与实际 transport 配置；Python 绑定存在不证明外部发布可用。

`world.set_osi_output([carla.OsiOutput.GroundTruth_MovingObject,...])` 输入枚举列表，绑定将其转换为 vector；选项包括 StationaryObject/MovingObject/TrafficSign/TrafficLight/RoadMarking/LaneBoundary/Lane/EnvironmentalConditions/ReferenceLine/LogicalLaneBoundary/LogicalLane，以及 TrafficUpdate_HostVehicleData/OtherVehicleData 的完整枚举前缀。不要把列表误写 bitmask 或 GroundTruthOutput。

授权独占任务按需求只开必要项；WorldObserver 分别调用 `publish_osi_groundtruth` 与 `publish_osi_traffic_update`，不是 Python API 直接返回消息。保存输出选择、receiver 原始 protobuf、schema version、header 时间和对象 ID，并检查至少一个实际填充字段与 CARLA snapshot 的坐标/单位对应。

FOsiWrapper 中有字段映射不表示完整 OSI 合规；缺选项、未填字段、primary/secondary 条件、发布失败与 receiver 解码失败要区分。没有原输出配置 getter 时不保证原状态恢复，结束按已知受控初值处理并报告。缺 receiver 时可交付静态配置/缺口，不能宣称端到端验证。

## 交接与证据

[carla-ground-truth](../carla-ground-truth/SKILL.md)；[carla-capture](../carla-capture/SKILL.md)；[carla-ros2-native](../carla-ros2-native/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/World.cpp`、`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Sensor/WorldObserver.cpp`、`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Util/OsiWrapper.h`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
