---
name: carla-prop-assets
description: 把已有 StaticMesh 注册成 static.prop.* 并保存 factory/package JSON；用于 prop 资产注册，不负责运行时 spawn/control。
metadata:
  category: engineering
  execution: native-api
  operations: ''
---

# carla-prop-assets

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：StaticMesh object path、唯一 prop name、size（tiny/small/medium/big/huge）、目标 Content 与写授权。确认 mesh 可加载、名字不带 `static.prop.` 前缀、不与当前 DefinitionsMap 冲突，备份 factory asset 与 `Content/Carla/Config/Default.Package.json`。

在已启用 Unreal Python 的 Editor 环境执行 `Unreal/CarlaUnreal/Plugins/CarlaTools/Content/Python/add_prop_to_prop_factory.py --static_mesh_path <mesh-object-path> --name <name> --size <size>`。该脚本加载 `/Game/Carla/Blueprints/Props/PropFactory.PropFactory_C` CDO 的 DefinitionsMap，构造 `unreal.PropParameters(name,mesh,size)`，写键 `static.prop.<name>`；已存在时仅输出提示，不更新 mesh/size。未知 size 会默认为 Medium，所以先校验，不能借它做隐式修正。

新条目分两步持久化：先 `EditorAssetLibrary.save_asset(prop_factory_path, False)`，再向 Default.Package.json 的 props 添加 `{name,path,size}`。没有跨文件事务；JSON 缺失/无 props/写失败可能已保存 factory，先比较两侧再修复，不盲目重跑或追加重复项。按需要重载 factory、JSON 回读并核对 ID/mesh/size。

产物：factory 保存日志、JSON 增量、重载后条目；运行时 blueprint library 可发现性需另获运行授权验证。StaticMesh 存在不证明碰撞合理；导入碰撞、尺寸与物理单列。失败仅回退本任务条目和对应 JSON 项，保留已有配置。

路由：缺 mesh → `carla-fbx-import`/`carla-gltf-load`；cache factory → `carla-actor-extension`；使用 prop → `carla-actors`。

Source：`Unreal/CarlaUnreal/Plugins/CarlaTools/Content/Python/add_prop_to_prop_factory.py`；`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Actor/StaticMeshFactory.cpp`。
