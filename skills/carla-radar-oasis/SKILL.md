---
name: carla-radar-oasis
description: 配置 CARLA Oasis 目标级雷达；用于遮挡筛选、目标数量、坐标方向及目标位姿/速度/尺寸/RCS 输出，避免与普通射线雷达或 target 真值混用。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.other.radar_oasis
---

# Oasis target radar

精确 blueprint：`sensor.other.radar_oasis`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.other.radar_oasis"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

horizontal_fov/vertical_fov（Float degrees）、range/min_detect_distance（Float m）、points_per_second/noise_seed/max_object_num（Int）、occlusion_thresh（Float阈值）、right_hand（Bool）、sensor_tick（Float seconds）；exact属性按describe。遮挡阈值与目标上限改变输出集合，不等于检测模型准确率。

回调RadarOasisMeasurement；object_id/object_type为uint32，x/y/z、pitch/yaw/roll、velocity_*、angular_velocity_*、length/width/height、min_distance/relative_velocity/rcs为float32。位置实际sensor局部m（源成员名world_X容易误导），姿态degrees，线速度m/s，尺寸全长m，径向速度m/s；角速度来自actor接口degrees/s且未统一转局部。right_hand分支有额外轴向/安装变换，字段不能一概宣称同坐标空间。

rcs按tag查表/默认值给定，未校准；uint32+float struct不按普通radar四列读取。完整字段与差异见 [Oasis契约](../../references/sensors-object-contracts.md)。

## 最短采集与恢复

describe → 记录right_hand、遮挡与目标筛选条件 → 原生脚本自有挂载 → native listener先迭代绑定对象保存字段和measurement姿态 → 需要ABI级raw解码再读实际struct/serializer。当前capture.run不支持Oasis。

目标缺失先查min distance、遮挡、目标上限和registry目标类型；位置反向先查局部/world误读与right_hand，不直接翻所有Y值掩盖问题。全球真值交ground-truth，车道/灯混合输出交target。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-target-sensor](../carla-target-sensor/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/RadarOasis.cpp:45、91、350–470；A:1531；D/RadarOasisData.h；Z/RadarOasisSerializer.h；P:1029。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
