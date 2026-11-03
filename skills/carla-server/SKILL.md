---
name: carla-server
description: 启动和停止用户指定的已有 CARLA Shipping 包，核实端口、进程身份、日志与 RPC ready；不编译打包，不接管借用实例。
metadata:
  category: engineering
  execution: workflow
  operations: ''
---

# carla-server

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：PACKAGE_ROOT、实际 `CarlaUnreal.sh`、RPC_PORT、地图/渲染参数、日志目录和实例所有权。先检查已有监听者、包 VERSION 与 launcher 内容；发现端口已有实例时只诊断或按用户指定改端口，不先杀进程。插件目前没有 server.start/server.stop 封装，此处用受限进程操作，不虚构 CLI。

已有包启动路径为 `./CarlaUnreal.sh -carla-rpc-port=<RPC_PORT> <verified-launch-args>`，在 PACKAGE_ROOT 运行，保存 launcher 与实际 child PID、进程启动时间、可执行路径、完整参数和本次日志。不要只记录后台 shell 的 `$!` 就认为它一定是 UE 进程；脚本可能派生 child。端口 flag 由 `CarlaSettings.cpp` 接受，其他参数先在当前源码/包核实。需要后台运行时在独立进程会话中启动并记录其身份，不对系统所有 CARLA 进程操作。

ready 必须用匹配 wheel 的 `carla.Client(host, port)`、`set_timeout(seconds)`、`get_server_version()` 和 `get_world()` 做有界探测，或交 `carla-connection`；启动超时报告进程/端口/RPC 各层，不无期限重启。输出为实例身份记录、日志、ready 结果、包与代码版本；连接成功不证明传感器有效。

停止前重新核对 PID 启动时间、路径、参数与本任务记录一致，再向本任务拥有的实际 UE 进程发 SIGTERM 并有界等待；wrapper 残留分别处理。不使用 `pkill`、按端口盲杀、默认 SIGKILL 或停止借用实例。失败/身份变更就停止自动终止，保留诊断。

路由：缺包 → `carla-build-shipping`（仍需显式授权）；Editor → `carla-editor-launch`；独占世界资源 → `carla-session`；cluster/ROS2 开关 → 对应条件 skill。

Source：`UE5_BUILD_README.md` 的 Run the package；`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Settings/CarlaSettings.cpp` 的 RPC port 解析；安全进程所有权为本插件 workflow，尚无专用封装。
