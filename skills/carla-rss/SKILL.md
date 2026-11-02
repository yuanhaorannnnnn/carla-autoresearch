---
name: carla-rss
description: 配置 CARLA 条件编译 RSS 感知与控制约束链；用于 RssResponse、路由目标、ego/other dynamics、actor constellation 和 RssRestrictor，要求匹配 RSS 构建与依赖。
metadata:
  category: sensors
  execution: conditional
  operations: 'sensors.describe,sensors.attach'
  blueprint: sensor.other.rss
---

# RSS response and restriction

精确 blueprint：`sensor.other.rss`。先读 [执行、所有权与采集边界](../../references/sensors-native-acquisition.md)。`execution` 标示主要路径，`operations` 只列现有CLI入口；不表示此sensor已获通用采集支持。

只读入口：`carla-agent sensors describe --profile PROFILE --params '{"blueprint":"sensor.other.rss"}'`，先查`sensors.describe` schema。CLI attach仅作已授权安装核对；需要native采集时采用参考中的独立原生任务，不接管CLI-owned actor。

## 能力与配置

先核对当前wheel是否导出RssSensor/RssRestrictor/RssResponse和server blueprint；PythonAPI.cpp仅在LIBCARLA_RSS_ENABLED下export_ad_rss，registry NoopSerializer不证明依赖可用。generic blueprint主要role_name，不用sensor_tick属性调RSS或把第三方dynamics对象塞进attributes。

匹配原生API的RssSensor可设置ego_vehicle_dynamics/other_vehicle_dynamics/pedestrian_dynamics、road_boundaries_mode，读取routing_targets；append_routing_target/reset_routing_targets/drop_route与register_actor_constellation_callback改变RSS计算条件。先保存原配置及路由，使用实际第三方typed objects，数值单位以对应ad-rss物理类型（加速度m/s²、时间s等）为准，不猜字段结构。

## 输出与最短控制链

回调RssResponse含response_valid（Bool）、proper_response、rss_state_snapshot、situation_snapshot、world_model、ego_dynamics_on_route；后五项是绑定的RSS结构，非同质raw点数组。SensorData给frame/timestamp/transform，RSS执行在client侧，需保持监听进程与匹配的episode。

能力检查 → 独立原生任务持有自有vehicle/RSS sensor → 设路由与dynamics → 有界listen并保存response_valid与typed response → 需要约束控制时先确认有效且时效匹配，再调用`RssRestrictor.restrict_vehicle_control(control, proper_response, ego_dynamics_on_route, vehicle_physics)`取得新control，应用控制由vehicle-control负责且必须在授权范围。此接口参数取AdRss.cpp绑定，不能用不存在的CLI rss.restrict。

无效/过期/无响应不可当“安全通过”，保留状态并停止依赖该response的自动控制；缺构建能力只报告缺口，不自动构建或退化成普通collision sensor。结束stop/清理自有资源并恢复原任务设置。当前capture.run不支持RSS；RSS计算结果也不等于现实安全认证。

## 交接与源码

安装外参/拆卸交 [carla-sensor-rig](../carla-sensor-rig/SKILL.md)，有界采样/对齐交 [carla-capture](../carla-capture/SKILL.md)，时间与唯一tick owner交 [carla-clock](../carla-clock/SKILL.md)。相邻专项：[$carla-vehicle-control](../carla-vehicle-control/SKILL.md)。

静态依据（缩写和基线见[源码范围](../../references/sensors-native-acquisition.md#源码范围)）：S/RssSensor.cpp:15；PythonAPI/carla/src/PythonAPI.cpp条件export；PythonAPI/carla/src/AdRss.cpp:179–209；LibCarla/source/carla/client/RssSensor.cpp；LibCarla/source/carla/rss/RssRestrictor.cpp；SensorRegistry.h NoopSerializer。 本技能未把静态注册等同当前二进制、运行或物理模型验证。
