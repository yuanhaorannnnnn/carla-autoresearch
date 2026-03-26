# Mistake Patterns

## Purpose

Record durable, reusable guardrails here. Keep raw incident details elsewhere if
needed, and only promote mistakes that are worth reusing as long-term rules.

### CARLA 真实联调时，服务端和客户端都优先在真正的新桌面终端里运行；客户端必须先激活指定 conda 环境（当前为 py38）再执行 benchmark/脚本。

- 错误做法：直接在 agent 的当前 shell/PTY 里启动 CARLA 服务端或客户端，或在未激活目标 conda 环境时运行 Python client。
- 正确做法：CARLA 真实联调时，服务端和客户端都优先在真正的新桌面终端里运行；客户端必须先激活指定 conda 环境（当前为 py38）再执行 benchmark/脚本。
- 触发场景：当任务涉及 CARLA Shipping 包启动、PythonAPI 连通性验证、LiDAR benchmark 或任何依赖桌面会话环境变量的联调时。

### 验证正式工作流时，不要用临时内联脚本复制正式入口逻辑。

- 错误做法：为了图快，写临时内联 Python 脚本去复刻 `benchmark_client.py` 或其他正式入口逻辑，导致参数和流程与仓库真实实现不一致。
- 正确做法：验证正式工作流时，优先直接运行仓库里的正式入口；如果确实需要额外观测字段，先把观测能力加到正式入口里，再执行正式代码路径。
- 触发场景：当任务目标是验证 benchmark、实验控制器、CLI 入口或任何“当前仓库真实行为”时。

### 手动/验证流程中如果当前已有活跃 CarlaServer，优先复用，不要重复启动第二个实例。

- 错误做法：在 `2000` 端口已有 CarlaServer 运行时，再起一个新的 Shipping 服务端，导致 `Address already in use`。
- 正确做法：手动 smoke test、点数验证或 benchmark 验证前，先检查是否已有活跃 CarlaServer；如果已有，就直接复用该实例。只有在明确需要新实例时才重新启动。
- 触发场景：当任务涉及手动联调、点数验证、benchmark 复测或任何可能重复占用 CARLA RPC 端口的流程时。
