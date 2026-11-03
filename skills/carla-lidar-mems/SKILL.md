---
name: carla-lidar-mems
description: 配置 CARLA 定制 MEMS LiDAR；用于 CSV 扫描轨迹、运动畸变、beam index、距离噪声及 MemsLidarMeasurement 采集。要求 custom-mems 能力和真实扫描资产。
metadata:
  category: sensors
  execution: conditional
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.lidar.ray_cast_mems
---

# MEMS LiDAR

精确 blueprint：`sensor.lidar.ray_cast_mems`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.lidar.ray_cast_mems"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

先确认profile.capability_profile=custom-mems、blueprint及资产都存在。channels/beams_num/noise_seed为Int；range为Float m、rotation_frequency为Float Hz；scanning_patterns为String路径名；simu_brdf/simu_motion_distortion/sim_nearest_down_sample为Bool；dropoff_*、noise_stddev、distance_accuracy/distance_precision为Float。CPU MEMS未把udp_ip/udp_port加入definition，不沿用CPU AT128的网络字段。

CSV路径为`ProjectContentDir()/Carla/Config/<scanning_patterns>`，不会自动加.csv；跳过首行，0列vertical/1列horizontal角度degrees。先检查真实文件、数值列、非空与角范围；beams_num会被CSV实际长度覆盖，不能只改数字声称已换扫描模式。

回调MemsLidarMeasurement：laser_beam_index（uint32）、channels、get_point_count、raw_data；point.xyz/intensity均float32，每点16bytes，point单位m。D/MemsLidarData.h残留SurfaceType注释/PLY表头不代表第五列，精确布局见 [LiDAR契约](../../references/sensors-lidar-contracts.md)。

## 最短采集与恢复

describe/能力与CSV检查 → 原生脚本自有挂载 → native有界脚本保存beam index/点数/XYZI/frame/time与pattern身份 → 按扫描时序解释运动畸变，不套机械旋转LiDAR的一圈规则。当前capture.run不支持MEMS，custom-mems只允许检查/挂载；缺能力或资产时停止该路径，不改成raycast报告MEMS成功。

零点/异常先查CSV、实际beam数与扫描时序；pattern加载失败不通过增大timeout掩盖。结束只清理原生任务资源，保留失败与恢复记录。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-lidar-at128](../carla-lidar-at128/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/RayCastMemsLidar.cpp:90、135；A:1863/SetMemsLidar；D/MemsLidarData.h；Z/MemsLidarSerializer.h；P:845。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
