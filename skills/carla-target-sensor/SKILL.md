---
name: carla-target-sensor
description: 配置 CARLA target 局部目标传感器；用于视域/遮挡、目标运动学、车道多项式、交通灯及端口输出，区别于全局真值、Oasis 雷达和 OSI。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.other.target
---

# Target sensor

精确 blueprint：`sensor.other.target`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.other.target"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

horizontal_fov/vertical_fov为Float degrees，range/min_detect_distance为Float m，points_per_second/noise_seed/max_object_num/send_port为Int，occlusion_thresh为Float，sensor_tick为Float seconds。send_port只在用户要求外部输出时设置，接收证据单列；可见范围/遮挡过滤使它不是全世界truth。

Python TargetMeasurement可迭代。对象字段object_id/object_type/sub_type/sim_id为uint32；x/y/z、pitch/yaw/roll、velocity_*、angular_velocity_*、length/width/height、min_distance/relative_velocity/rcs、acceleration_*为float32。位置/姿态实际转sensor局部（m/degrees），不是成员名world_X暗示的world坐标；运动学各字段的赋值/坐标不能全部类推。

另有5组lane（主组无m_前缀，l_/r_/ll_/rr_），validity/ID/type/color为int，width/c0..c3为double；车道多项式系数按阶数有不同量纲，先查LaneInfoFit约定及有效区间。traffic_light_num/traffic_light_validty/t_id/state/junction_id/type/cycle为int，distance/forward_angle/countdown为float，elapsed_time为double。不同object_type只有对应字段有效，不能把无效零值当观测。保留traffic_light_validty的真实拼写。

## 最短采集与恢复

describe → 明确需要对象/车道/灯哪一类及过滤条件 → 原生脚本自有挂载 → 有界监听迭代Python字段，按record类型和validity导出 → 保留frame/time、地图、坐标约定和未知字段。结构含int/double和对齐，raw_data不当同质float数组；详见 [target契约](../../references/sensors-object-contracts.md)。

缺目标查FOV/遮挡/最大数与sim_id有效性；车道异常查地图与拟合，不把局部目标输出等同完整ground-truth。当前capture.run不支持target，端口协议未核验时不承诺通用OSI兼容。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-ground-truth](../carla-ground-truth/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/TargetSensor.cpp:77、172、684–801、LaneInfoFit、1987、2122；A:1444；D/TargetData.h；Z/TargetSerializer.h；P:918–1027。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
