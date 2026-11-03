---
name: carla-camera-dvs
description: 配置 CARLA DVS 事件相机并解码时间、像素和极性；用于正负阈值、噪声、不应期、稀疏事件及无事件窗口诊断。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.camera.dvs
---

# DVS event camera

精确 blueprint：`sensor.camera.dvs`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.camera.dvs"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

除describe中的camera属性，还包括positive_threshold/negative_threshold、sigma_positive_threshold/sigma_negative_threshold（Float；亮度变化阈值及其标准差）、refractory_period_ns（Int ns）、use_log（Bool）、log_eps（Float）。阈值含义随use_log变化；记录曝光/照明/运动，不能仅靠阈值推断真实事件相机物理响应。

回调DVSEventArray，width/height/fov与raw_data；每个DVSEvent为packed x/y uint16 pixels、t int64 ns、pol bool，13 bytes。NumPy可用`[('x','<u2'),('y','<u2'),('t','<i8'),('pol','?')]`（确认平台小端且不align）；SensorData.timestamp是double秒，不能混用纳秒事件时间。优先to_array_x/y/t/pol或迭代对象，to_image只用于累积显示。

## 最短采集与恢复

describe → 原生脚本自有挂载 → native listener按有界观察时间窗收集events → 保存每个事件及窗的frame/time边界，不补造每tick一帧RGB。S/DVSCamera.cpp仅events.size()>0才send；静止无事件与连续图像丢帧不同，但纯超时不能证明“正确空集合”。详见 [camera事件段](../../references/sensors-camera-contracts.md)。

无回调先检查运动/阈值、listener、tick与source guard：本静态基线PostPhysTick含`if (!HasActorBegunPlay() || IsValid(this)) return;`，活跃有效actor可能提前退出。只报告源码风险与实际观测，不能声称此版DVS已运行成功，也不擅自改产品代码。当前capture.run不支持DVS。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-capture](../carla-capture/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/DVSCamera.cpp:40、PostPhysTick、SimulateEvents；D/DVSEvent.h；P:1114；Z/DVSEventArraySerializer.h。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
