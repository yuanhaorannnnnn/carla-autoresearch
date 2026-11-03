---
name: carla-camera-instance
description: 配置 CARLA 实例分割相机并核对语义与实例编码；用于同类目标分离、实例掩码和跨帧身份边界，避免将像素 ID 当作 Actor.id。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.camera.instance_segmentation
---

# Instance segmentation camera

精确 blueprint：`sensor.camera.instance_segmentation`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.camera.instance_segmentation"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

image_size_x/y（Int pixels）、fov（Float degrees）、sensor_tick（Float seconds）沿用本blueprint真实camera属性。回调是Image/BGRA8，保留每个uint8通道。标准实例编码把语义放R、实例身份放G/B，但本fork实际材质是`/Game/Carla/PostProcessMaterials/M_InstanceSegmentationSensorMaterial`；C++仅加载资产，不能凭上游公式确定该资产的高低字节方向或Actor ID映射。

最短可靠导出先用(G,B)原始二元组作为单帧实例key，另存R语义及材料版本；用户需要uint16实例ID时核验实际材质/已知对象对照后再选择合并顺序。不要自动把它关联为world actor ID或承诺跨reload/重生稳定。细节见 [camera标签段](../../references/sensors-camera-contracts.md)。

## 最短采集与恢复

describe → 原生脚本自有挂载 → native listener收集有界原始Image → 按未着色的字节拆R和G/B → 用已知的两个同类目标核对分离与时间一致性。原始和显示palette分开，不对标签做JPEG或双线性插值。

实例ID突变先核对episode、actor生命周期、材质和字节方向；不要重新编号掩盖变化。当前capture.run不支持instance，跨帧/多sensor对齐交capture，全局actor身份查询交ground-truth。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-ground-truth](../carla-ground-truth/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/InstanceSegmentationCamera.cpp:15、constructor材质路径；A:332；D/Image.h；P:728。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
