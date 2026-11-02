---
name: carla-scene-materials
description: 构造 CARLA Color/FloatColor 纹理并应用到自有 actor 或授权对象的 diffuse/emissive/normal/ARM 通道；不制作 UE 材质资产，World 旧贴图入口为 deprecated。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 运行时纹理与材质通道

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先发现目标 actor 或 `world.get_names_of_all_objects()` 的精确 object name，限制修改范围。独立原生任务自有 actor 优先使用 `actor.apply_texture(material_parameter,texture)`；参数为实际 `carla.MaterialParameter.Diffuse/Emissive/Normal/AO_Roughness_Metallic_Emissive`。

```python
texture = carla.TextureColor(width, height)
texture.set(x, y, carla.Color(r, g, b, a))
actor.apply_texture(carla.MaterialParameter.Diffuse, texture)
```

TextureColor 是 uint8 Color，TextureFloatColor 用 FloatColor；均有 width/height、set_dimensions/get/set，像素坐标须在界内。浮点 HDR/emissive/normal 与颜色通道语义不同，不能把所有图片当 RGB byte。

静态对象旧 `world.apply_color_texture_to_object(name,parameter,texture)` / float 版本及 objects 批量入口仍有绑定但标记 deprecated；批量名单必须明确。四纹理 `apply_textures_to_object(name,diffuse,emissive,normal,ao_roughness_metallic_emissive)` 类型按绑定核对。

错误纹理类型、名称未匹配、材质无通道需保留实际失败；setter 返回不证明屏幕/采集更新。没有原纹理 getter，不能保证恢复旧材质；使用自有可重建 actor，或授权的受控场景并明确恢复缺口，不覆盖 UE 资产文件。

## 交接与证据

[carla-scene-objects](../carla-scene-objects/SKILL.md)；[carla-map-materials](../carla-map-materials/SKILL.md)；[carla-capture](../carla-capture/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`、`PythonAPI/carla/src/World.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
