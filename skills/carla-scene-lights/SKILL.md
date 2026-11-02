---
name: carla-scene-lights
description: 使用 CARLA LightManager 的灯组、颜色、强度、active 状态和批量灯态，管理日夜循环；车辆灯与交通灯分别由 accessories/signals 负责。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 场景照明

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

只读 `lm=world.get_lightmanager()`、`lights=lm.get_all_lights(carla.LightGroup.Street)`，保存各灯 id/location/intensity/color/light_group/is_on/light_state。灯组 None 表示查询范围按实际 API 语义，不等于关闭灯。

授权独占的原生任务保存指定灯状态，再用 `lm.turn_on(lights)`/turn_off、`set_color(lights,Color)`、`set_intensity(lights,float)`、`set_active(lights,list[bool])`；复数 `set_colors/set_intensities/set_light_states` 的数组与 lights 按索引等长对应。`get_light_state(lights)` 回读列表；单灯也可 set_color/set_intensity/set_light_state/turn_on/off。

`set_day_night_cycle(active)` 是全局行为；无对应 getter 不擅自声称恢复原模式。若日夜系统持续覆盖手动灯态，明确控制源和恢复限制，而非每帧反复覆盖。没有灯可能是地图资产能力或尚未同步，不自动改车辆灯/交通灯来替代。

需要视觉结果时确认后续 frame/图像；API intensity 不直接等价像素亮度，曝光和天气会影响观察。结束恢复已保存灯态并按同 episode 读回，日夜模式恢复独立报告。

## 交接与证据

[carla-weather](../carla-weather/SKILL.md)；[carla-vehicle-accessories](../carla-vehicle-accessories/SKILL.md)；[carla-traffic-signals](../carla-traffic-signals/SKILL.md)；[carla-capture](../carla-capture/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/LightManager.cpp`、`PythonAPI/carla/src/World.cpp`、`LibCarla/source/carla/client/LightManager.h`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
