---
name: carla-large-map
description: 在 Editor 生成或整理 CARLA main map、tile maps 和 tile 元信息；不处理运行时 streaming 策略、navmesh 或完整打包。
metadata:
  category: engineering
  execution: conditional
  operations: ''
---

# carla-large-map

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：唯一 MapName、UE DestinationPath、SizeX/SizeY、GlobalHeightmap、必要 Blueprint class 与已授权的目标范围。使用 `FMapGeneratorMetaInfo`，不要混用运行时米制坐标与 UE 厘米；先核对 current implementation 的 tile 尺寸和命名规则，旧资产不得覆写。需要匹配 Content 中 landscape/main-map templates 和 Editor widget 实现。

在现有 `UMapGeneratorWidget` 派生 Editor Utility Widget 中调用 `GenerateMapFiles(MetaInfo)`；它依次 CreateTilesMaps、CreateMainLargeMap、CreateOpenDriveFile。部分失败只记日志仍继续，因此不能以 void 返回/按钮结束判断全成功。`LoadMapInfoFromPath(InDirectory, OutMapSize, OutFoundMapName)` 可核对现有路径；`SanitizeDirectory` 处理 UE 路径格式。需要复制基础 world 可调用 `DuplicateWorld(BaseWorldPath, TargetWorldPath, NewWorldName)`，先核对输入存在和目标空闲。

生成后核对 main map 的 LargeMapManager、各 `_Tile_` world、坐标索引/原点与辅助 XODR，抽查相邻 tile 的道路/地形连接；只有源码/资产检查时明确未取得 runtime streaming 证据。工具的 SaveWorld 会保存 dirty packages，使用隔离 Editor，不夹带他人编辑。地图生成依赖的 BlueprintImplementableEvent 如 UpdateTileRT/AssignLandscapeMaterial 未实现时列具体缺口，不能只靠 C++ 名称宣称可用。

产物：main/tile `.umap` 路径、MetaInfo、辅助 ODR、日志和缺失 tiles。失败按每阶段已经写出的文件恢复，不把整个 Content 包删除重建。LargeMapManager runtime streaming/dormancy 不由此 skill 接管。

路由：地形接缝/碰撞 → `carla-terrain`；植被/水体 → `carla-map-dressing`；ODR 空实现边界 → `carla-opendrive-authoring`；Nav/TM/cook 各专项。

Source：`Unreal/CarlaUnreal/Plugins/CarlaTools/Source/CarlaTools/Public/MapGeneratorWidget.h` 和 `Private/MapGeneratorWidget.cpp` 的 GenerateMapFiles/CreateTilesMaps/CreateMainLargeMap；`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/MapGen/LargeMapManager.h`。
