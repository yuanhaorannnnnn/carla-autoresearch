---
name: carla-sensor-extension
description: 开发新 CARLA sensor 的 UE definition、数据 serializer/registry 与 Python binding 全链路；使用现有 sensor 走对应专项。
metadata:
  category: engineering
  execution: workflow
  operations: ''
---

# carla-sensor-extension

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：独立 sensor ID、属性/单位/合法范围、parent 与时间语义、连续或事件输出 schema、依赖/构建开关。先找最接近的数据契约，例如 GNSS、event 或 image，而不是复制 RGB 解码器套任意数据。

按现有源码链落实：

1. 在 `Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Sensor/` 增加 UE ASensor 子类、`GetSensorDefinition()`、`Set(FActorDescription)` 与具体 tick/event 生成；定义属性使用 ActorBlueprintFunctionLibrary 的实际 helper，明确本类 ID。
2. 在 `LibCarla/source/carla/sensor/data/` 定义 payload，在 `s11n/` 实现 serializer/deserializer，说明 header、stride、endian、单位、frame/timestamp 与空数据意义。
3. 在 `SensorRegistry.h` 声明、注册 `<Sensor*, Serializer>` 并加入 WITH_SENSOR_INCLUDES 的 include。factory 使用注册表自动调用 GetSensorDefinition；含 `not_spawnable` 的内部类型会被跳过，不应另造可生成 Blueprint。注册顺序决定 wire type，client/server 必须一致，不能只替换一端。
4. 在 `PythonAPI/carla/src/SensorData.cpp` 导出 data type/容器/访问器；有控制 RPC 时再补相应 server/client/binding，不因可序列化就省略 Python 暴露。
5. 为新专项记录实际输出和属性 schema；挂载/owned actor 清理由 rig/session 复用，不复制通用操作。

产物：上述各层 diff 和完整 source→payload→binding 对照；静态检查只证明接口路径，构建、spawn、回调、解码验证另依明确授权。NoopSerializer 仅适用于确实无 server 数据/客户端 sensor，不能用来掩盖未实现输出。新增 code 不自动授权 build-editor。失败保留现有 registry ABI，完整撤回本类型接线而非删他人项。

路由：新 actor 通用 factory → `carla-actor-extension`；既有传感器 → 对应 25 专项；采集 → `carla-capture`。

Source：`LibCarla/source/carla/sensor/SensorRegistry.h`；`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Sensor/SensorFactory.cpp`、`GnssSensor.cpp`；`PythonAPI/carla/src/SensorData.cpp`。
