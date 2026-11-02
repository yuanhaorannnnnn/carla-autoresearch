---
name: carla-vehicle-assets
description: 将已有车辆 Blueprint 注册到 CARLA factory 并核对保存/运行时可发现性；不负责车辆建模、USD 导入或动力学标定。
metadata:
  category: engineering
  execution: conditional
  operations: ''
---

# carla-vehicle-assets

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：已存在车辆 Blueprint 的 UE asset path、make/model/generation/base_type、目标 factory 路线和修改范围。先检查当前项目使用传统 VehicleFactory 还是 `UCarlaActorFactoryParameters` cache；不要同时写两套配置造成重复或假成功。

传统 helper 位于 `Unreal/CarlaUnreal/Plugins/CarlaTools/Content/Python/add_vehicle_to_vehicle_factory.py`，需在启用 Unreal Python 的 Editor 环境执行，参数 `--vehicle_blueprint_path <asset-object-path-without-_C> --name <model>`。它读取 `/Game/Carla/Blueprints/Vehicles/VehicleFactory.VehicleFactory_C` 的 CDO，加载 `<path>_C`，构造 `VehicleParameters`：make 固定 `usd`、model 为 name、generation 固定 2、base_type 固定 car，然后仅 `vehicle_list.append(...)`。

关键缺口：helper 没有 set_editor_property、mark dirty、save 或写 JSON；不能把脚本运行称为注册已持久化，也不直接用于用户指定其他 make/generation。按当前 factory 实际资产模型，在 Editor 对目标 Vehicles 数组显式提交并仅保存对应 factory/Blueprint，随后卸载重载回读数组；若无法确认 CDO 修改是否回写 Blueprint，停在内存状态，交付待完成步骤。cache 模式改对应 parameters asset 的 VehicleParameters，并执行 UpdateActorDefinitionCache，按 actor-extension 约束检查 cache。

产物：具体 factory asset、条目字段、保存/重载证据；再在获授权的运行实例查询 blueprint library 的实际 vehicle ID 和 generation。spawn/运动另行验证。失败撤回本次新增条目，恢复目标 asset，不能改动已有车辆。

路由：cache 结构/新类型 → `carla-actor-extension`；USD → `carla-usd-import`；运行时 actor → `carla-actors`；物理参数 → `carla-vehicle-physics`。

Source：上述 helper；`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Actor/Factory/VehicleActorFactory.cpp`；`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Actor/CarlaActorFactoryParameters.cpp`。
