---
name: carla-gltf-load
description: 核实并使用 WITH_GLTF 条件下的 GLB static mesh/车辆加载路线；不泛化为任意 glTF 地图导入，不代替 factory 注册。
metadata:
  category: engineering
  execution: conditional
  operations: ''
---

# carla-gltf-load

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：GLB 文件、已启用且有运行证据的 WITH_GLTF/glTFRuntime 插件、目标 static mesh 或 vehicle definition、文件路径与执行范围。先核对 CMake `ENABLE_GLTF`、实际 UE `WITH_GLTF`、插件和二进制；开关 ON 不证明插件齐备或加载器安全。

static mesh 路线在 `AStaticMeshFactory::SpawnActor` 读取 `ActorDescription.Variations["mesh_path"]`；仅 `.glb` 分支使用 `glTFLoadAssetFromFilename`，TransformBaseType=YForward，然后 LoadStaticMeshRecursive；非 glb 走 UE LoadObject。应先查看当前 blueprint 可修改属性再通过 actor spawn 设置 mesh_path/scale/place_on_ground/dist_to_ground，不能虚构统一 `load_gltf()` Python API。文件必须在 server 可读路径；client 路径不能直接替代。

vehicle 路线要求现有 definition 的 ID 包含 `.glb.`，从 ID 最后段取名，读取 server `Content/CustomVehicles/<name>.glb`。Body skeletal mesh、Glass 与 `Vehicle_Base`/四轮节点及 physics bodies 有专有命名契约；先在文件中检查这些结构，不任意改车辆 ID 强行触发。运行前确认 loader 返回值处理，本基线若 RuntimeAsset 为空有未充分防护路径，不用坏文件试崩 server。

产物：生效编译条件、server 文件路径、实际生成 actor/mesh、变换与加载日志；不保证持久化 UE asset，也不证明车辆 physics 标定。没有合适 definition/编译证据就报告条件缺失，交 asset/extension，不造假入口。失败仅清理本任务 owned actor 与输入副本，不删除共享 CustomVehicles。

路由：runtime spawn → `carla-actors`；vehicle 注册 → `carla-vehicle-assets`；构建 flag → `carla-build-configure`；USD → `carla-usd-import`。

Source：`CMake/Options.cmake` 的 ENABLE_GLTF；`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Actor/StaticMeshFactory.cpp`；`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Actor/Factory/VehicleActorFactory.cpp`。
