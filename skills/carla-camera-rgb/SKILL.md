---
name: carla-camera-rgb
description: 配置和采集 CARLA RGB 相机；用于内参、镜头畸变、曝光、后处理、BGRA/YUV 输出及 Python 图像回调诊断。深度、标签和事件相机走各专项。
metadata:
  category: sensors
  execution: cli
  operations: 'sensors.describe,sensors.attach,capture.run'
  blueprint: sensor.camera.rgb
---

# RGB camera

精确 blueprint：`sensor.camera.rgb`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.camera.rgb"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

先读 [camera 契约](../../references/sensors-camera-contracts.md) 的常规属性/像素格式段。关键属性 image_size_x/y 为Int pixels，fov为Float degrees，sensor_tick为Float seconds；use_custom_projection_matrix为Bool，fx/fy/cx/cy为Float pixels。开启自定义矩阵后不能只用fov计算内参；记录实际矩阵输入、镜头模型和分辨率。exposure_mode为String，shutter_speed/iso/fstop/gamma为Float，enable_postprocess_effects为Bool；摄影效果与数值图像一致性按用户用途选择。

该fork的send_data_stream（Bool）源码默认False；若实际describe有此属性，Python采集显式设true。仅UE窗口有画面不证明回调已收到。image_type定义推荐RGBA/YUV420；capture只按四字节路径解码，因此使用RGBA并核对回调Image.pixel_format和raw_data长度。标准Image每像素BGRA8，width/height为整数，fov为degrees；frame/timestamp见共享采集规则。

## 最短采集与判断

属性检查后，将精确blueprint、属性、已有map、frames/warmup_frames/fixed_delta_seconds放入`capture.run`的recipe；先查schema，不手工另开session。保留原始BGRA与capture.json。只要RGB显示则可调用Image.save_to_disk；数值比较保留原始bytes，预览才做BGR→RGB。

无回调先对照send_data_stream、实际image_type、唯一role_name、listener与tick，再区分渲染失败/发送失败/客户端超时。YUV要原生脚本并核对plane，不能用现capture的BGRA解释。成功帧只证明当前分辨率和配置；曝光或噪声模型真实性另需实验。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-camera-depth](../carla-camera-depth/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/SceneCaptureCamera.cpp:28、NeedSendDataToStream；A:332 MakeCameraDefinition/SetCamera；D/Image.h、Color.h；P:728；插件 protocol.py/worker.py capture。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
