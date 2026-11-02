---
name: carla-fbx-import
description: 准备或导入 FBX 地图/props package JSON，核对导入设置与 UE5 适配；用于工程资产导入，不走 runtime import_asset、USD 或 Houdini。
metadata:
  category: engineering
  execution: conditional
  operations: ''
---

# carla-fbx-import

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：FBX/XODR、package 名、maps/props JSON、材质策略、单图/tiles、目标 Content 及资产修改授权。地图 JSON 至少含 `maps:[{name,xodr,use_carla_materials,source}]`；tile 图改用 `tiles:[...]` 和 `tile_size`；props 使用 `{name,source,tag}`。source/xodr 相对该 JSON 所在目录。默认扫描 CARLA_ROOT/Import，同名 `.fbx`/`.xodr` 成对识别，tile 用 `*_Tile_*.fbx`。

可先只生成输入描述：`"$PYTHON" Util/BuildTools/Import.py --package <name> --json-only`；这会写 JSON/decals，并非只读。检查 `generate_import_setting_file(...)` 生成的 ImportGroups：DestinationPath、FbxFactory、bConvertSceneUnit、碰撞与材质设置，默认 `bReplaceExisting=true`，因此先确认已有目标是否允许替换。

完整 `Import.py` 的 `invoke_commandlet` 仍读取 `UE4_ROOT` 并调用 `UE4Editor`；此 sprint42 UE5 链路未经适配，不运行旧全链路，也不把环境变量改成 UE5 路径就宣称修好。已构建 UE5 Editor 中可按当前 FbxFactory/ImportAssets commandlet 支持情况，使用审查后的 import settings：`UnrealEditor <uproject> -run=ImportAssets -importSettings=<exact-json> -nosourcecontrol -replaceexisting`；此直接路线需先核实当前 Editor 接受这些参数，不能绕过替换授权。未满足则交付 JSON、待适配入口和具体缺口。

产物：输入 JSON、import settings、生成的 package config/Content 资产与导入日志；完整脚本还会启动 navmesh 线程、MoveAssets、PrepareAssetsForCooking、LoadAssetMaterials 和 TM cache，所以不能把它作为单个 FBX 试导入。失败按具体目标恢复备份，不全量重新导入。

路由：材质/地图准备 → `carla-map-materials`；步行导航 → `carla-navmesh`；TM cache → `carla-tm-map-cache`；runtime 文件传输 → `carla-runtime-assets`。

Source：`Util/BuildTools/Import.py` 的 generate_json_package、generate_import_setting_file、invoke_commandlet、import_assets_from_json_list。
