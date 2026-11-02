---
name: carla-scene-objects
description: 查询 CARLA 环境对象 label/ID/name/transform/bbox、level BB 和 static objects，按授权启停指定环境对象；动态 actor 生命周期与射线查询另走专项。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 环境对象与包围盒

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

`world.get_environment_objects(carla.CityObjectLabel.Buildings)` 返回 EnvironmentObject 列表，保存 id/name/type/transform/bounding_box；默认 Any 可能很大，按 label 和任务区域筛选。`get_level_bbs(bb_type)` 只返回 BB，不带相同对象身份契约；`get_static_objects()` 的 StaticObject 有 id/type/subtype/subtype_name/transform/length/width/height，不把它当 Actor handle。

场景全局修改 `world.enable_environment_objects(env_objects_ids,enable)` 输入环境对象 ID 集合与 bool；先保存明确对象清单，授权后独立原生任务执行。ID 来自当前 episode，不能把 actor ID 或上次地图 ID 传入。`get_names_of_all_objects()` 可用于材质目标发现。

绑定未提供所有对象启用状态 getter；无法知道先前是否禁用时不承诺逆操作完整恢复，使用受控初始场景或说明恢复缺口。空 label、资产未标注、隐藏后 bbox 仍可查询与实际几何可见性分开报告。不要据 BB 重叠宣称碰撞发生，也不清理所有场景对象以解决单点遮挡。

## 交接与证据

[carla-actors](../carla-actors/SKILL.md)；[carla-scene-query](../carla-scene-query/SKILL.md)；[carla-scene-materials](../carla-scene-materials/SKILL.md)；[carla-ground-truth](../carla-ground-truth/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/World.cpp`、`PythonAPI/carla/src/Actor.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
