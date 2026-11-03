---
name: carla-lidar-at128
description: 配置 CARLA CPU AT128 LiDAR；用于三组扫描资产、256 点分块、MemsLidarMeasurement、时间/CRC 与 UDP 包核对。GPU AT128 预设另走 sc_lidar。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.lidar.at128
---

# CPU AT128 LiDAR

精确 blueprint：`sensor.lidar.at128`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.lidar.at128"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

该blueprint使用MakeMemsLidarDefinition(at128)：channels/beams_num/noise_seed为Int，range为Float m，rotation_frequency为Float Hz，scanning_patterns为String；simu_brdf/simu_motion_distortion/sim_nearest_down_sample为Bool，dropoff/噪声/精度为Float；额外udp_ip为String、udp_port为Int。网络目的地址非空且端口非0才创建sender；不要因stream成功推断UDP已收到。

CreateLasers固定加载Carla/Config/AT128Field1PointOrderTable.csv到Field3；三组扫描和256点分块，ChannelCount按tick/扫描量计算，不把channels属性直接当实际包通道数。全部CSV及列顺序按LoadPointOrderFile核验。

Python仍是MemsLidarMeasurement（laser_beam_index、channels、各channel点数，XYZI float32×4），不是AT128Measurement。UDP的seq/field/time/CRC与点协议需按本fork封包代码解读，不能reshape成Python raw_data，也不能以外部标准手册取代静态实现。细节见 [LiDAR契约](../../references/sensors-lidar-contracts.md)。

## 最短采集与恢复

describe → 三份扫描资产检查 → 原生脚本自有挂载 → native listener收取有界MemsLidarMeasurement；只有用户要求网络输出才配置UDP并保存接收端原始包 → 分别报告stream和UDP证据。当前capture.run不支持AT128。

无点先查3组资产与tick计算出的分块数；UDP异常先查启用条件、目的端与序号/CRC，不重开重复sender。GPU实现选择sc_lidar，不更换后仍称CPU AT128验证。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-lidar-gpu](../carla-lidar-gpu/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/RayCastAT128.cpp:89、117、157、438；A:1863；D/MemsLidarData.h；Z/MemsLidarSerializer.h；SensorRegistry.h:103；P:845。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
