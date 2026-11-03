---
name: carla-lane-invasion-sensor
description: 监听 CARLA vehicle 越线事件；用于车体边界穿过车道标线、crossed_lane_markings 与客户端计算排障，不按服务端连续传感器流诊断。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.other.lane_invasion
---

# Lane invasion sensor

精确 blueprint：`sensor.other.lane_invasion`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.other.lane_invasion"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

generic definition不自动提供sensor_tick/FOV/range。必须附着vehicle；LibCarla客户端Listen会dynamic cast parent为Vehicle，其他parent只记录错误而不会形成有效监听。地图标线与车辆bounding box决定几何判断，不是相机检测或服务器碰撞事件。

LaneInvasionEvent.actor为parent，crossed_lane_markings为LaneMarking列表，按实际绑定读取type/color/lane_change/width等；width的道路标线宽度为meters。frame/timestamp取world snapshot，transform来自parent；不擅自当作sensor局部外参。实现计算vehicle bbox四角的跨线并可能给出多条marking，不能只保留第一条。

## 最短采集与恢复

describe → 核对自有parent确为vehicle与地图有相应标线 → 独立原生脚本自有挂载并保留listener进程 → 有界监听snapshot回调 → 保存全部marking和观察窗证据。registry使用NoopSerializer，事件由client计算，等服务器TCP包会走错排障路径。

无事件先查parent/地图标线/实际越线/进程是否活着，再查snapshot推进。没有越线时不回调；不能按每tick数据齐备规则判失败。当前capture.run不支持lane，时间/多源对齐交capture。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-map](../carla-map/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/LaneInvasionSensor.cpp:10；LibCarla/source/carla/client/LaneInvasionSensor.cpp:108、Listen；D/LaneInvasionEvent.h；PythonAPI/carla/src/Map.cpp LaneMarking绑定；P:876；SensorRegistry.h NoopSerializer。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
