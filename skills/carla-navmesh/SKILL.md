---
name: carla-navmesh
description: 从 CARLA 场景碰撞或 FBX/OBJ 与 XODR crosswalk 生成 Walker 导航 bin；不生成 TM 路网，旧 tiled Recast 路线不支持。
metadata:
  category: engineering
  execution: conditional
  operations: ''
---

# carla-navmesh

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：目标地图/碰撞或单图 FBX/OBJ、同图 XODR、可用 FBX2OBJ/RecastBuilder、输出 Nav 目录及生成授权。先核对工具文件和当前 Python 依赖；旧 Import.py 对 tiles 的 navigation 分支已注释，不承诺 tile FBX 自动导航。

已有 Editor 可用 CarlaExporter 的 Export All 导出：实际若有 selected actors 则只导出选择，否则整个 world；带 `NoExport` tag 会跳过。产物为 project `Saved/<WorldMapName>.obj`，导出碰撞并以 0.01 将 UE cm 转为 Recast m。明确选择范围，不能误把局部 OBJ 当全图。已有 OBJ 可直接交匹配 `RecastBuilder <Map.obj>`，保留工具版本与参数。

单图 FBX 旧工具路线在 `Util/DockerUtils/dist` 中 `./build.sh <fbx-basename> <xodr-basename-without-extension>`：依次 FBX2OBJ、get_xodr_crosswalks.py、addOBJ.py、RecastBuilder，输出 `<basename>.bin`。脚本若缺 tool/file 多数直接跳过，且会删工作目录 crosswalks.obj、chmod 工具及覆盖同名结果；使用隔离 scratch 副本，不碰共享 dist 输入。Import.py 传第二参数时可能已含 `.xodr`，build.sh 再加扩展名；先按实际文件名核对，不能据无报错假定 crosswalk 加入。

产物检查：OBJ 与 bin 非空、本次生成时间/日志、crosswalk 是否合并；仅经明确目标写入 `Content/<Package>/Maps/<Map>/Nav/<basename>.bin`，保存原 bin。可用 Walker 导航需之后运行验证，不能只凭 bin 存在。失败保留源 FBX/XODR，恢复本次目标 Nav，不清其他地图。

路由：TM cache → `carla-tm-map-cache`；large-map → `carla-large-map`；Walker 使用 → `carla-walker-navigation`；旧导入 → `carla-fbx-import`。

Source：`Unreal/CarlaUnreal/Plugins/CarlaExporter/Source/CarlaExporter/Private/CarlaExporter.cpp`；`Util/DockerUtils/dist/build.sh`；`Util/BuildTools/Import.py` 的 build_binary_for_navigation。
