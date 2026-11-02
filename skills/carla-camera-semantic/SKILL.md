---
name: carla-camera-semantic
description: 配置 CARLA 语义分割相机并导出类别标签；用于原始类别 ID、CityScapesPalette、标签颜色和自定义分类核对。实例身份另走 instance 相机。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.camera.semantic_segmentation
---

# Semantic segmentation camera

精确 blueprint：`sensor.camera.semantic_segmentation`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.camera.semantic_segmentation"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

image_size_x/y（Int pixels）、fov（Float degrees）、sensor_tick（Float seconds）和镜头参数以describe为准。回调Image/BGRA8；语义ID取红通道即raw数组byte2，不从显示颜色反查类别，也不把R/G/B当连续物理量。

类别名称/颜色核对 [camera标签段](../../references/sensors-camera-contracts.md) 的CityObjectLabel/CityScapesPalette源码。CityScapesPalette转换仅生成显示图，原始uint8标签单独保存；fork的扩展标签不能按上游编号猜名称。语义类不能区分同类别的两辆车。

## 最短采集与恢复

describe → rig设置与参考RGB相同外参/尺寸 → native listener保存原始Image、frame/timestamp与class table → 提取R平面 → 另存palette预览。跨sensor对齐交capture，不能按回调到达顺序配对。

标签全0/缺类别时核对tagging、语义材质、透明/特殊mesh和当前地图资产；spawn成功不证明语义标签完整。颜色对但训练标签不对时检查是否误用palette/JPEG、通道顺序或插值。当前capture.run不支持此blueprint。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-camera-instance](../carla-camera-instance/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/SemanticSegmentationCamera.cpp:11；A:332；P:728；D/Image.h；LibCarla/source/carla/rpc/CityObjectLabel.h；LibCarla/source/carla/image/CityScapesPalette.h。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
