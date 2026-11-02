---
name: carla-gnss
description: 配置 CARLA GNSS 并解释经纬高、噪声/偏置与地图地理参考；用于地理坐标观测，避免声称具备卫星遮挡、多径或完整 GNSS 传播模型。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.other.gnss
---

# GNSS

精确 blueprint：`sensor.other.gnss`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.other.gnss"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

noise_seed为Int；noise_lat_stddev/noise_lat_bias、noise_lon_stddev/noise_lon_bias为Float degrees；noise_alt_stddev/noise_alt_bias为Float meters；sensor_tick为Float seconds。经纬度噪声不是米误差，不能直接用同一个值代表各纬度的相同平面距离。

回调GnssMeasurement.latitude/longitude/altitude均double，依次degrees/degrees/meters；SensorData仍给frame/timestamp/transform。serializer为GeoLocation MsgPack，不存在应套XYZI的raw点布局。地图geoReference决定世界→地理坐标转换，不把actor.x/y直接当经纬度。

## 最短采集与恢复

describe → 先由map查询确认geoReference/已知位置 → 原生脚本自有挂载 → 有界监听保存经纬高与外参、seed和地图身份 → 与同帧world位置转换结果对照。只读询问坐标时不启动sensor。

明显偏移先查地图地理参考、actor高度和noise bias；没有传播/遮挡实现证据就不能把正常输出当定位精度或可见卫星数。初始噪声/seed一致不证明真实RTK/多路径模型。当前capture.run不支持GNSS。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-map](../carla-map/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/GnssSensor.cpp:26；A:2023；D/GnssMeasurement.h；LibCarla/source/carla/geom/GeoLocation.h；Z/GnssSerializer.h；P:882。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
