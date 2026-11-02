---
name: carla-radar-mmwave
description: 配置 CARLA 毫米波雷达信号模型；用于载频、功率、天线增益、热噪声、SNR、角分辨率、延迟及目标检测字段，识别未实现的常量置信度/测高。
metadata:
  category: sensors
  execution: conditional
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.radar.millimeter_wave
---

# Millimeter-wave radar

精确 blueprint：`sensor.radar.millimeter_wave`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.radar.millimeter_wave"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

依赖匹配Sensors/RadarModel及FFTW链路，不从blueprint存在推断模型运行。全为Float attributes：F0_GHz（GHz）、Pt_dBm（dBm）、Gt_dBi/Gr_dBi（dBi）、Ts_K（K）、Fn_dB/L0_dB/SNR_min_dB（dB）、FovVertial/FovHorizional/ResVertial/ResHorizional（degrees）、Range（m）、Delay（单位及实际作用需核对setter/依赖模型）。保留Vertial/Horizional拼写，不能改成上游radar的horizontal_fov。

MillimeterWaveRadarMeasurement可迭代；objidx/objtype为uint32；distance/azimuth/elevation/radialvelocity/rcs/existenceprobability为double。distance=m、radialvelocity=m/s、azimuth=degrees，不是普通radar的radians；rcs单位依据RadarModel，不直接猜dBsm。

当前依赖实现固定ObjType=0、Elevation=0、ExistenceProbability=1，不能把它们当有效类别、高度或已校准置信度。不是4列float32原始点阵。细节见 [mmwave契约](../../references/sensors-object-contracts.md)。

## 最短采集与恢复

describe → 核对匹配wheel/server/插件依赖 → 原生脚本自有挂载 → native listener迭代并保存检测字段与RF配置 → 分别判断流是否收到、目标/数值是否符合用途。当前capture.run不支持mmwave。

全常量先区分实现占位和链路错误，不提高超时或改阈值声称修复占位字段。依赖缺失只报告缺口，不自动编译/安装/换普通radar。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-radar-raycast](../carla-radar-raycast/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：A:3800；S/MillimeterWaveRadarSensor.cpp:58；D/MillimeterWaveRadarData.h；P:1144；Unreal/CarlaUnreal/Plugins/Sensors/Source/Sensors/Radar/MillimeterWaveRadar.cpp:144–155、RadarModel/RadarInitEcho.h。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
