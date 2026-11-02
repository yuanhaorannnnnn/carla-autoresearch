---
name: carla-lidar-raycast
description: 配置和采集 CARLA 标准 RayCast LiDAR；用于通道、扫描频率/FOV、dropoff、BRDF、距离噪声和 XYZI 点云解码。semantic、MEMS、AT128、GPU 路径另走专项。
metadata:
  category: sensors
  execution: cli
  operations: 'sensors.describe,sensors.attach,capture.run'
  blueprint: sensor.lidar.ray_cast
---

# RayCast LiDAR

精确 blueprint：`sensor.lidar.ray_cast`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.lidar.ray_cast"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

channels/points_per_second/noise_seed为Int；range（Float m）、rotation_frequency（Float Hz）、upper_fov/lower_fov/horizontal_fov（Float degrees）；atmosphere_attenuation_rate、dropoff_general_rate/intensity_limit/zero_intensity、noise_stddev为Float，simu_brdf/simu_motion_distortion为Bool。完整差异见 [LiDAR契约](../../references/sensors-lidar-contracts.md)，只提交本blueprint实际暴露字段。

回调LidarMeasurement：horizontal_angle（float radians）、channels（整数）、get_point_count(channel)、raw_data；每个点point.xyz float32 meters、intensity float32，16 bytes/point。`np.frombuffer(data.raw_data,np.float32).reshape(-1,4)`只用于该布局。坐标是sensor局部，转世界需该measurement.transform；强度不能直接当真实反射率或dB。

## 最短采集与恢复

describe → 按点预算/频率设置扫描 → `capture.run` recipe用精确blueprint、已有map和有界frames，capture自行管理session → 保留原始XYZI、各frame/timestamp、点数与配置。每tick扫描角与rotation_frequency*fixed_delta相关，不默认一帧完整360°。

无点先检查range/FOV、扫描可见目标、dropoff和时钟；标准raycast直接序列化，不使用camera的send_data_stream修复。点少与物理不正确分开诊断；噪声/BRDF效果需要针对指标的证据。多sensor挂载交rig，采集缺帧/队列交capture。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-lidar-semantic](../carla-lidar-semantic/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/RayCastLidar.cpp:68；A:1739 MakeLidarDefinition/SetLidar；D/LidarData.h；Z/LidarSerializer.h；P:811；插件worker.capture。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
