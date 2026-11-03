---
name: carla-build-libcarla
description: 按已确认 CMake 配置构建 CARLA C++ client/server 库；用于 LibCarla 编译与依赖错误，不构建 Editor、wheel 或 Shipping。
metadata:
  category: engineering
  execution: workflow
  operations: ''
---

# carla-build-libcarla

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：已配置 BUILD_DIR、client/server 所需目标及明确编译授权。读 `CMakeCache.txt` 的 `BUILD_CARLA_CLIENT`/`BUILD_CARLA_SERVER` 和 toolchain；只有启用的库才有对应 target。依赖包括 Boost、rpclib、Recast、png/zlib、server protobuf 等，以当前 `LibCarla/CMakeLists.txt` 链接列表为准。

按目标分别运行：

```bash
cmake --build "$BUILD_DIR" --target carla-client --parallel <jobs>
cmake --build "$BUILD_DIR" --target carla-server --parallel <jobs>
```

用户只要求一种库就只选对应命令；`<jobs>` 取已确认资源预算。`INSTALL_LIBCARLA=ON` 是配置默认，不等于授权执行 install target。禁止为了库构建顺带 `cmake --build Build` 构建全部目标。

产物：完整构建退出码/日志、具体库文件路径与修改时间、代码 commit、配置及依赖版本。从生成器实际输出定位库，不硬编码不存在的 Release 目录。失败先定位 compile/link/dependency 层，保留 cache 与对象供增量恢复；需要改配置转 configure，不默认 clean 或切 Python。

路由：Python binding 编译 → `carla-build-python-api`；UE server game binary → `carla-build-editor`/`carla-build-shipping`；C++ client 库成功不能证明仿真 server ready。

Source：`CMakeLists.txt` 的 LibCarla add_subdirectory；`LibCarla/CMakeLists.txt` 的 `carla-client`、`carla-server` targets。
