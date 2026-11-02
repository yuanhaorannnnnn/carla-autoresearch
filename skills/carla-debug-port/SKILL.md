---
name: carla-debug-port
description: 核查或使用 CARLA DebugPort UDP 的 ConnectTest/List/Data 协议、port/magic 与 console 回应；查询与执行分别授权，不代替普通 DebugHelper。
metadata:
  category: engineering
  execution: conditional
  operations: ''
---

# carla-debug-port

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：已启用 CarlaDebugPort 的专用实例、target IP/receive port/magic、client reply port、明确只读查询或精确 command、匹配协议客户端。默认不假设已开放。服务端通过配置 bSystemEnableFromConfig 或启动 `-OpenDebugPort=<port>:<magic>` 创建 subsystem；改变启动配置属于实例变更，交 server，不能为查询自动重启用户实例。

以 ParsePkgHeader 的实现为准：头部依次读取 5 个 int32：`magic, resPort, pkgType, pkgID, pkgSlice`；`sliceNum=pkgSlice/10000`、`totalSliceNum=pkgSlice%10000`。源码上方注释的字段顺序/optional 与实际 parser 不一致，不能据注释发短包。原生 TryRead 使用其自身字节/字符串实现，匹配 UE 目标布局；不直接套网络大端 JSON/UTF8。ConnectTest=1、List=2、Data=3。

先用 ConnectTest 验证协议。List payload 为 int32 CmdBufSize + 对应 UE 字符数据的 filter；Data 为同结构 command，`CDP.ListCmd <filter> <start> <count>` 为分页查询路径。Data 的其他内容会依次走 GEngine/World Exec 或 Player ConsoleCommand，具有真实状态影响；只在用户授权了具体命令及对象范围后执行，不因已授权连通查询就发送任意 command。它不是 server 强制白名单机制；限制由本任务客户端执行。

response 使用 magic=356849、原 pkgID、result、outputs 数量，再按 byte length 读 UE 字符串。记录端口/包ID、原始响应、结果枚举、截断/分页情况。存在回应不证明命令效果，写操作要从业务状态回读；未知结果不重发可能有副作用的 Data。缺现成匹配客户端时交付字段契约和缺口，不发猜测报文；不能把 UDP send 成功当完成。

产物：connect/list 证据或明确命令执行与状态回读、失败/超时层。只关闭自建 socket，不改远端 security/config 或停止借用实例。路由：普通标绘/console → `carla-debug`；Cluster RPC → `carla-cluster`；进程启动 → `carla-server`。

Source：`Unreal/CarlaUnreal/Plugins/CarlaDebugPort/Source/CarlaDebugPort/Public/CarlaDebugPortSystem.h`、`CarlaDebugPortBPLibrary.h`；同模块 `Private/CarlaDebugPortSystem.cpp` 的 ParseCmdList/ParsePkgHeader/HandleMessage/OnReceiveDatas。
