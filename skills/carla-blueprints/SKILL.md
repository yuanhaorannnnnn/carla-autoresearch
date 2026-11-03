---
name: carla-blueprints
description: 筛选 CARLA ActorBlueprint，读取属性类型、推荐值、可修改性并构造合法生成属性；用于蓝图发现和参数校验，不制作 UE Blueprint 或解释各 sensor 物理模型。
metadata:
  category: runtime
  execution: cli
  operations: 'blueprints.list'
---

# 蓝图与生成属性

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先读 `carla-agent schema blueprints.list`：

```bash
carla-agent blueprints list --profile profile.json --params '{"filter":"vehicle.*"}'
```

`filter` 为 wildcard，默认 `*`；输出仅按实际 result 提供，不承诺 CLI 返回全部 attribute 元数据。需要完整属性时只读原生 `world.get_blueprint_library().find(real_id)`，迭代 blueprint，记录每个 attribute 的 `id/type/is_modifiable/recommended_values` 与 `as_str()`；类型转换用对应 `as_bool/as_int/as_float/as_color`。

修改 blueprint 副本采用 `has_attribute(name)` 检查、`get_attribute(name).is_modifiable` 校验，再 `set_attribute(name,str(value))`。此操作只改待生成描述，不修改已存在 actor；spawn 才影响世界。推荐值不是所有数值的合法范围，专项规则继续校验。

空匹配报告真实 filter/基线能力；find 不存在、只读属性或格式不符保留失败，不猜相似 blueprint 自动替换。sensor 专项解释其属性，生命周期交 actors/rig。

## 交接与证据

[carla-actors](../carla-actors/SKILL.md)；[carla-sensor-rig](../carla-sensor-rig/SKILL.md)；[carla-vehicle-assets](../carla-vehicle-assets/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Blueprint.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
