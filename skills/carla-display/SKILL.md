---
name: carla-display
description: 管理 CARLA quality、窗口和 secondary HDMI/device/Xserver sensor viewport；用于本地或多显示设备显示，依赖显示环境与插件，不负责 sensor 原始采集。
metadata:
  category: runtime
  execution: conditional
  operations: ''
---

# 显示与 secondary viewport

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先检测实际显示会话、窗口与 CarlaDisplayUtil/XWindowForCarla 插件能力；headless/server 无窗口时报告条件，不安装显示服务或改登录环境。

只读 `world.get_quality()`、`get_secondary_num()`、`get_all_secondary_hdmi_info()`、`get_hdmi_info_on_secondary(secondary_id)` 发现真实 secondary/device ID。授权后 `set_quality(level)` 输入此基线整数级别，按实现核实枚举，不猜 Low/Epic 字符串；`minimize_window/restore_window/force_window_to_front` 改用户窗口。

sensor viewport 输入真实自有 sensor actor_id：`assign_viewport_on_secondary_for_sensor(actor_id,secondary_id,device_id=-1)`；定位版本 `_ip(actor_id,secondary_id,x,y,device_id=-1)` 的 x/y 是窗口位置参数，不是网络 IP 字符串；Xserver 用 `assign_viewport_with_xserver_id(actor_id,secondary_id,x,y,xserver_id)`。

保存原 quality、显示目标和可读配置；没有完整 viewport getter/反向 API 时明确恢复限制。无图像先查 sensor 是否在流、device/secondary 是否存在、Xserver 权限与插件，不自动换主显示器。画面显示成功不证明 capture 原始文件完整；API 返回不等于物理显示器已经呈现。

## 交接与证据

[carla-spectator](../carla-spectator/SKILL.md)；[carla-sensor-rig](../carla-sensor-rig/SKILL.md)；[carla-capture](../carla-capture/SKILL.md)；[carla-server](../carla-server/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/World.cpp`、`Unreal/CarlaUnreal/Plugins/CarlaDisplayUtil`、`Unreal/CarlaUnreal/Plugins/XWindowForCarla`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
