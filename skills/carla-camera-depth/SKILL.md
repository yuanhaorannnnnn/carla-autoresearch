---
name: carla-camera-depth
description: 配置 CARLA 深度相机并解码 RGB24 深度；用于距离图、深度单位、原始图与灰度显示差异、Linux 深度材质排障。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.camera.depth
---

# Depth camera

精确 blueprint：`sensor.camera.depth`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.camera.depth"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

使用常规camera的image_size_x/y（Int pixels）、fov（Float degrees）、sensor_tick（Float seconds）及镜头参数；仅按本sensor describe设置，depth定义不启用RGB的完整可修改后处理组。回调为Image而不是浮点深度数组，原始颜色是距离编码。

按 [camera深度段](../../references/sensors-camera-contracts.md) 从BGRA取R/G/B，在float中计算 `(R+256*G+65536*B)/16777215*1000` 得meters，先转float防uint8溢出。Image.convert(Depth/LogarithmicDepth)是显示用途，不能从显示灰度还原完整测距精度；原始图先保存。不要把DepthFloat枚举存在当作当前blueprint自动输出FloatImage的证据。

## 最短采集与恢复

describe → 原生脚本自有挂载 → 匹配wheel的有界native listener，核对Image类型与4WH bytes → 解码并用已知平面/距离检查缩放与方向。当前capture.run不支持depth，不造命令或伪装RGB采集。Linux材质为DepthEffectMaterial_GLSL，其他平台为DepthEffectMaterial；读取到bytes还不足以证明材质输出正确。

全黑/饱和/距离不符时先检查raw bytes、材质资源、相机遮挡、图像尺寸、镜头与平台，保留原始失败。该派生相机直接SendDataToClient，不把RGB的send_data_stream修复当唯一诊断。结束按原生任务保存的设置恢复。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-camera-rgb](../carla-camera-rgb/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/DepthCamera.cpp:13；A:332；D/Image.h；LibCarla/source/carla/image/ColorConverter.h；S/PixelReader.cpp:731；P:728。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
