---
name: carla-opendrive-world
description: 将 OpenDRIVE 导入或生成 CARLA world，管理生成地图名、删除及程序化树木建筑；用于 XODR runtime 世界，不负责 OSM 转换或 Editor 离线制图。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# OpenDRIVE 运行时世界

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先验证 XODR 输入内容和用户指定 map_name/map_type，保存原文 hash。此定制基线 `OpendriveGenerationParameters(map_name,map_type="city")` 只有这两个绑定字段，不套用上游 vertex_distance 等参数：

```python
params = carla.OpendriveGenerationParameters(map_name, map_type)
new_world = client.generate_opendrive_world(xodr_text, params, reset_settings=True)
```

另一路为 `client.import_opendrive(xodr_text,map_name,map_type)` 后 `load_opendrive_world(map_name)`；不要两条路线重复执行。`get_generated_maps()`、`is_map_generated(map_name)` 查询；`delete_generated_map(map_name)` 删除生成资产，须明确目标且确认未被使用。`generate_opendrive_trees(density)`、`generate_opendrive_buildings(density)` 改场景；density 合法域按实现核实，不猜百分比。`get_default_phase_table(xodr_text)` 查询生成的默认相位数据。

所有生成/加载导致 episode/资产变化，先清理自有旧世界资源，再取得新 World 与加载状态。解析失败、重名、生成后 topology 空或缺路口分开报告；不自动删除既有地图重试。旧 `config.py` 上游参数与此绑定不一致，不作为可执行契约。

## 交接与证据

[carla-world](../carla-world/SKILL.md)；[carla-osm-conversion](../carla-osm-conversion/SKILL.md)；[carla-opendrive-authoring](../carla-opendrive-authoring/SKILL.md)；[carla-traffic-signals](../carla-traffic-signals/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Client.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
