---
name: carla-collision-sensor
description: 监听和解释 CARLA 碰撞事件；用于碰撞双方、normal_impulse、事件去重与碰撞/overlap 通道排障，不用于提前避障或连续距离流。
metadata:
  category: sensors
  execution: native-api
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.other.collision
---

# Collision sensor

精确 blueprint：`sensor.other.collision`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.other.collision"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 配置与数据

此generic sensor definition主要提供role_name；不能假定具有sensor_tick、range或hit_radius。父actor碰撞设置与物理响应决定是否触发，不能仅因sensor生成成功称已配置有效碰撞检测。

CollisionEvent.actor/other_actor为actor引用，normal_impulse为Vector3D float32，单位kg·m/s；不是力（N）、速度或加速度。实现将UE冲量乘1e-2转换单位，物理碰撞与overlap补充路径需分别核对。OnCollisionEvent对同frame/actor pair去重，不代表返回了每个接触点或全部峰值。

## 最短采集与恢复

describe → 原生脚本挂到自有parent → 监听有界观察窗，保存双方ID/type、normal_impulse.xyz/norm与frame/time；没有发生碰撞时无事件是允许情形，但需要窗口/tick证据。不能为了证明监听成功擅自撞车。

无事件先查parent/physics、collision response和是否真的接触，再查listener；无碰撞不等于数据通道故障。多回调按实际frame和对象记录，不跨frame盲目去重。当前capture.run不支持collision；结束停止监听并清理自有资源。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-obstacle-sensor](../carla-obstacle-sensor/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/CollisionSensor.cpp:26、SetOwner、OnCollisionEvent、OnCollisionOverlapEvent；D/CollisionEvent.h；Z/CollisionEventSerializer.h；P:862。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
