---
name: carla-weather
description: 读取和设置 CARLA 雨雾风太阳扬尘、降雪积雪和 environment_lighting_gain、天气预设；用于世界环境配置，不据天气参数断言 sensor 物理响应或标定准确。
metadata:
  category: runtime
  execution: native-api
  operations: 'weather.inspect'
---

# 天气与环境增益

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先读 `carla-agent schema weather.inspect`，再 `carla-agent weather inspect --profile profile.json --params '{}'`；result.weather 只包含实际存在的有限数值字段，缺字段不能默认为 0。设置和启用观测使用下列原生接口。

先 `before=world.get_weather()`、`world.is_weather_enabled()` 记录真实配置/启用观测。WeatherParameters 绑定字段：cloudiness、precipitation、precipitation_deposits、wind_intensity、sun_azimuth_angle/sun_altitude_angle、fog_density/fog_distance/fog_falloff、wetness、scattering_intensity/mie_scattering_scale/rayleigh_scattering_scale、dust_storm、snow_precipitation/snow_accumulation/environment_lighting_gain。

独立授权的原生任务修改副本后 `world.set_weather(weather)`；普通百分比与角度、距离、增益不混用。snow_* 和 environment_lighting_gain 没有构造器位置参数，使用属性赋值。预设如 `carla.WeatherParameters.ClearNoon`、`HardRainNoon`、`DustStorm`，用实际绑定存在的名称；应用预设会替换一组条件，不只改雨量。

set_weather 后读回并观察对应帧；天气系统禁用、渲染未更新、无渲染模式或定制 shader 缺失分别诊断，不把相等参数当图像已变化。此 Python 绑定只有 is_weather_enabled，没有通用 enable_weather/disable_weather；不能编造启停操作，缺入口转工程/实际支持接口。

结束同 episode 恢复 before 并读回。降雨/雪参数值不等于真实降水率或传感器误差，科学比较走对应 sensor 与研究 workflow。

## 交接与证据

[carla-world](../carla-world/SKILL.md)；[carla-scene-lights](../carla-scene-lights/SKILL.md)；[carla-capture](../carla-capture/SKILL.md)；[carla-research-plan](../carla-research-plan/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Weather.cpp`、`PythonAPI/carla/src/World.cpp`、`LibCarla/source/carla/rpc/WeatherParameters.h`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
