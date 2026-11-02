---
name: carla-carsim
description: 启用 CARLA CarSim 插件 simfile、切换 CarSim 道路模型并核对后端失败；依赖安装/构建与 server 可读 simfile，UDP CarSim 走独立入口。
metadata:
  category: runtime
  execution: conditional
  operations: ''
---

# CarSim 插件动力学

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先检查实际 wheel 有 `enable_carsim/use_carsim_road`，server 构建与日志能确认 CarSim plugin，simfile 与运行库在 server 上可读且授权可用。绑定存在不足以证明许可证/二进制能初始化；缺条件则停止，不偷偷换默认动力学。

独立原生任务创建可销毁自有 vehicle，记录原默认模型/起始状态后 `vehicle.enable_carsim(simfile_path)`，按实验需要 `vehicle.use_carsim_road(enabled)`；输入路径按 server 解释，不默认客户端同名路径有效。控制仍由 vehicle-control 单一来源提交。

初始化失败、库加载/许可证错误、道路模型/坐标不符与控制无响应分开保留。查看 server 日志与有界位置/速度响应，不因 setter 无返回而宣称 CarSim 正在运行。

UE 内有创建默认 movement component 的恢复分支，但 Python 无通用 disable_carsim/restore 绑定。不得编造调用；清理本任务车辆后重建默认车辆，或报告尚未恢复。不能用 `use_carsim_road(False)` 声称退出 CarSim backend。

## 交接与证据

[carla-vehicle-control](../carla-vehicle-control/SKILL.md)；[carla-vehicle-physics](../carla-vehicle-physics/SKILL.md)；[carla-carsim-udp](../carla-carsim-udp/SKILL.md)；[carla-actors](../carla-actors/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`、`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Vehicle/MovementComponents/CarSimManagerComponent.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
