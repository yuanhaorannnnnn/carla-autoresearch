---
name: carla-debug
description: 使用 CARLA DebugHelper 标绘、调试模式、UE console 与主/次服 console 诊断；不代替专用 debug-port 协议，不把任意 console 文本当作已验证操作。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 调试标绘与控制台

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

可先只读查询 world FPS/sim time 与 snapshot，避免为诊断改场景。标绘是世界副作用，授权后用有限寿命、非永久线：

```python
world.debug.draw_point(location, size=0.1,
    color=carla.Color(255,0,0), life_time=2.0, persistent_lines=False)
```

draw_line(begin,end,thickness,color,life_time,persistent_lines)、draw_arrow、draw_box(box,rotation,...)、draw_string 等按绑定签名选；坐标与 box rotation 不混用。寿命 -1/持久标绘可能留存，不默认全场绘制大批点。

`world.enable_debug_mode()`/`disable_debug_mode()` 改调试模式；`exec_ue_cmdline(cmdline)` 和 `exec_console_commands(secondary_id,cmds)` 执行 server 端命令，是额外变更能力。先核对精确命令的作用/参数与范围，未知 console command 不试探，不将用户数据拼接为命令，不用于绕过 session/actor ownership 或进程管理。

保留命令、目标 secondary、真实日志和可见效果；无输出不判成功。结束关本任务 debug 模式、等有限标绘过期，不能声称已撤回无公开取消接口的永久绘图。需要协议探测/端口调试交 debug-port。

## 交接与证据

[carla-clock](../carla-clock/SKILL.md)；[carla-scene-query](../carla-scene-query/SKILL.md)；[carla-debug-port](../carla-debug-port/SKILL.md)；[carla-display](../carla-display/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/World.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
