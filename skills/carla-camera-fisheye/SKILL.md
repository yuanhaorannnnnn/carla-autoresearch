---
name: carla-camera-fisheye
description: 配置 CARLA fisheye 相机；用于 Kannala_Brandt、Conti、Equidistant、Scaramuzza 投影、k1–k6、cube face、拼接和 ImageCube 输出解码。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.camera.fisheye
---

# Fisheye camera

精确 blueprint：`sensor.camera.fisheye`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.camera.fisheye"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

此专用definition的image_size_x/y和cube_face_res都是Float（表示pixel尺寸），并非普通camera的Int。fov为Float degrees；fx/fy/cx/cy、new_fx/new_fy/new_cx/new_cy为Float pixels；k1–k6及C/D/E为Float模型系数；auto_center、disable_face_merge、enable_semantic_segmentation、send_data_stream为Bool，sensor_tick为Float seconds。distortion_model为String，推荐Kannala_Brandt/Conti/Equidistant/Scaramuzza，按实际describe选用，不把它们建成不同sensor。

输出ImageCube（不是Image或六路sensor），绑定width/height/fov/raw_data/convert/save_to_disk；像素Color为BGRA8。cube采样和最终输出尺寸不同；disable_face_merge改变生产路径，先检查实际header/len，不假定总是6×face_res²或直接reshape成普通相机图。详见 [camera专用serializer段](../../references/sensors-camera-contracts.md)。

## 最短采集与恢复

describe → 选择模型及匹配标定系数，记录fov/cube_face_res/输出尺寸与merge模式 → 原生脚本自有挂载 → native listener保存ImageCube、bytes与标定 → 需要显示时才convert。语义模式按标签规则保留原始值，不能对标签使用颜色连续插值。

图像边界/缝隙/畸变不符先核对模型、auto_center/new_*、cube face可见范围和merge模式，不把普通pinhole的fov公式强用。无回调核对本sensor的发送开关与render readback。当前capture.run不支持fisheye。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-camera-rgb](../carla-camera-rgb/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/FisheyeSensor.cpp:145、MergeCubeTo2D、SendPixels_RenderThread；A:3149、SetFisheyeSensor；D/ImageCube.h、ImageTmplCube.h；Z/ImageSerializerCube.h；P:776。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
