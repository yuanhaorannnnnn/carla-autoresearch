---
name: carla-map-optimize
description: 审计 CARLA 地图 mesh/material/asset/tag/path，筛选重复对象或在明确范围内做 ISM 合并；性能改善须另有 benchmark。
metadata:
  category: engineering
  execution: native-api
  operations: ''
---

# carla-map-optimize

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：当前 Editor map、明确 actor/level/volume 范围、审计或合并意图、是否保留原 actor。确认 MapOptTool 插件已加载和 `IsEditingMap()`，先取 `GetEditingWorld()`，不要操作 PIE world 或未确认的全图范围。

只读审计优先用 `UMapOptToolBPLibrary::GetAllFeatureOfActors(Actors, RefActorClasses, RefAssets, RefMaterials, RefLevels, RefTags, RefPaths)`；`FindAllSameActors(FMOTSelectActorFilter)` 按明确 filter 找同类。`GetStaticMeshStatsInEditingLevel()`/AnalizeAssets 路径为 C++ helper，未标 BlueprintCallable 的方法不能虚构 Python 暴露。可使用插件现有 UI 或已接线 C++；缺可访问入口时交付 audit 方案与缺口，不把函数名写成 carla-agent 命令。

修改路线为现有插件合并 UI/C++ `MakeInstanceStaticMesh(Volume, ISMActor, StaticMesh, SrcLevelName, bSearchAssetInAllLevels, bRemoveAfterMerge, OutActors)`；限制 Volume/level/asset，默认保留原对象，禁止无授权 `bRemoveAfterMerge=true`。记录每个原 actor 到 ISM instance 的 transform 与 material；已有 custom behavior/collision/semantic tags 不一定可等价合并，先在副本做少量代表对象。`RemoveAllBeInstancedStaticMeshActors()` 为广泛删除入口，不作为自动清理。

产物：统计/候选列表，或合并后的指定 ISM asset/actor、原对象保留/删除清单和保存日志。验收至少核对 world transform、材质、碰撞和标签语义；不能仅因 draw-call 数减少宣称帧率更快。失败恢复本次选择与 map 副本，不清整个场景；性能测试另行固定 workload 执行。

路由：资产材质修复 → `carla-map-materials`；地形 → `carla-terrain`；运行时 scene object 查询 → `carla-scene-objects`。

Source：`Unreal/CarlaUnreal/Plugins/MapOptTool/Source/MapOptTool/Public/MapOptToolBPLibrary.h`、`Private/MapOptToolBPLibrary.cpp`、`Public/MapOptToolWorkContext.h`。
