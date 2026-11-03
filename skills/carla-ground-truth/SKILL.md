---
name: carla-ground-truth
description: 读取 CARLA WorldSnapshot/ActorSnapshot/Timestamp，配置 listen_actors 与 GroundTruthOutput 的 OASIS 发布边界；不与 target sensor 或 OSI protobuf 混称。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 世界快照与 OASIS 真值

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

只读 `snapshot=world.get_snapshot()`；保存 snapshot.id/frame、timestamp.frame/elapsed_seconds/delta_seconds/platform_timestamp，用 `snapshot.find(actor_id)` 或迭代 ActorSnapshot 的 get_transform/velocity/angular_velocity/acceleration。find 可为 None；snapshot 是同一帧观测，不能把多次 actor.get_* 的缓存组合成另一帧真值。

定制 `world.listen_actors(names=[])` 按名字配置观测范围，不是 `sensor.listen(callback)`。`world.set_ground_truth_output(output)` 输入 GroundTruthOutput bitmask，如 Vehicle/Walker/TrafficLight/TrafficSign/Prop/All 的实际枚举全名。它改变 server 输出配置，不返回 protobuf 数据；无对应 getter 时记录初始受控条件，不能保证还原借用服务。

WorldObserver 组装 `oasis::GroundTruth` 后经 `publish_traffic` 发布；实际 topic/传输/receiver 需检查配置与接收原始消息，不虚构 Python world.get_ground_truth 或固定网络端口。接收帧、对象 ID、单位/坐标应与 snapshot 对齐；source 内有填字段不代表每资产字段有效。

只拿到 snapshot 就只报告 snapshot 层；发布调用与 receiver 成功分开。真值配置变化、输出空、名字过滤和 primary/secondary 条件分别定位，不将空输出写成场景没有目标。

## 交接与证据

[carla-osi](../carla-osi/SKILL.md)；[carla-capture](../carla-capture/SKILL.md)；[carla-dataset](../carla-dataset/SKILL.md)；[carla-actors](../carla-actors/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Snapshot.cpp`、`PythonAPI/carla/src/World.cpp`、`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Sensor/WorldObserver.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
