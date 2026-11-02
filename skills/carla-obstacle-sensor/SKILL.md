---
name: carla-obstacle-sensor
description: 配置 CARLA 前方障碍探测事件；用于检测距离、sweep 半径、only_dynamics 和障碍事件距离，区别于已经发生的 collision。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.other.obstacle
---

# Obstacle detector

精确 blueprint：`sensor.other.obstacle`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.other.obstacle"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

distance/hit_radius为Float meters（推荐5/0.5），only_dynamics/debug_linetrace为Bool，sensor_tick为Float seconds。探测沿sensor朝向，用sphere sweep而非无宽度单射线；安装姿态与半径决定检测体积。only_dynamics=true选择AllDynamicObjects，否则实现使用静态通道，具体可见对象仍受collision response影响。

回调ObstacleDetectionEvent.actor/other_actor为actor引用，distance为float meters；frame/timestamp/transform随SensorData。只有命中才发送事件，不是每tick一个distance帧，也不把没有回调的窗口补成distance=0。

## 最短采集与恢复

describe → 保存distance/hit_radius/only_dynamics和安装朝向 → 原生脚本自有挂载 → 在有界tick/观察窗内监听并保存事件或有证据的无事件窗。不要为验证制造实际碰撞；提前检测与collision有不同契约。

未检出先核对朝向、range、radius、对象通道与动态筛选，再查listener。debug_linetrace是可视化副作用，仅请求时开启。当前capture.run不支持obstacle；事件语义见 [object事件段](../../references/sensors-object-contracts.md)。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-collision-sensor](../carla-collision-sensor/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/ObstacleDetectionSensor.cpp:25、PostPhysTick；A:2408；D/ObstacleDetectionEvent.h；Z/ObstacleDetectionEventSerializer.h；P:869。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
