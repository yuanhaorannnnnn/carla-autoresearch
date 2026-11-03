---
name: carla-build-editor
description: 仅在用户明确要求编译 CARLA Editor 或运行 lunch.sh 时构建 CarlaUnrealEditor；启动已有 Editor 走 carla-editor-launch。
metadata:
  category: engineering
  execution: workflow
  operations: ''
---

# carla-build-editor

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：用户明确构建授权、含匹配 Content 的正式主 checkout、UE fork、已有配置和构建日志位置。先用 `git rev-parse --show-toplevel`/`git worktree list` 确认当前目标；检查 Content、dirty 状态和 Build 目录。可读取 checkout 自带 `.agents/skills/build-editor/SKILL.md` 的本地规则，但不要再次调用本插件同名 skill，不依赖个人 skill 目录。

用户明确要求 `lunch.sh` 时，在确认过的 CARLA checkout 运行 `./lunch.sh`。当前脚本会 `rm Build/CMakeCache.txt`、重新 configure Release/ROS2 OFF/GLTF ON，随后 `cmake --build Build --target launch -j 24`，因此包含编译和启动；先说明这些具体副作用，cache 缺失时 rm 报错也不能代表后续未执行。保留原 cache 证据，不自行改脚本消除差异。

用户只要求构建 Editor 时，在已审查配置下使用：

```bash
cmake --build "$BUILD_DIR" --target carla-unreal-editor --parallel <jobs>
```

该 target 依赖 `carla-unreal` 和 UE order-only dependencies。未配置、Content 缺失、不是正式主 checkout 时停在缺项，交 configure/content-sync，不自行下载资产或在工作树复制 Content。若用户要求新终端，终端打开状态、实际编译状态与 launch 状态分开报告。

产物：实际 target、退出码、完整日志、CarlaUnrealEditor 输出与代码/配置身份。编译通过不证明地图可打开。失败保留增量输出，按首个有效 compile/link 错误修复；不清空 Intermediate/DerivedDataCache。

路由：已有二进制启动 → `carla-editor-launch`；Shipping → `carla-build-shipping`；禁止把普通修改或测试请求当显式构建授权。

Source：`lunch.sh`；`Unreal/CMakeLists.txt` 的 `carla-unreal-editor`、`launch`。
