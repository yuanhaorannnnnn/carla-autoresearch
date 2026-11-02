---
name: carla-build-python-api
description: 为指定 Python 构建 CARLA wheel，或在明确授权时安装到指定环境；用于 binding/wheel 错误，不改全局 Python。
metadata:
  category: engineering
  execution: workflow
  operations: ''
---

# carla-build-python-api

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：已配置 BUILD_DIR、目标解释器/venv、构建授权、可选安装授权。先核实 cache 中 `Python3_EXECUTABLE` 与 `BUILD_PYTHON_API`。PEP517 默认以该解释器 `-m build --wheel` 构建，wheel 输出在 `<BUILD_DIR>/PythonAPI/dist`；不能用 controller 的解释器替代目标 wheel Python。

```bash
cmake --build "$BUILD_DIR" --target carla-python-api --parallel <jobs>
```

构建成功后定位本次生成的唯一 wheel，核对 filename 的 Python/平台 tag。安装须有相应授权，向指定 venv 执行 `"$PYTHON" -m pip install <exact-wheel-path>`；不使用通配符吞入多个旧 wheel。现有 `carla-python-api-install` target 实际先依赖 wheel 构建，再 `pip install -e <generated-carla-source>`，它不是 wheel 安装，也不是只读检查；只有明确需要 editable 安装才选择该 target。

`buildpyapi.sh` 会强设私人 HTTP/HTTPS proxy 且重新 configure，不把它当通用构建入口。无网络、缺 Python build 工具或 binding/link 错误，报告所在阶段，保留当前可用 venv/wheel；不自动升级全局 pip/Python。安装后只读检查 `carla.__file__`/client 版本；连 server 由 connection 执行。

产物：wheel 路径、tag、构建日志、解释器与代码 commit；安装结果单列目标环境和实际导入路径。

路由：配置解释器 → `carla-build-configure`；连接/版本匹配 → `carla-connection`；包附带 wheel → `carla-build-shipping`。

Source：`PythonAPI/CMakeLists.txt` 的 `CARLA_PYTHON_API_DIST_PATH`、`carla-python-api`、`carla-python-api-install`；`buildpyapi.sh`。
