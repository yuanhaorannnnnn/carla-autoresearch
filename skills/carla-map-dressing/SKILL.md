---
name: carla-map-dressing
description: 离线布置 CARLA 地图的植被、misc actors、ROI、水体或 weather actor 并保存；实时天气与灯光操作走运行时 skills。
metadata:
  category: engineering
  execution: conditional
  operations: ''
---

# carla-map-dressing

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：目标 map/tile、FMapGeneratorMetaInfo、FoliageSpawners、ROI 数据、指定 actor classes/river preset/weather 名称与修改范围。先记录现有实例与 dirty packages；依赖匹配 Content 的 foliage/river/weather Blueprint，以及 widget 的具体 BlueprintImplementableEvent。

在 `UMapGeneratorWidget` 派生 Editor widget 选择具体动作，不一键重造全部地图：`CookVegetationToCurrentTile(FoliageSpawners)` 仅当前 world；`CookVegetation(MetaInfo)` 遍历符合 `_Tile_` 名称的 tiles。ROI 用 `CreateVegetationRoisMap(...)`、`CreateMiscSpreadedActorsRoisMap(...)`、`CreateMiscSpecificLocationActorsRoisMap(...)` 构造后分别 `CookMiscSpreadedInformationToTiles(MetaInfo)` 或 `CookMiscSpecificLocationInformationToTiles(MetaInfo)`。这些 Cook 是离线布置，不是 UE package cook。

水体用 `GenerateWater(RiverClass)` 或 `GenerateWaterFromWorld(RiversWorld,RiverClass)`；地图 weather actor 用 `AddWeatherToExistingMap(WeatherActorClass, MetaInfo, SelectedWeather)`，实现已有时返回现有 actor，不假定创建了新的。调用 Blueprint 事件生成 river sublevel/spline 时必须检查实现存在。保存前核对实例数、类别、位置和预期范围。

删除入口 `DeleteAllVegetationInMap(Path,MapName)` 与 `DeleteAllSpreadedActors(MetaInfo)` 作用广，只有明确删除范围授权才执行；不能把删除当作补种的自动前置。产物为变更 levels/actors、ROI 配置、保存日志。缺依赖保留当前资产与失败阶段；恢复本任务 map/actor 增量，不清空其他植被或装饰。

路由：terrain/tiles → `carla-terrain`/`carla-large-map`；运行时天气/灯 → `carla-weather`/`carla-scene-lights`；ODR tree positions 空实现 → `carla-opendrive-authoring`。

Source：`Unreal/CarlaUnreal/Plugins/CarlaTools/Source/CarlaTools/Public/MapGeneratorWidget.h`、`Private/MapGeneratorWidget.cpp`；`Public/RegionOfInterest.h`。
