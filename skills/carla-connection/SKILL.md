---
name: carla-connection
description: 诊断 CARLA profile、指定 Python wheel、client/server 版本、timeout 与 ready；用于首次连接、连接拒绝、解释器或版本不匹配。进程启动停止交 carla-server。
metadata:
  category: runtime
  execution: cli
  operations: 'connection.doctor'
---

# 连接诊断

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先读 `carla-agent schema connection.doctor`，再执行：

```bash
carla-agent connection doctor --profile profile.json --params '{}'
```

输入为共享 profile，参数对象为空。区分 controller Python 可运行、worker 可导入 `carla`、目标 server 可访问、版本相符四层，按实际 result 字段报告；不得添加 schema 外的 ready flag。只读诊断无需 session。

原生补充诊断时可用 `client.get_client_version()`、`client.get_server_version()`、`client.is_carla_ready()`，各自保留返回和 timeout；`is_carla_ready` 不证明地图/传感器就绪。连接失败先核对 host/port、进程日志和 wheel ABI；不安装全局依赖、启动或杀死借用 server。修改 profile 后只重试失败层，不自动采集。首次教学按需读 [教学参考](../../references/carla-learning.md)。

## 交接与证据

[carla-server](../carla-server/SKILL.md)；[carla-session](../carla-session/SKILL.md)；[carla-world](../carla-world/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Client.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
