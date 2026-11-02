---
name: carla-ultrasonic
description: 配置 CARLA ultrasonic 超声传感器；用于声频、换能器、衰减、角采样、水泥附着与距离噪声，并按活跃 V2 单距离输出解码。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.other.ultrasonic
---

# Ultrasonic sensor

精确 blueprint：`sensor.other.ultrasonic`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.other.ultrasonic"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

horizontal_fov/vertical_fov/horizontal_fov_res/vertical_fov_res为Float degrees；range为Float m；points_per_second/noise_seed为Int；sonic_frequency为Float Hz，dB为Float衰减参数，sonic_radius为Float m；noise_std为Float，其值经噪声采样后乘1e-2加入m距离（cm尺度）；attachment_type为String，attachment_range为Float覆盖比例，sensor_tick为Float seconds。具体水/泥模式字符串只取实时推荐值或源码，不发明枚举。

活跃registry是UltraSonicSerializerV2→UltraSonicMeasurementV2，只有distance（float meters，经MsgPack），不是旧UltraSonicMeasurement检测数组。旧velocity/azimuth/altitude/depth绑定仍存在，不能据此说当前输出多点雷达。无命中返回post range，不把该数值当确有障碍。

## 最短采集与恢复

describe → 保存声学/附着配置 → 原生脚本自有挂载 → 有界监听V2并记录distance/frame/time；distance有限性/范围与模型post range分开核对。旧数组解析报错先核对Python类名和registry，不强行读raw_data。

noise_std路径每次新建random_device，noise_seed不保证该噪声完全复现。水/泥影响范围不证明真实传感器标定。当前capture.run不支持ultrasonic，细节见 [object距离段](../../references/sensors-object-contracts.md)。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-obstacle-sensor](../carla-obstacle-sensor/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/UltraSonicSensor.cpp:68、101–110、170–184、253；A:1622；SensorRegistry.h:99；Z/UltraSonicSerializer.h；P:1081–1099。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
