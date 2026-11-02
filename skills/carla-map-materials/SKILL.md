---
name: carla-map-materials
description: 独立恢复已导入 CARLA 地图的语义目录、road painter/decals 和 cook 前地图准备；不重导全部 FBX，不编写 shader 或打包。
metadata:
  category: engineering
  execution: native-api
  operations: ''
---

# carla-map-materials

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：已导入 package 名、目标 map 名列表、package/roadpainter decals 配置、现有 UE5 Editor、资产修改授权。确认 `Content/<Package>/Config/<Package>.Package.json` 等真实配置位置，以 `GetFirstPackagePath` 的实际搜索为准。先检查 package 中 assets 和 map 路径，保留被移动/改材质的目标备份。

在 CARLA_ROOT，使用现有 `UnrealEditor <uproject>` 逐阶段调用，不经 Import.py 的 UE4 launcher：

```text
-run=MoveAssets -PackageName=<Package> -Maps="<MapA> <MapB>"
-run=PrepareAssetsForCooking -PackageName=<Package> -OnlyPrepareMaps=1
-run=LoadAssetMaterials -PackageName=<Package>
```

MoveAssets 为 semantic segmentation 移动 map meshes 到标签目录；PrepareAssetsForCooking 根据 package 描述创建/保存地图、处理 spawn points 与 MapPaths/PackagePath 文件；LoadAssetMaterials 读取 road painter/decals 并应用材质。函数参数与旧 Import.py 的封装一致，但实际 UE5 commandlet 运行仍需观察退出码与日志。恢复时选择失败阶段所需的最小 commandlet；不要在前阶段成功后重跑整个 import pipeline。

产物：变更的 asset 路径/redirectors、保存的 `.umap`、材质与 decals 日志、辅助路径文件；逐图核对保存与引用。Commandlet 名含 prepare/cooking 不表示已 cook/package。失败保留部分产物并核对 package JSON、地图名、材质 Blueprint/road painter 依赖；禁止用错误语义目录强行通过。

路由：缺基础 mesh → `carla-fbx-import`；运行时贴图 → `carla-scene-materials`；cook → `carla-map-cook`。

Source：`Util/BuildTools/Import.py` 的 load_asset_materials_commandlet、prepare_maps_commandlet_for_cooking、move_assets_commandlet；`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Commandlet/{LoadAssetMaterials,MoveAssets,PrepareAssetsForCooking}Commandlet.h` 及同名 `.cpp`。
