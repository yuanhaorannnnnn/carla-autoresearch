---
name: carla-ros2-native
description: 在已有支持 ROS2 的 CARLA 二进制上配置 native sensor stack、publisher 与 RViz；顶层 Ros2Native 接线被注释时报告条件缺失，不改走外部 ROS bridge。
metadata:
  category: engineering
  execution: conditional
  operations: ''
---

# carla-ros2-native

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：明确已支持 native ROS2 的 server/wheel、stack JSON、host/port、ROS2/RViz 环境、专用实例与 spawn/tick 授权。先核对构建证据：顶层 `CMakeLists.txt` 的 `if(ENABLE_ROS2) add_subdirectory(Ros2Native)` 整段注释；LibCarla server ROS2 接线也有注释。`ENABLE_ROS2=ON` 或 README 启动示例不证明当前基线可用，不能自动构建/安装补齐。

条件齐备才使用实际例程：server 端由 `carla-server` 启动已有包 `./CarlaUnreal.sh --ros2`；在 `PythonAPI/examples/ros2` 用匹配解释器运行 `ros2_native.py --host <host> --port <port> --file <stack.json>`。stack schema 为车辆 `{type,id,sensors:[{type,id,spawn_point:{x,y,z,roll,pitch,yaw},attributes:{...}}]}`；例程给 blueprint 设置 `ros_name`，挂载 sensors 后 `enable_for_ros()`。确认指定 vehicle/sensor IDs 在实际 library 存在，不能照抄示例后假定定制车辆可用。

例程会生成 actors、设置同步/推进世界等，需要遵守 shared 的专用实例、lease、settings/owned actor finally 清理边界，先审查当前脚本的完整恢复行为，不能直接在借用/CLI session 中运行。RViz 示例 `./run_rviz.sh` 依赖 Docker，先检查其镜像/挂载/网络操作与现有本地依赖；仅有 RViz UI 不证明收到数据。

产物：实际构建支持证据、stack、owned actors、ROS topic/type/frame 与收到消息的 timestamp/数据、RViz 展示及恢复结果。缺 Ros2Native target、共享库或 enable_for_ros 行为时停在对应缺口；给出明确需修复的 CMake/构建链，不把 external ROS bridge 当静默替代。关闭只清理本次 actors/container/自有 server。

路由：配置/源码接线 → `carla-build-configure`/`carla-actor-extension`（另行授权）；sensor 属性 → 对应专项；外部 ROS bridge 仅在 catalog 预留，未实现；actor ownership → `carla-session`。

Source：`PythonAPI/examples/ros2/README.md`、`ros2_native.py`、`stack.json`、`run_rviz.sh`；`CMakeLists.txt`；`Ros2Native/CMakeLists.txt`；`LibCarla/CMakeLists.txt`。
