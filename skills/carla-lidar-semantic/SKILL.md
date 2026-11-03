---
name: carla-lidar-semantic
description: 配置 CARLA semantic LiDAR 并解码几何、入射角和对象标签；用于 point/cos_inc_angle/object_idx/object_tag，避免当作 XYZI 点云。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.lidar.ray_cast_semantic
---

# Semantic LiDAR

精确 blueprint：`sensor.lidar.ray_cast_semantic`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.lidar.ray_cast_semantic"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

先核对MakeLidarDefinition中ray_cast_semantic分支的实际属性：channels/points_per_second为Int，range为Float m，rotation_frequency为Float Hz，upper_fov/lower_fov/horizontal_fov为Float degrees，sensor_tick为Float seconds。标准raycast的dropoff/噪声/BRDF字段不能未经describe直接复制。

回调SemanticLidarMeasurement，horizontal_angle（radians）、channels、get_point_count；detection.point.xyz float32 m、cos_inc_angle float32无量纲、object_idx/object_tag uint32，每点24bytes。object_tag是语义类别，object_idx是命中对象索引，不能把cos_inc_angle称强度，也不能将uint32重新解释为float坐标。

## 最短采集与恢复

describe → 原生脚本自有挂载 → native listener保存raw_data与点数/头部 → 先用Python迭代对象核对字段，再使用 [LiDAR契约](../../references/sensors-lidar-contracts.md) 的structured dtype批量解码。标签表核对CityObjectLabel；需关联actor时保存相同时刻/episode真值，不仅凭index猜。

标签全0/对象缺失先检查语义tag与可见mesh；形状错误检查24byte stride与uint32列。空measurement可为无命中，但纯回调超时不是有效空帧。当前capture.run不支持semantic，不能以标准raycast替代。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-ground-truth](../carla-ground-truth/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/RayCastSemanticLidar.cpp:83；A:1739分支；D/SemanticLidarData.h；Z/SemanticLidarSerializer.h；P:828。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
