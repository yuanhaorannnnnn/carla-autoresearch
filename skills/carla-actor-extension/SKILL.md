---
name: carla-actor-extension
description: 扩展 CARLA actor factory 参数、definition cache 和新 actor 接线；用于开发新类型，既有 vehicle/prop 注册走专用资产 skill。
metadata:
  category: engineering
  execution: workflow
  operations: ''
---

# carla-actor-extension

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：新 actor ID/类型、UE Class/asset、可配置属性与序列化需求、是否启用 factory cache。先读 `UCarlaActorFactoryParameters` 与现有对应 factory，选既有类型扩展还是新增 actor 类；不要仅向 Python blueprint 列表伪造名字。

已有 Editor 入口：Content Browser 的 CarlaActorDefParameters 创建动作经 `UCarlaActorParameterAssetFactory::FactoryCreateNew` 创建 `UCarlaActorFactoryParameters`；编辑 Vehicle/Pedestrian/Sensor/PropParameters 后可调用 `UpdateActorDefinitionCache()`，将 asset 设置到 `UCarlaScriptSettings::CarlaActorFactoryParameters`。运行启用 `-USE_ACTOR_FACTORY_CACHE` 时，system 加载并 DuplicateObject，再 UpdateActorDefinitions；这是运行副本，不会保存源 asset。

具体开发链：定义唯一 `FActorDefinition`/属性 → 对应 factory 的 GetDefinitions/SpawnActor → 确保 UE class 与参数映射 → 需要新 RPC/control 时更新 LibCarla rpc/client/server 及 `PythonAPI/carla/src` binding → 仅保存本次 parameters/Blueprint。注意此基线 `CollectSensorParameters()` 为空，RefreshCache 内 Sensor maps/definitions 的构造也未完成；不能用 SensorParameters 编辑代替 sensor registry/factory 接线。车辆参数 map 当前以 `Param.Make` 为键，新增同 make 项先检查覆盖风险。

产物：源码 diff、参数 asset/definition ID、缓存与非缓存发现路径说明；代码静态链闭合后，构建与运行验证须另有明确授权。失败恢复本次 asset/源改动，避免清空已有 cache 配置。不要直接调用会清除广泛 static props 的 console reclaim 操作来验证新 actor。

路由：新 sensor → `carla-sensor-extension`；已有车辆/prop → `carla-vehicle-assets`/`carla-prop-assets`；运行时生命周期 → `carla-actors`。

Source：`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Actor/CarlaActorFactoryParameters.{h,cpp}`、`CarlaActorFactorySystem.cpp`；`Unreal/CarlaUnreal/Plugins/CarlaTools/Source/CarlaTools/Private/CarlaAssetFactory.cpp`。
