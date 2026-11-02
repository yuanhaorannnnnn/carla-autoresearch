---
name: carla-build-shipping
description: 仅在用户明确要求 CARLA Shipping 打包或运行 package.sh 时执行 build/cook/stage/archive/package；最终包必须由正式主分支生成，发布另行授权。
metadata:
  category: engineering
  execution: workflow
  operations: ''
---

# carla-build-shipping

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：明确打包授权、正式主分支/主 checkout、代码 commit、匹配 Content、UE fork、配置与目标包路径。先核实主分支身份和 `git worktree list`，检查 dirty 工作与当前 Build/Package 产物。不能在 feature 工作树产出最终发布包；不自动切分支/merge。可读取 checkout 内同名 build-shipping 规则，但不递归调用本插件，不依赖个人绝对路径。

用户明确要求 `package.sh` 时从核实 checkout 执行 `./package.sh`。先说明当前脚本会删除 `Build/CMakeCache.txt`，并 `rm -rf Build/Package/*` 清除原包，然后 configure Release/ROS2 OFF/GLTF ON，最终 `cmake --build Build --target package -j 24`。需保留的已有包先按用户目标另存；不得用清包掩盖未验证旧产物。

明确要求 Shipping 且采用已有审核配置时可执行：

```bash
cmake --build "$BUILD_DIR" --target package-shipping --parallel <jobs>
```

`package` 使用 cache 的 `CARLA_UNREAL_PACKAGE_BUILD_TYPE`，不能仅凭 target 名推断 Shipping。底层依赖 wheel/Editor，执行 UE Build 后 UAT `BuildCookRun -cook -stage -archive -package -iterate -build -clientconfig=Shipping`，版本文件与附加文件复制在 post-build；压缩步骤当前注释，目录产物不等于 tar/zip 已生成。

产物位于 `<BUILD_DIR>/Package/Carla-<version>-<system>-Shipping`，另有 StagedBuilds。报告实际路径、VERSION、日志、代码 commit、Content 身份及是否启动验证；不可把打包成功称为发布。失败标清 build/cook/stage/archive 阶段，保留日志和部分包，不自动清目录重试。

路由：单地图 cook → `carla-map-cook`；包启动 → `carla-server`；代码/资产版本缺口 → configure/content-sync。发布必须在正式主分支另行完成授权动作。

Source：`package.sh`；`Unreal/CMakeLists.txt` 的 `add_carla_ue_package_target`；`Unreal/Package/CreateCarlaVersionFile.cmake`。
