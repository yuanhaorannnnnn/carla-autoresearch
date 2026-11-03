---
name: carla-usd-import
description: 核查或接入 CARLA 的 USD prop/vehicle 导入、wheel/light 和车辆 Blueprint 路线；当前 Omniverse 构建分支未实现，不承诺开箱可用或通用地图 USD 导入。
metadata:
  category: engineering
  execution: conditional
  operations: ''
---

# carla-usd-import

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：USD 文件、目标 UE asset path、prop/vehicle 类型、wheel templates/light metadata、现有 Omniverse 插件与编译证据。先明确硬阻塞：`CarlaTools.Build.cs` 的 EnableNVIDIAOmniverse 分支添加 WITH_OMNIVERSE/OmniverseUSD/OmniverseRuntime 后抛 `NotImplementedException`；USDImporterWidget 的实际导入受 WITH_OMNIVERSE 保护。仅有 API 声明或 `UUSDImporterActor` 空实现不能证明可用。

当前基线默认只做依赖/接线诊断与输入准备，不直接尝试 enable flag、安装外部插件或构建。若用户提供已修复且编译验证的环境，再核实原生 `UUSDImporterWidget::ImportUSDProp(USDPath, DestinationAssetPath, bAsBlueprint)` 或 `ImportUSDVehicle(USDPath,DestinationAssetPath,BaseWheelData,LightList,WheelObjects,bAsBlueprint)`；其委托 UUSDCARLAInterface::ImportUSD。车辆后处理有 SplitVehicleParts、GenerateVehicleMeshes、GenerateNewVehicleBlueprint(World,BaseClass,NewSkeletalMesh,NewPhysicsAsset,DestPath,VehicleMeshes,WheelTemplates)、EditSkeletalMeshBones/CopyCollisionToPhysicsAsset，不能省略 skeleton/physics/wheel 输入就称生成完整车辆。

产物：当前环境的具体阻塞与待接线路径；条件满足后才交付导入 asset/Blueprint、wheel/light、physics metadata 与日志。导入与 factory 注册分开，已生成 Blueprint 不等于运行时 vehicle 可发现。失败只处理本次目标路径的部分资产，保留原 USD；不自动重建整包或安装 Omniverse。

路由：车辆注册 → `carla-vehicle-assets`；props → `carla-prop-assets`；FBX → `carla-fbx-import`；完整地图制作 → `carla-large-map`。USD 构建接线修复属于另行开发授权。

Source：`Unreal/CarlaUnreal/Plugins/CarlaTools/Source/CarlaTools/CarlaTools.Build.cs`、`Public/USDImporterWidget.h`、`Private/USDImporterWidget.cpp`；`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/MapGen/USDImporterActor.cpp`。
