# 运行时原生 API 使用约定

仅在所需功能没有现有 CLI operation 时读此页；先读 [共享规则](carla-agent-shared.md)。源码路径均相对 sprint42 CARLA 根，基线 `2075f526dec86362fe058a6fff939e6832876759`。下面是按绑定核对的操作说明，未执行 server、依赖探测或实机演示。

## 连接与变量

使用 profile 指定的 `client_python` 和匹配 wheel。Python 示例中的 `host`、`port`、`timeout_seconds` 来自真实 profile；不是新命令或硬编码的另一台 server。

```python
import carla
client = carla.Client(host, port)
client.set_timeout(timeout_seconds)
client_version = client.get_client_version()
server_version = client.get_server_version()
if client_version != server_version:
    raise RuntimeError(f"CARLA version mismatch: {client_version} != {server_version}")
world = client.get_world()
episode_id = world.id
```

读取时记录 client/server 版本、`world.id`、map name 和观测 frame；某个绑定不存在即停止该分支，不能据源码存在宣称已安装 wheel 支持。短片段是操作核心，不能直接当成包含初始化、限时、清理的完整 runner。

## 原生变更与资源

原生变更只能在明确授权、独占条件核实且没有活动 CLI lease 的独立原生任务中执行。它必须自己完成创建→使用→有界等待→逆序清理→按同一 episode 恢复的完整生命周期，保存自有 actor ID、回调 ID、settings 和本任务实际改变的全局状态。不能连接到 CLI session 后接管其 actor，不能修改 lease 文件或把原生生成的 ID 注入 CLI ownership。需要混合能力时，先完成并关闭原 CLI session，再以独立原生任务从头创建资源；已有 operation 继续走 CLI。

片段中的 `actor`、`vehicle`、`walker`、`controller`、`sensor` 指本原生任务创建并登记的对象。发现现有 actor、用户给出 ID、`role_name=hero` 均不构成 ownership。只读查询可观察外部 actor；控制、销毁、重绑必须有对应所有权与任务授权。

原生 actor 创建保存返回对象；`try_spawn_actor` 的 `None` 不登记成功，异常或 timeout 后先核对身份，禁止盲重试。清理 sensor 先 stop，再销毁子 actor、controller、父 actor。每次变更前核对 episode；换图后丢弃旧 handle，不在新 episode 恢复旧 settings。不可读取的原始状态或没有公开恢复入口的变更，事前说明该限制并使用本任务可销毁重建的资源。

## 时钟与观察

全任务只有一个 tick owner。同步模式不能用 `wait_for_tick()` 替代推进者；异步观察不调用 `tick()`。有界循环使用帧上限和 wall timeout；回调只入队，不在回调内 tick。停止后移除 `on_tick` 的返回 ID。`fixed_delta_seconds <= max_substep_delta_time * max_substeps`；与 Traffic Manager 同步开关协调。世界配置、天气、信号、灯光等全局变更不能靠 actor 清理恢复，需按各领域记录恢复能力与实际结果。

## 输出

每项结果保留输入、版本、episode/frame、对象 ID、实际返回值或异常、清理和恢复结果。异步 setter 通常没有业务成功回执，应在后续 snapshot/readback 或 receiver 数据验证；不能把无异常当作效果已验证。原生结果不伪装成 CLI JSON 信封。几何查询、录制文件、内部发布调用各只证明自身层次，不证明 sensor、接收端或完整确定性。
