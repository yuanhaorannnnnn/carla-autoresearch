---
name: carla-osm-conversion
description: 使用条件编译的 Osm2Odr 将 OSM XML 转为 OpenDRIVE，配置投影、偏移、道路过滤与信号生成；转换结果交 opendrive-world，不承诺道路运行正确。
metadata:
  category: runtime
  execution: conditional
  operations: ''
---

# OSM 转 OpenDRIVE

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先检查所选 wheel 的 `hasattr(carla,"Osm2Odr")` 与 `Osm2OdrSettings`；缺失说明 `CARLA_PYTHON_API_HAS_OSM2ODR` 能力未包含，转工程构建，不安装其他 wheel 覆盖现环境。

```python
settings = carla.Osm2OdrSettings()
settings.center_map = True
settings.default_lane_width = lane_width_m
xodr = carla.Osm2Odr.convert(osm_xml_text, settings)
```

输入是 OSM XML 内容，返回 OpenDRIVE 字符串；不是传入文件路径让 server 读取。可设置 `use_offsets/offset_x/offset_y/proj_string/elevation_layer_height/generate_traffic_lights/all_junctions_with_traffic_lights`；用 `set_osm_way_types([...])` 和 `set_traffic_light_excluded_way_types([...])` 限制 highway 类型。记录投影、中心/偏移选择和过滤条件，以供世界坐标解释。

保留原始 OSM 与输出，显式路径写新文件；转换本身不加载 CARLA world。输入不完整、投影失败、输出缺 roads、非法 highway 类型分别处理；不要自动放宽过滤来凑非空结果。生成后需另验证 topology、junction 和目标道路连通。

## 交接与证据

[carla-opendrive-world](../carla-opendrive-world/SKILL.md)；[carla-map](../carla-map/SKILL.md)；[carla-build-python-api](../carla-build-python-api/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/OSM2ODR.cpp`、`PythonAPI/carla/src/PythonAPI.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
