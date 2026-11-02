---
name: carla-terrain
description: 处理 CARLA Editor heightmap 地形、tile 接缝与碰撞重算；不把空 CreateTerrain 方法或保存成功当作可驾驶性验证。
metadata:
  category: engineering
  execution: conditional
  operations: ''
---

# carla-terrain

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：GlobalHeightmap/DefaultHeightmap、空间范围、高度上下限、tile 索引、目标 landscape 与写入范围。先检查纹理分辨率/高度映射、UE 厘米坐标、已有 landscape 和相邻边界备份。`UOpenDriveToMap::CreateTerrain()` 当前为空，不调用它宣称生成；`CreateTerrainMesh(MeshIndex, Offset, GridSize, GridSectionSize)` 是另一个原生 mesh 路径，需核对 heightmap/GetHeight 输入，而非等同完整 landscape generator。

实际 large-map 地形路线使用 `UMapGeneratorWidget` 的 MetaInfo.GlobalHeightmap 与 widget 的 `UpdateTileRT`、`AssignLandscapeMaterial` Blueprint 实现，再由 `GenerateMapFiles(MetaInfo)` 内 CreateTilesMaps 生成 Landscape，内部 SmoothHeightmap/SewUpperAndLeftTiles 处理边界。这些内部 helper 没有公共 Blueprint API，不虚构可直接调用的 Python 方法。现有图只需重算碰撞时用 `RecalculateCollision()`；该实现直接取得首个 ALandscape 并解引用，必须先确认当前 level 有且是期望 landscape。多 tile 用 `CookTilesCollisions(MetaInfo)`，这会加载/写多个 level，先确认全范围。

产物：heightmap/参数、实际 landscape/tile maps、接缝前后检查、collision 重建与保存日志。碰撞生成不证明车辆稳定/Walker 可走；缺 Runtime 验证就明确。需要土壤参数标定属另行研究，不能凭视觉 terrain 代替物理结论。

失败按本次 level/heightmap 备份恢复，保留源高度图；空 level、缺 Blueprint 事件、无 Landscape 时停止对应动作，不自动创建未知规模世界。工具可能 SaveDirtyPackages，必须隔离会话。

路由：初建 tile → `carla-large-map`；ODR 道路 → `carla-opendrive-authoring`；装饰 → `carla-map-dressing`；步行 nav → `carla-navmesh`。

Source：`Unreal/CarlaUnreal/Plugins/CarlaTools/Source/CarlaTools/Private/OpenDriveToMap.cpp` 的 CreateTerrain/CreateTerrainMesh；`Public/MapGeneratorWidget.h` 和 `Private/MapGeneratorWidget.cpp` 的 CreateTilesMaps/SmoothHeightmap/SewUpperAndLeftTiles/RecalculateCollision。
