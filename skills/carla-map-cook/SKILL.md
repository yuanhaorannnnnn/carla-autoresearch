---
name: carla-map-cook
description: 在已有 CARLA Editor 工具链中仅 cook 指定地图并核对 cooked 输出；用于 single_map_package.sh，不声称生成独立可分发地图包。
metadata:
  category: engineering
  execution: workflow
  operations: ''
---

# carla-map-cook

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：含 Content 的正式主 checkout、现有 UE Editor、明确地图名称、cook 授权、预期平台。确认目标地图存在并记录已有 cooked 文件，禁止依赖脚本默认 `EmptyGround` 代替用户目标。

Linux 基线入口为 `./single_map_package.sh <MapName>`，使用环境 `CARLA_UNREAL_ENGINE_PATH` 拼出 `Engine/Binaries/Linux/UnrealEditor`，project 为当前目录下 `Unreal/CarlaUnreal/CarlaUnreal.uproject`；实际命令是 `UnrealEditor <uproject> -run=cook -targetplatform=Linux -MAP=<MapName> -cooksinglepackage`。脚本名含 package 但没有 stage/archive/package 或依赖完整性封装。未明确 cook 权限不运行。

产物：Editor cook 日志、目标 map 对应的 `Unreal/CarlaUnreal/Saved/Cooked/Linux` 实际文件及本次生成证据；平台/目录以日志为准。区分 map package 本体与所需依赖是否已 cook。只有 cook 通过，不得宣称脱离基础 Shipping 包可部署。失败按缺 asset、shader、map path 或 toolchain 归因，保留其他地图缓存；不全删 Saved/Cooked。

路由：准备 imported map → `carla-map-materials`；完整分发包 → `carla-build-shipping`；启动已有包验证 → `carla-server`。

Source：`single_map_package.sh`；`Unreal/CMakeLists.txt` 的完整 UAT package 路线作边界对照。
