---
name: carla-editor-launch
description: 启动已有 CARLA Unreal Editor、打开指定项目或地图；用于 launch-only，不编译过期目标，缺二进制时交 build-editor。
metadata:
  category: engineering
  execution: workflow
  operations: ''
---

# carla-editor-launch

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：正式主 checkout、UE fork 的现有 UnrealEditor、匹配 Content、项目与可选地图、启动授权。核实 `Unreal/CarlaUnreal/CarlaUnreal.uproject`、Editor 二进制及 `Content/Carla/Blueprints`；后者只是一项基本检查，另核对用户请求地图。

已有 Build 配置时：

```bash
cmake --build "$BUILD_DIR" --target launch-only
```

该 target 只依赖 `check-unreal-content`，不会 rebuild 过期目标。明确指定地图且不需 CMake launch 参数时，用已有 Editor：`"$UE_ROOT/Engine/Binaries/Linux/UnrealEditor" "$CARLA_ROOT/Unreal/CarlaUnreal/CarlaUnreal.uproject" <verified-map-asset-path>`，只添加核实过的 RHI/display 参数。不要用 `launch` 或 `lunch.sh` 实现只启动：前者依赖编译，后者还删 cache。

产物：启动进程身份、日志、实际打开的 project/map；进程存在不证明 Editor ready、PIE 正在运行或 CARLA RPC 可连接。二进制/模块缺失时给出缺失路径并路由构建；不自动编译。关闭只处理本任务创建的 Editor，先处理其未保存资产，不结束借用进程。

路由：Content → `carla-content-sync`；显式编译 → `carla-build-editor`；已有 Shipping 包 → `carla-server`；运行时连接 → `carla-connection`。

Source：`Unreal/CMakeLists.txt` 的 `CARLA_LAUNCH_TARGET_OPTIONS`、`launch-only`、`check-unreal-content`。
