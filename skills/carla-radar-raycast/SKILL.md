---
name: carla-radar-raycast
description: 配置 CARLA 射线雷达并解码径向速度、方位、仰角和距离；用于 FOV/range/points_per_second 与 RadarMeasurement 点检测，不处理 Oasis 目标级结构。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.other.radar
---

# RayCast radar

精确 blueprint：`sensor.other.radar`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.other.radar"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

horizontal_fov/vertical_fov为Float degrees，range为Float m，points_per_second/noise_seed为Int，sensor_tick为Float seconds。FOV描述采样角域，PPS决定射线预算，不能把raycast命中点数量当稳定目标数量。

RadarMeasurement可迭代、get_detection_count/raw_data；每条RadarDetection按velocity/azimuth/altitude/depth顺序float32×4，分别m/s、radians、radians、m。可`np.frombuffer(data.raw_data,np.float32).reshape(-1,4)`，不是XYZI。velocity是相对sensor的径向投影，不能当车辆world速度；符号按实现的(target-current)·ray约定，标明远离/接近方向。

## 最短采集与恢复

describe → 原生脚本自有挂载 → native listener保存每帧原始检测与安装姿态 → 用r/azimuth/altitude在sensor坐标绘点或直接迭代字段 → 保存frame/time与零检测帧。坐标变换不要漏sensor外参。

空检测先核对FOV/range与命中物，纯超时另查listener/tick；不同角单位是常见错位原因，Oasis和mmwave不可用本dtype解。当前capture.run不支持radar；相关布局对照见 [object contracts](../../references/sensors-object-contracts.md)。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-radar-oasis](../carla-radar-oasis/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/Radar.cpp:22、CalculateRelativeVelocity；A:1386；D/RadarData.h；Z/RadarSerializer.h；P:896。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
