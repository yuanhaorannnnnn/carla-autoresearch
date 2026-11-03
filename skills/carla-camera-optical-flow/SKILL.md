---
name: carla-camera-optical-flow
description: 配置 CARLA 光流相机并读取二维 float32 流；用于帧间运动、光流数值与彩色显示差异，避免按 BGRA 或物理速度解码。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.camera.optical_flow
---

# Optical flow camera

精确 blueprint：`sensor.camera.optical_flow`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.camera.optical_flow"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

image_size_x/y（Int pixels）、fov（Float degrees）、sensor_tick（Float seconds）和镜头参数按describe；此definition不开放RGB完整后处理组。OpticalFlowImage每像素是两个float32 x/y，raw_data为8WH bytes；`np.frombuffer(data.raw_data,np.float32).reshape(H,W,2)`，不能按四通道颜色读取。

源渲染读回后对RG减0.5再乘4，得到normalized screen displacement；像素位移转换需结合宽高及材质约定。单位不能写m/s，不凭flow直接报告三维真值速度。get_color_coded_flow()给显示FakeImage，原始float32先保存。详见 [camera flow段](../../references/sensors-camera-contracts.md)。

## 最短采集与恢复

describe → 原生脚本自有挂载 → native listener → 核对类型/shape/finite → 保存raw flow和颜色预览；丢弃初始化warmup，记录当前/前帧与模拟时间。固定相机/物体运动的参照用于分辨方向和尺度，非本轮授权时只准备步骤不自行启动实验。

全0先检查画面是否静止与历史帧有效，彩色显示异常先检查8WH长度和dtype。frame间隔变化时不能直接比较同等流量或当成速度；跨sensor对齐/时钟交capture/clock。当前capture.run不支持此blueprint。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-ground-truth](../carla-ground-truth/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/OpticalFlowCamera.cpp:17、PostPhysTick；D/Color.h OpticalFlowPixel；D/Image.h；Z/OpticalFlowImageSerializer.cpp；P:794、ColorCodedFlow。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
