---
name: carla-build-configure
description: 生成或诊断 CARLA 的 CMake 配置、toolchain、Python 和 feature flags；仅配置，不自动编译、安装或启动。
metadata:
  category: engineering
  execution: workflow
  operations: ''
---

# carla-build-configure

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：CARLA_ROOT、空或已有 BUILD_DIR、CARLA UE fork、目标 Python、client/server/Unreal 需求和明确 feature flags。先读取已有 `CMakeCache.txt` 的相关键，保留旧 cache，不删缓存去掩盖编译器或路径冲突。配置本身可下载依赖、生成工程和复制文件，需要相应授权。

在 CARLA_ROOT 执行所需配置，参数值必须来自本任务：

```bash
cmake -G Ninja -S . -B "$BUILD_DIR" --toolchain="$CARLA_ROOT/CMake/Toolchain.cmake" -DCMAKE_BUILD_TYPE=Release -DCARLA_UNREAL_ENGINE_PATH="$UE_ROOT" -DPython3_EXECUTABLE="$PYTHON" -DBUILD_CARLA_CLIENT=ON -DBUILD_CARLA_SERVER=ON -DBUILD_PYTHON_API=ON -DBUILD_CARLA_UNREAL=ON
```

只需要 LibCarla 时可显式 `-DBUILD_CARLA_UNREAL=OFF -DBUILD_PYTHON_API=OFF`。按需求设置 `ENABLE_OSM2ODR`、`ENABLE_RSS`、`ENABLE_GLTF`、`ENABLE_ROS2` 等，缺依赖就停在缺项；`ENABLE_ROS2=ON` 仍不接通被注释的 Ros2Native 子目录。`CARLA_LAUNCH_ARGS` 才是 Options 定义的 launch 参数，使用分号列表，不照抄旧脚本未对应的 `LAUNCH_ARGS`。

产物：configure 日志、Build/CMakeCache.txt、生成器/编译器/Python/UE 路径和生效 flags；检查目标是否实际生成。配置通过只证明生成成功。改生成器或编译器时使用独立 BUILD_DIR，恢复为原目录与原参数，不全局清理。

路由：库 → `carla-build-libcarla`；wheel → `carla-build-python-api`；GLTF/ROS2 条件 → 对应 skill；Editor/Shipping 必须另有显式授权。

Source：`CMakeLists.txt`，`CMake/Options.cmake`，`CMake/Toolchain.cmake`，`Unreal/CMakeLists.txt`。
