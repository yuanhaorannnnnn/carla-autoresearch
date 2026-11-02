# Sensor 专项：执行与证据边界

适用于 25 个专项。先读 [共享规则](carla-agent-shared.md)，只读请求只执行 describe。此参考补充 native listener；不赋予额外操作权限。

## 最短操作路径

1. `carla-agent schema sensors.describe`，再执行 `carla-agent sensors describe --profile PROFILE --params '{"blueprint":"实际ID"}'`。当前describe提供value/modifiable/recommended_values，不能声称它返回type；需要类型时读取匹配native blueprint attribute.type或对应源码定义。推荐值不等于安全范围，源码定义不证明当前二进制具有相同能力。
2. CLI安装核对由 [carla-session](../skills/carla-session/SKILL.md) 与 [carla-sensor-rig](../skills/carla-sensor-rig/SKILL.md) 使用`sensors.attach`完成，请求含session_id/自有parent_id/blueprint/attributes与可选transform（xyz meters、pitch/yaw/roll degrees）。attach仅负责已授权安装，不顺接native listener。当前没有通用listener ownership守卫，禁止原生listener接管CLI-owned actor或借用CLI/research lease。
3. 当前`capture.run`的protocol/worker只支持RGB与标准RayCast，其session由capture自管。MEMS需要capability_profile=custom-mems才能CLI attach，当前仍不能capture.run。其他sensor的采集应采用独立原生任务；只读describe可先CLI完成，但不要为此open CLI session，也不要编造camera.capture/radar.listen命令。
4. 原生脚本由profile.client_python启动，读取相同host/port/timeout；先确认目标server没有active CLI/research lease或其他tick owner，并验证server version/map/episode与独占使用条件。没有排他证据时只做检查。脚本自身拥有整个连接→保存settings→spawn自有parent/sensor→listen→bounded tick→stop→destroy→restore生命周期；不要借用刚才CLI attach的sensor，已有CLI任务须先由其owner正常close。
5. 原生脚本按本次请求显式实现安装属性/外参，记录自己创建的actor ID、parent、role_name和episode；同类型sensor使用不同role_name。保存有界队列、frame/timestamp/transform、实际Python类名与原始bytes/结构化字段。回调只入队，重解码/写盘在主循环；脚本是唯一tick owner，设墙钟deadline、tick/frame预算和队列溢出记录，每批推进前核验episode与独占条件。多源采集应在同一个原生任务内，不混CLI lease。
6. finally先停止自有listener，再只销毁本脚本在相同episode创建的sensor/parent；只有原世界/所有权仍匹配时才恢复先前settings。世界变化或无法确认资源身份时停止并报告未恢复部分，不能按猜测ID清理。不调用session.close冒充native资源恢复；采集失败和恢复失败分别记录。

## 采样与输出

`SensorData.frame` 是整数 frame ID，`timestamp` 是 double 模拟秒，`transform` 是采样时安装姿态；不要用文件写入时间代替。已暴露的 sensor_tick 为 Float 秒，0 通常每模拟 tick 更新，最终以实现与回调为准。collision/lane/RSS 的 generic definition 不自动获得 sensor_tick，不能给所有 sensor 强加相同属性。

连续 measurement 可以包含 0 个 detection；碰撞、越线是有事件才回调；DVS 只在非空 events 时发送。记录“完成观察窗但无事件”需有 tick/窗口证据；单纯回调超时既不能当成功，也不能直接当丢帧。多频率/事件流对齐、warmup、manifest 交 [carla-capture](../skills/carla-capture/SKILL.md)，时间配置交 [carla-clock](../skills/carla-clock/SKILL.md)。

## 源码范围

静态基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`。以下路径相对用户提供的CARLA源码根目录，不依赖插件作者本机路径；下列缩写只用于本组参考：

- `A` = `Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Actor/ActorBlueprintFunctionLibrary.cpp`
- `S/` = `Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Sensor/`
- `D/` = `LibCarla/source/carla/sensor/data/`
- `Z/` = `LibCarla/source/carla/sensor/s11n/`
- `P` = `PythonAPI/carla/src/SensorData.cpp`
- 注册表 = `LibCarla/source/carla/sensor/SensorRegistry.h`；挂载接口 = `PythonAPI/carla/src/Sensor.cpp`。

插件执行边界来自 `src/carla_agent/protocol.py` 的 OPERATIONS/schema 和 `src/carla_agent/worker.py` 的 attach/capture。静态结构检查不代表运行、图像正确、硬件等价或实时性能已验证。
