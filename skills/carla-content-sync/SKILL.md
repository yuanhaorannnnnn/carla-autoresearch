---
name: carla-content-sync
description: 核实或同步 CARLA Unreal Content 的来源、版本配对与目标路径；用于资产缺失和代码资产不匹配，不触发构建或 Editor。
metadata:
  category: engineering
  execution: workflow
  operations: ''
---

# carla-content-sync

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：代码 commit、资产来源/允许的 commit、目标主 checkout 和下载或同步授权。定位 `Unreal/CarlaUnreal/Content/Carla`，检查实际版本控制状态、`Blueprints` 及请求地图依赖；记录 symlink 的真实目标和拥有者。`check-unreal-content` 只检查 `Content/Carla/Blueprints` 是目录，不能据此判断资产完整。

基线 `CarlaSetup.sh` 缺 Content 时在 `Unreal/CarlaUnreal/Content` 下 clone `https://bitbucket.org/carla-simulator/carla-content.git` 的 `ue5-dev` 到 `Carla`。该默认分支不证明与定制 sprint42 配对；优先用项目已有资产锁定记录/已验证主 checkout 版本，缺版本证据就明确缺口。不要为同步 Content 执行整套 CarlaSetup.sh。只在授权下载且目标未占用时，单独执行等价 `git clone --branch <approved-ref> <approved-source> <empty-Carla-target>`；已有目录先检查 dirty 和实际 remote，禁止强制 reset、替换或自动 pull。

产物：代码 commit、资产 commit/来源、真实目录、请求资产存在性及同步日志。资产来自非 Git 包时保留包版本/校验记录，不伪造 commit。同步失败保留已完成路径和缺项；暂存下载与当前可用资产分开，验证后再切换用户指定目标。

路由：环境依赖 → `carla-environment-setup`；launch-only → `carla-editor-launch`；制作地图 → `carla-fbx-import`/`carla-opendrive-authoring`。

Source：`CarlaSetup.sh` 的 CLONE CONTENT 段；`Unreal/CMakeLists.txt` 的 `CARLA_UE_CONTENT_CHECK_PATH`、`check-unreal-content`。
