---
name: carla-opendrive-authoring
description: 检查和接入 Editor 的 OpenDriveToMap ODR/tiles 制作路径；本基线道路网格/标线生成有空实现，不承诺完整 ODR→地图制作。
metadata:
  category: engineering
  execution: conditional
  operations: ''
---

# carla-opendrive-authoring

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：有效 XODR、目标 map/level、BaseLevelName、tiles/边界、材质/heightmap 与期望交付。先说明本基线的硬边界：`GenerateRoadMesh()`、`GenerateLaneMarks()`、`CreateTerrain()` 为空；`GenerateAll()` 内 `GenerateSpawnPoints(...)` 调用被注释。不能把函数声明或 Valid Map 日志当作道路、标线、spawn points 已生成。

现有 UE `UOpenDriveToMap` 属性包括 FilePath、MapName、BaseLevelName、CurrentTilesInXY、默认材质、TileSize/Tile0Offset、DefaultHeightmap/MinHeight/MaxHeight。已有 large-map 时可从 Editor Blueprint 的 `GenerateTile()` 路径读取 FilePath，解析 XODR，加载 BaseLevelName 中 LargeMapManager、得到 tile 元信息并加载当前 tile；`GoNextTile()`/`ReturnToMainLevel()` 管理切换，必须逐项保存范围，不能盲遍历全部 tile。`GenerateTileStandalone()` 调 BlueprintImplementableEvent `ExecuteTileCommandlet` 后保存 dirty packages，缺相应 Blueprint 实现时没有完整 commandlet 动作。

`CreateMap()` 实际用 Url 启动下载，随后 OSM→XODR、保存并 LoadMap，并非直接导入任意本地 XODR 的万能入口。用户给本地 ODR 时优先做解析/元信息和现有接线路径核验；要求完整道路资产时，交付缺失函数及可选实现设计，不自动补代码、调用外部 DCC 或宣称成功。运行时生成可路由 `carla-opendrive-world`，但它不产出同等 Editor authored asset。

产物：解析状态、实际加载的 tile/level、已有生成资产及明确缺失的道路/标线/terrain/spawn 项。Editor 操作可能 save-all，必须隔离会话。恢复按实际保存的 map/asset 备份；无产物就明确无产物。

路由：large-map 元信息 → `carla-large-map`；heightmap 生成 → `carla-terrain`；mesh 导入替代 → `carla-fbx-import`；运行时 ODR → `carla-opendrive-world`。

Source：`Unreal/CarlaUnreal/Plugins/CarlaTools/Source/CarlaTools/Public/OpenDriveToMap.h` 及 `Private/OpenDriveToMap.cpp`，尤其 GenerateAll 与空函数。
