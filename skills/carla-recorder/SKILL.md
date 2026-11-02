---
name: carla-recorder
description: 使用 CARLA recorder 文件录制、查询碰撞/阻塞并按时间回放，设置 follow/sensor replay/倍速/ignore/keep_actors；原始 sensor 文件采集仍走 capture。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 录制与回放

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

查询已有文件可只读：`client.show_recorder_file_info(name,show_all)`、`show_recorder_collisions(name,type1,type2)`、`show_recorder_actors_blocked(name,min_time,min_distance)` 返回文本；type 字符代码先核对实现，文件名按 server recorder 路径解释。

录制是 server 全局状态，必须独占任务且确认没有其他 recorder：`client.start_recorder(name,additional_data=False)`，保存返回路径/状态，限定时长/frame 后 `stop_recorder()`。不因 start 无异常就认定文件完整，stop 后查询并保留文件证据。

`client.replay_file(name,time_start,duration,follow_id,replay_sensors=False)` 输入秒与目标 actor ID；会改变世界/actor，旧 lease、控制和 sensor 先结束。`set_replayer_time_factor(factor)`、ignore_hero/ignore_spectator(bool) 按任务配置；`stop_replayer(keep_actors)` 明确残留策略。keep_actors=True 不等于原场景恢复，False 也不授权删外部 actor。

不存在/不兼容文件、空时窗、actor ID 不匹配和 replay sensor 缺输出分别报告。Recorder 不保存所有原始 sensor 流，也不保证物理/渲染完全确定；文件查询成功不能代替实际回放演示。

## 交接与证据

[carla-capture](../carla-capture/SKILL.md)；[carla-world](../carla-world/SKILL.md)；[carla-clock](../carla-clock/SKILL.md)；[carla-ground-truth](../carla-ground-truth/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Client.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
