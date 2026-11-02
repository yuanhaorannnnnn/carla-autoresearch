---
name: carla-environment-setup
description: 定位或准备 CARLA UE5 的 OS、编译工具、UE fork、Python 与依赖；用于安装前检查或明确要求的环境安装，不用于直接构建和启动。
metadata:
  category: engineering
  execution: workflow
  operations: ''
---

# carla-environment-setup

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：目标 OS、CARLA checkout、已有 UE fork、Python 路径及允许的安装范围。先只读查看 `UE5_BUILD_README.md`、`CMake/Toolchain.cmake`、`Util/SetupUtils/InstallPrerequisites.sh`，核对 `cmake --version`、`ninja --version`、编译器版本及目标 Python 的版本；读取 `CARLA_UNREAL_ENGINE_PATH` 的路径值，不打印 Git token 或整个环境。

本基线需要 CARLA fork 的 UE5.3；通用 Epic UE 安装不自动满足要求。安装路线为 `CarlaSetup.sh --interactive --python-root <python-bin-dir>`，但只有用户授权了脚本全部实际副作用才可运行。`--skip-prerequisites` 只跳过 prerequisites，仍会检查/下载 Content、可能下载并编译 UE、configure/build CARLA 和安装 Python API；`--launch` 还会启动 Editor。脚本中的 `--python-root` 在 prerequisites 阶段被拼成 `<dir>/python3`，不要传 Python 文件代替目录。需要仅安装前置时，单独审查并授权 `Util/SetupUtils/InstallPrerequisites.sh --python-path=<interpreter>`，不顺便跑 Setup。

产物：核实过的工具/路径清单及缺项；若实际安装，列出变更的系统包、UE/Content 目录、Python 环境和日志。缺 GitHub/Epic 权限由用户现有认证解决，不请求输出凭据。失败停在具体阶段，不重跑会覆盖现有环境的全套脚本。

路由：Content 配对 → `carla-content-sync`；CMake → `carla-build-configure`；wheel → `carla-build-python-api`；Editor/Shipping 各自显式授权。

Source：`CarlaSetup.sh`，`Util/SetupUtils/InstallPrerequisites.sh`，`UE5_BUILD_README.md`，`CMake/Toolchain.cmake`。
