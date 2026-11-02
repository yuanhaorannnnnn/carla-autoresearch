---
name: carla-sensors
description: 兼容旧 carla-sensors 入口，仅在显式指定旧名称或尚未确定传感器类型时使用；按请求路由到具体传感器专项或 carla-sensor-rig。
metadata:
  category: compatibility
  execution: alias
  operations: ''
---

# 旧 sensor 入口路由

仅做分流，不再承包全部 sensor 操作。查询/配置/数据解释进入对应专项：

- 相机：[RGB](../carla-camera-rgb/SKILL.md)、[depth](../carla-camera-depth/SKILL.md)、[semantic](../carla-camera-semantic/SKILL.md)、[instance](../carla-camera-instance/SKILL.md)、[normals](../carla-camera-normals/SKILL.md)、[optical flow](../carla-camera-optical-flow/SKILL.md)、[DVS](../carla-camera-dvs/SKILL.md)、[fisheye](../carla-camera-fisheye/SKILL.md)、[stereo](../carla-camera-stereo/SKILL.md)。
- LiDAR：[raycast](../carla-lidar-raycast/SKILL.md)、[semantic](../carla-lidar-semantic/SKILL.md)、[MEMS](../carla-lidar-mems/SKILL.md)、[CPU AT128](../carla-lidar-at128/SKILL.md)、[GPU SceneCapture](../carla-lidar-gpu/SKILL.md)。
- 雷达：[raycast](../carla-radar-raycast/SKILL.md)、[Oasis](../carla-radar-oasis/SKILL.md)、[mmwave](../carla-radar-mmwave/SKILL.md)。
- 其他：[ultrasonic](../carla-ultrasonic/SKILL.md)、[IMU](../carla-imu/SKILL.md)、[GNSS](../carla-gnss/SKILL.md)、[target](../carla-target-sensor/SKILL.md)、[obstacle](../carla-obstacle-sensor/SKILL.md)、[collision](../carla-collision-sensor/SKILL.md)、[lane invasion](../carla-lane-invasion-sensor/SKILL.md)、[RSS](../carla-rss/SKILL.md)。

父对象/位姿/挂载转 [sensor-rig](../carla-sensor-rig/SKILL.md)，采集窗口与同步转 [capture](../carla-capture/SKILL.md)。不确定类型时先用 `blueprints.list`/`sensors.describe` 只读发现，不自动挂载或采集。所有操作仍遵循[共享规则](../../references/carla-agent-shared.md)。
