# Mistake Rules
## Rule
❌ 错误做法：直接在 agent 的当前 shell/PTY 里启动 CARLA 服务端或客户端，或在未激活目标 conda 环境时运行 Python client。
✅ 正确做法：CARLA 真实联调时，服务端和客户端都优先在真正的新桌面终端里运行；客户端必须先激活指定 conda 环境（当前为 py38）再执行 benchmark/脚本。
触发场景：当任务涉及 CARLA Shipping 包启动、PythonAPI 连通性验证、LiDAR benchmark 或任何依赖桌面会话环境变量的联调时。

## Rule
❌ 错误做法：在 2000 端口已有活跃 CarlaServer 运行时，再起一个新的 Shipping 服务端，导致 Address already in use。
✅ 正确做法：手动 smoke test、点数验证或 benchmark 验证前，先检查是否已有活跃 CarlaServer；如果已有，就直接复用该实例。只有在明确需要新实例时才重新启动。
触发场景：当任务涉及手动联调、点数验证、benchmark 复测或任何可能重复占用 CARLA RPC 端口的流程时。

## Rule
❌ 错误做法：为了图快，写临时内联 Python 脚本去复刻 benchmark_client.py 或其他正式入口逻辑，导致参数和流程与仓库真实实现不一致。
✅ 正确做法：验证正式工作流时，优先直接运行仓库里的正式入口；如果确实需要额外观测字段，先把观测能力加到正式入口里，再执行正式代码路径。
触发场景：当任务目标是验证 benchmark、实验控制器、CLI 入口或任何当前仓库真实行为时。

## Rule
❌ 错误做法：当改动范围扩到 LibCarla 或 PythonAPI 侧后，package 完成后仍直接复用旧的 carla Python 包启动客户端，导致客户端仍在用旧 wheel。
✅ 正确做法：如果改动范围扩到 LibCarla 或 Python 端，每次 package 之后启动客户端前都先在 py38 环境里 force-reinstall 新生成的 wheel：pip install /media/yhr/2T/CarlaUE5/Build/PythonAPI/dist/carla-0.10.0-cp38-cp38-linux_x86_64.whl --force-reinstall，然后再启动客户端脚本。
触发场景：当优化或修复涉及 /media/yhr/2T/CarlaUE5/LibCarla、PythonAPI、carla Python 绑定或任何会改变 Python wheel 内容的代码时。
