---
name: carla-chrono
description: 用 CARLA 条件支持的 Chrono vehicle/powertrain/tire JSON、base path 与 substep 切换动力学；需 server 的 Chrono 构建和模型资产，不管理其他后端。
metadata:
  category: runtime
  execution: conditional
  operations: ''
---

# Chrono 动力学

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先核对 wheel 绑定、server Chrono 构建/库、JSON 版本与 server 路径；读取文件存在/内容版本不等于 Chrono 初始化成功。独立原生任务创建可重建车辆，设定明确正 max_substeps、max_substep_delta_time 并与 world fixed delta 协调。

```python
vehicle.enable_chrono_physics(
    max_substeps=n, max_substep_delta_time=dt,
    vehicle_json=vehicle_file, powetrain_json=powertrain_file,
    tire_json=tire_file, base_json_path=model_root)
```

关键字确为 **`powetrain_json`**，不要修正为 powertrain_json。记录模型路径/hash、地形适配和控制输入；JSON 参数属于 Chrono，不改用 Chaos PhysicsControl 假装调整了该模型。

缺运行库、JSON 相互引用、地形碰撞与默认后端回退分别查日志和有界轨迹。内部有默认组件恢复路径，Python 未暴露通用 disable_chrono_physics；只能在获授权的自有资源生命周期中销毁重建，或明确未恢复。绑定或文件存在不构成动力学精度证据。

## 交接与证据

[carla-vehicle-physics](../carla-vehicle-physics/SKILL.md)；[carla-vehicle-control](../carla-vehicle-control/SKILL.md)；[carla-clock](../carla-clock/SKILL.md)；[carla-actors](../carla-actors/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`、`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Vehicle/MovementComponents/ChronoMovementComponent.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
