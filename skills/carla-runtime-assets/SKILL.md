---
name: carla-runtime-assets
description: 管理 CARLA runtime 文件基目录、required files 下载、request_file、import_asset 与 static mesh 存在性检查；不负责 UE 资产制作、cook 或发布。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 运行时资产传输

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先确认路径属于 client 还是 server，不把本地文件存在当作 server 可访问。按实际目标选择：

| API | 输入/结果与状态影响 |
|---|---|
| `client.set_files_base_folder(path)` | 文件基目录；改变后续传输落点 |
| `client.get_required_files(folder="", download=False)` | 查询所需文件；`download=True` 会下载写盘 |
| `client.request_file(name)` | 请求指定文件，可能写盘；保留返回与落点 |
| `client.check_static_mesh(mesh_path)` | 查询 server mesh 路径检查结果 |
| `client.import_asset(package_name)` | server 导入 package；属于资产变更 |

先列清单、磁盘空间和授权下载/导入范围，再请求具体对象。保存文件名、来源、目标和异常；先检查相同输出，避免 timeout 后重复导入。不存在的 mesh/package、传输失败、权限/路径错误分别报告；不得为了补资源跑全量资产安装或改 package 内容。API 返回不证明材质、碰撞、cook 质量；这些由工程资产 skill 验证。

## 交接与证据

[carla-world](../carla-world/SKILL.md)；[carla-prop-assets](../carla-prop-assets/SKILL.md)；[carla-vehicle-assets](../carla-vehicle-assets/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Client.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
