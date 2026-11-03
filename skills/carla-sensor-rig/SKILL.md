---
name: carla-sensor-rig
description: 配置 CARLA 传感器的父对象、安装位姿和组合布局，挂载或拆卸自有 sensor；用于安装多传感器、调整外参。各传感器物理参数和解码转对应专项，数据采集转 carla-capture。
metadata:
  category: data
  execution: cli
  operations: sensors.describe,sensors.attach,actors.list,actors.destroy
---

# 传感器安装与组合

先读[共享规则](../../references/carla-agent-shared.md)。安装配置包含真实 blueprint、父 actor ID、相对 `transform`、attributes 与配置来源。CARLA 位置使用米、旋转使用度；相对位姿属于父对象坐标系，不能把世界坐标当安装外参。

1. 使用 `actors.list` 核对父对象；只有本 [session](../carla-session/SKILL.md) 拥有的 actor 可以通过 CLI 挂载。外部 actor 可见不代表本任务拥有。
2. 用 `sensors.describe` 核对 blueprint/属性，再读对应专项（如 [RGB](../carla-camera-rgb/SKILL.md)、[MEMS](../carla-lidar-mems/SKILL.md)）。属性未暴露时不强传上游参数。
3. 读取 `carla-agent schema sensors.attach`，传 `session_id`、`parent_id`、`blueprint`、`attributes`，可选 transform 的 `x,y,z,pitch,yaw,roll`。明确写全预期位姿，避免把默认 z=2.5 当作通用安装规范。
4. 返回的 `actor_id` 与原安装参数一同记录；组合安装逐项完成，任一失败时只清理本轮新增 sensor。CLI 尚无批量 rig transaction、保存配置命令或热更新接口，不承诺原子回滚。

```bash
carla-agent sensors attach --profile profile.json --request sensor-attachment.json
```

已有 blueprint 的许多属性只能生成前设置。要改变此类属性，记录配置后销毁并重建自有 sensor；不得将“修改 blueprint 对象”说成已改变活跃实例。重建会改变 sensor ID，采集 manifest 必须记录新身份。sensor 先于其父对象拆除；使用 `actors.destroy` 或关闭所属 session，不能全世界扫删。

安装完成的证据是对象身份、父对象与位姿；收到有效数据另由 [capture](../carla-capture/SKILL.md) 证明。CLI `capture.run` 当前自行生成单车单 sensor，不能消费已经挂载的 rig；多传感器同步使用专用原生流程，不能混用现有 CLI lease。

源码依据：`PythonAPI/carla/src/World.cpp` spawn/attachment 绑定、`PythonAPI/carla/src/Sensor.cpp:45–77`；CLI 契约见 [implementation-contract](../../docs/implementation-contract.md)。
