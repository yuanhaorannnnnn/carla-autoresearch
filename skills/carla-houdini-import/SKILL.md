---
name: carla-houdini-import
description: 把已有 Houdini 导出 actors 接入 CARLA large-map sublevels 并校正 tile 坐标；不执行外部 Houdini 建模或 graph。
metadata:
  category: engineering
  execution: conditional
  operations: ''
---

# carla-houdini-import

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：已导入 UE 的 actor 列表、有效 ALargeMapManager、目标 ULevelStreaming、tile origin、原始坐标/单位记录。依赖已有 large-map/levels 与 Houdini 产物，不因存在 widget 头文件就推定 Houdini 软件或插件已安装。先备份 actors 的 level、transform 和实例 mesh，确认只处理指定对象。

原生 Editor Blueprint 入口为 `UHoudiniImporterWidget` 的静态方法：已有 LargeMapManager 先 `CreateSubLevels(LargeMapManager)`，然后 `MoveActorsToSubLevelWithLargeMap(Actors, LargeMapManager)`；明确某个 streaming level 时可用 `MoveActorsToSubLevel(Actors, Level)`。仅在需本任务坐标校正时执行 `UpdateGenericActorCoordinates(Actor, TileOrigin)`。HISM 的 UpdateInstancedMeshCoordinates 是 C++ helper，不虚构公开 Python 调用；必须观察其实际调用路径，避免重复加减 tile origin。

`UseCOMasActorLocation(Actors)` 会改变 actor pivot/位置策略，先保留 transform；`GetNumberOfClusters(ActorList, OutNumClusters)` 要求名字 `b<building>c<cluster>of<clustersize>`，解析失败不自动改名。需要卸载本任务 levels 才调用 `ForceStreamingLevelsToUnload(LargeMapManager)`，不打断用户编辑中的其他 level。

产物：actor→sublevel 映射、调整前后 transform、实例 mesh 状态、保存的 levels；检查跨 tile world-space 位置一致。移动成功不证明模型完整、材质/碰撞或 runtime streaming 正确。失败恢复原 level 与 transform，处理已移动子集，不能再跑一遍坐标操作叠加偏移。

路由：Houdini 外部资产制作需用户明确另行范围；large-map → `carla-large-map`；mesh 导入 → `carla-fbx-import`；材质 → `carla-map-materials`。

Source：`Unreal/CarlaUnreal/Plugins/CarlaTools/Source/CarlaTools/Public/HoudiniImporterWidget.h` 及 `Private/HoudiniImporterWidget.cpp`。
