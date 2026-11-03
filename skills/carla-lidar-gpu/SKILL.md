---
name: carla-lidar-gpu
description: 配置 CARLA SceneCapture GPU LiDAR；用于 mechanical、AT128、M1、Pandar64 预设、扫描资产、CPU/GPU 噪声以及 stream/UDP 输出边界。
metadata:
  category: sensors
  execution: conditional
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.lidar.sc_lidar
---

# SceneCapture GPU LiDAR

精确 blueprint：`sensor.lidar.sc_lidar`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.lidar.sc_lidar"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

精确ID是sensor.lidar.sc_lidar，不能虚构sensor.lidar.gpu。image_size_x/y/channels/points_per_second/beams_num/udp_port为Int；range/min_range为Float m；fov/upper_fov/lower_fov/horizontal_fov/horizontal_fov_offset/horizontal_angular_resolution/vertical_fov_interval为Float degrees；rotation_frequency为Float Hz；sensor_tick为Float seconds。

data_source_type/data_source/scanning_patterns/noise_mode/udp_ip为String，wheel_mode/high_res_mode/udp_work_mode为Bool，dropoff_*、noise_stddev、distance_accuracy/precision和high_res_*_threshold为Float。data_source按实际Sensors loader/资产而定；mechanical/AT128/M1AT128/M1/Pandar64是同一blueprint的配置路径，不新建型号skill。

registry用LidarSerializer→LidarMeasurement：point.xyz m与intensity为float32，16bytes/point；channels/horizontal_angle与get_point_count照实际头部。GPU内部渲染buffer与UDP包不是此raw_data契约；见 [LiDAR契约](../../references/sensors-lidar-contracts.md)。

## 最短采集与恢复

describe → 检查匹配的Sensors插件、材质/shader及扫描数据源 → 原生脚本自有挂载 → native脚本接收有界Python帧或用户指定UDP输出。udp_work_mode改变发送分支，逐条保存接收证据；CLI capture.run不支持sc_lidar。

加载器失败先保留TryLoadLaserArray错误及source身份；帧有点不证明GPU角度/强度/扫描模型正确。噪声CPU/GPU模式和高精度开关属于需冻结的实验条件，不自动宣称更真实/更快。actor清理由创建它的独立原生任务完成，不独立杀GPU/UDP进程。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-lidar-at128](../carla-lidar-at128/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/SceneCapture_Lidar.cpp:183、730、796、907、BuildLidarDatas/BuildUdpLidarDatas；A:2460；D/LidarData.h；SensorRegistry.h:111；P:811。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
