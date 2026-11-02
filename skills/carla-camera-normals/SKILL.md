---
name: carla-camera-normals
description: 配置 CARLA 法线相机并正确读取颜色编码法线；用于表面方向图、法线显示和坐标空间核验，识别 Image 模板别名而非虚构 NormalsImage Python 类型。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.camera.normals
---

# Normals camera

精确 blueprint：`sensor.camera.normals`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.camera.normals"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

该sensor调用专用MakeNormalsCameraDefinition：image_size_x/y为Int pixels，fov为Float degrees，send_data_stream为Bool，sensor_tick为Float seconds；lens_circle_falloff/multiplier、lens_k/kcube、lens_x_size/y_size为Float。不把RGB的全套fx/k1–k6/曝光属性强塞给它。

registry选NormalsImageSerializer；D/Image.h的NormalsImage是ImageTmpl<Color> alias，与Image同一模板类型，Python输出使用Image绑定，BGRA8每像素4字节。源构造Enable16BitFormat(false)，不是FloatImage/float32 normals；详见 [camera法线段](../../references/sensors-camera-contracts.md)。

## 最短采集与恢复

describe → 原生脚本自有挂载 → native listener确认Image与长度 → 保存BGRA原始图 → 取RGB。`2*RGB/255-1`只能作为常见编码的候选解码；必须检查NormalsEffectMaterial或已知平面的朝向样例，才确认空间、轴向与归一化，不从像素布局推断world-space。

方向/符号不对先区分BGRA顺序、材质编码、sensor/world空间与坐标系；不要用normalize掩盖错误解码。无数据检查AreClientsListening和渲染读回链，RGB发送开关不替代本派生实现分析。当前capture.run不支持normals。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-camera-depth](../carla-camera-depth/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/NormalsCamera.cpp:11；A:1195；D/Image.h；Z/NormalsImageSerializer.cpp；P:728（同模板绑定）；SensorRegistry.h:88。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
