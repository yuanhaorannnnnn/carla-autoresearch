---
name: carla-camera-stereo
description: 配置 CARLA stereo 相机并处理成组左右图、左深度和视差；用于基线、enable_depth、uint16 单位、格式与组内帧一致性。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.camera.stereo
---

# Stereo camera

精确 blueprint：`sensor.camera.stereo`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.camera.stereo"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

基于camera属性，额外baseline为Float meters（定义推荐0.5），enable_depth为Bool（推荐false）。使用use_custom_projection_matrix/fx/fy/cx/cy时保存实际内参；baseline与right-camera变换由sensor一起管理，不用两个RGB替换后继续称原生stereo。

Python回调StereoImageData：left_image/right_image为Image，left_depth_image/left_disparity_image为ImageUint16；enable_depth=false后两项为None。每组共享frame/timestamp/transform；各子图读取width/height/fov/raw_data，只有左右Image读取pixel_format（ImageUint16未绑定该属性），不能按单一BGRA buffer解整个组。

深度数组uint16单位mm（meters=raw/1000），视差uint16单位0.01pixel（pixels=raw/100）；producer按disparity=FocalLength*Baseline/DepthMeters计算。直接uint16 cast没有饱和保护，超65.535m或655.35px无法可靠表示，不能称1000m可用量程。RGB/YUV依实际pixel_format解码，详见 [camera stereo段](../../references/sensors-camera-contracts.md)。

## 最短采集与恢复

describe → 原生脚本创建一颗自有stereo actor → native listener保存成组原始子图和标定 → 校验非None项、bytes长度与共同frame → 在uint16可表示范围核对深度/视差关系。当前capture.run不支持stereo。

左右尺寸/视差异常先核对enable_depth、image_type、baseline、FocalLength与producer缩放，不自行补None或用FloatImage猜解。先恢复原生任务，再单独报告图像采集与深度有效性。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-camera-depth](../carla-camera-depth/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/StereoCameraSensor.cpp:26、CalculateCameraTransforms、GetPixelFormat；S/PixelReader.cpp:715–807；D/StereoImageData.h；Z/StereoCameraSerializer.h；P:758–775。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
