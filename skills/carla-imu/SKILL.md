---
name: carla-imu
description: 配置 CARLA IMU 并解释加速度、角速度与 compass；用于各轴噪声/偏置、单位、sensor 坐标、重力与初始差分瞬态，不负责融合定位。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.other.imu
---

# IMU

精确 blueprint：`sensor.other.imu`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.other.imu"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

noise_seed为Int；noise_accel_stddev_x/y/z为Float（m/s²）；noise_gyro_stddev_x/y/z和noise_gyro_bias_x/y/z为Float（rad/s）；sensor_tick为Float seconds。没有已暴露的accel_bias属性就不能照搬真实IMU参数。以实际describe为准。

回调IMUMeasurement：accelerometer/gyroscope为Vector3D（各轴float32），分别m/s²与rad/s，compass为float radians。accelerometer由位置二阶差分，加world Z方向+9.81再转sensor局部，静止无噪声不应默认全0；pitch/roll后重力会分到不同轴。gyro从物理角速度转局部；CARLA轴为x前/y右/z上，转换ROS坐标必须显式记录。

compass基准North=(0,-1,0)，radians，不能当degrees或磁场向量。输出经MsgPack serializer，优先读属性，不按连续7float buffer猜解。

## 最短采集与恢复

describe → 原生脚本自有挂载并保存外参与噪声seed → 有界监听记录原字段 → warmup避开初始差分历史未建立的瞬态，记录步长和vehicle physics。安装点位置差分也受转动影响，不能直接当车体质心加速度。

突刺先查初始化、teleport、fixed delta与父actor物理；不要删重力来“修成零”而不说明含义。当前capture.run不支持IMU；融合定位交用户选定流程，时钟交clock。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-gnss](../carla-gnss/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/InertialMeasurementUnit.cpp:39、ComputeAccelerometer/ComputeGyroscope/ComputeCompass；A:1288；Z/IMUSerializer.h；P:889。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
