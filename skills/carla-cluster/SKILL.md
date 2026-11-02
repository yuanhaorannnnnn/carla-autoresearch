---
name: carla-cluster
description: 核查 CARLA Cluster 成员注册、heartbeat、类型化消息与 RPC 连通；只覆盖协议组件，不承诺完整多机或 multiGPU 调度。
metadata:
  category: engineering
  execution: conditional
  operations: ''
---

# carla-cluster

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：同版本 CarlaCluster 插件/二进制、primary/secondary 主机和端口、消息 UScriptStruct/MsgKey、已有实例所有权与协议试验授权。先确认没有 `-DisableCarlaCluster`。`UCarlaClusterSubSystem` 的 Config=CarlaClusterSystem 中 PrimaryPort 默认 39561、SecondaryPort 默认 39165；不要与 CARLA RPC/streaming 端口混同。

primary 无 `-carla-primary-host` 时以 primary 初始化；secondary 使用 `-carla-primary-host=<primary-ip>`。`FCarlaClusterProxy::Init(PrimaryPort,SecondaryPort)` 读取 `CarlaClusterHeartbeatDeltaTime`，诊断可用 `-DebugCarlaCluster`/`-DebugCarlaClusterHeartbeat`；启动参数交 server，缺插件或二进制不自动编译。确认 member 注册/ready、session identity、实际 heartbeat 往返数据，不能仅以 TCP 端口可连判协议成功。

原生 C++ 类型化链：`UCarlaClusterBPLibrary::RegisterMsgKeyAndType<TStruct>(MsgKey)` → `Bind<TStruct>(MsgKey, Callback)` 保存 FDelegateHandle → `MakeClusterMessage(Message,MsgKey,Struct)` → `SendDatas(TargetSession,Message)`；回调核对 Session/DataType/MsgKey，再 `UnBind(Handle)` 清本次绑定。payload 用 UScriptStruct::SerializeItem/FMemoryWriter，双方必须同类型布局；不是 JSON RPC。原生未暴露 Python 操作，不虚构 `carla.cluster.*`；缺现有 C++ harness 时只做配置和源码诊断，不用任意新脚本跨协议替代。

产物：实例/成员身份、端口、注册/heartbeat 日志、本次类型消息与回调证据、清理结果。只发送无业务副作用的已定义消息，不能用内置 TestCommand 执行未知 console 作为连通探针。超时停止有界消息试验、只解绑自有 handle/停止自有实例；不踢出其他 member。

协议成功不证明世界同步、actor 分片、渲染分配或完整 distributed scheduling。路由：进程 → `carla-server`；world/tick → `carla-world`/`carla-clock`；debug UDP → `carla-debug-port`。

Source：`Unreal/CarlaUnreal/Plugins/CarlaCluster/Source/CarlaCluster/Public/CarlaClusterBPLibrary.h`、`CarlaClusterSubSystem.h`；同模块 `Private/CarlaClusterProxy.cpp`、`CarlaClusterSubSystem.cpp`。
