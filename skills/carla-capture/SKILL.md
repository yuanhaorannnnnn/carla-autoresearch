---
name: carla-capture
description: 执行有界 CARLA 原始数据采集，管理 warmup、frame/timestamp、超时和清理；用于抓样本或多传感器同步采集。CLI 当前支持 RGB/RayCast 单传感器，其余采集按原生流程；数据解释与研究判断分别交专项。
metadata:
  category: data
  execution: cli
  operations: capture.run
---

# CARLA 有界采集

先读 [共享规则](../../references/carla-agent-shared.md)，再读 `carla-agent schema capture.run`。该操作组合自有车辆、传感器与 session；不要另开手工 session。

调用前用 doctor/world.inspect 及所需 blueprint/describe 确认真实连接、当前地图和传感器能力。它们是只读前置，不能代替采集变更授权。Recipe 的 `map` 必须匹配当前地图；不自动加载地图。

请求参数为 `{"recipe": {...}}`。Recipe 必填 `map`、`sensor_blueprint`；支持 `sensor_attributes`、可选 `vehicle_blueprint`、`spawn_index`（默认 0）、`frames`（默认 10）、`warmup_frames`（默认 2）、`fixed_delta_seconds`（默认 0.05）。具体类型、帧上限和其他可用字段读 schema，不发明无限循环或未实现参数。传感器与车辆 ID 从当前 blueprint 查询取得。

```bash
carla-agent capture run --profile profile.json --request capture-request.json
```

`capture-request.json` 应写入已核实的地图和目标传感器，固定短预算；不把示例 Town 名当成现场地图。当前 `capture.run` 只接受 RGB/RayCast LiDAR。MEMS 的 custom profile 只允许对应 attach，不会让 capture 自动支持 MEMS；其他 sensor 也不能强塞进 recipe。

## 其他 sensor 与多源采集

需要 CLI 未支持的流或多传感器时，按共享规则准备独立原生采集脚本，使用 [sensor-rig](../carla-sensor-rig/SKILL.md) 的安装配置和各专项的数据契约，不复用活跃 CLI session。sprint42 参考 `PythonAPI/examples/sensor_synchronization.py:57–85` 与 `PythonAPI/carla/src/Sensor.cpp:45–77`。

唯一 tick owner 使用有界同步循环；每个 sensor 的 callback 写入有容量上限的独立队列，消费端按 `data.frame`/timestamp 关联。低频 sensor 按 `sensor_tick` 与世界步长安排应到帧；事件流以采集时间窗口收集，空事件窗口单独记录。无回调本身不能证明“有效空事件”，还需核对监听、发送条件及专项实现限制。不同来源不能简单 `zip` 后假定对齐。超时输出期待/实收帧、sensor identity、队列丢弃计数；不得无限 wait。

RGB 的 `send_data_stream` 需先查实时属性，存在时显式开启；仅 UE 显示不证明 Python 收流。回调内只做轻量入队，写盘/解码在消费者进行。结束先 stop 监听，再处理残留队列和自有 sensor/parent 清理；只有 server/episode 身份一致才能恢复世界设置。脚本中断也走同一清理路径。

运行结束检查实际原始输出、manifest、frame/timestamp/receive timing，以及退出和清理状态。说明请求帧与收到的匹配帧、warmup、缺帧/超时；不能仅凭文件存在声称 frame 完整。失败保留原始输出和原因；没有证据时不能声称跨 episode 清理成功。用户未授权修改实验条件时，不自动换 blueprint、地图或步长反复尝试。

入门演示按需读 [教学参考](../../references/carla-learning.md)，展示一段真实输出并解释它支持的判断。

采集文件组织与标注交 [dataset](../carla-dataset/SKILL.md)；重复试验交 [benchmark](../carla-benchmark/SKILL.md)，读数比较交 [compare](../carla-compare/SKILL.md)。
