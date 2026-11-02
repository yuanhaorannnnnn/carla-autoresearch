# 开发预览入门

当前可在源码 checkout 中探索 CLI 和 skills。正式插件的干净安装仍待演示；不要把本页操作视为已完成的安装验收。

## 先认识操作面

控制器要求 Python 3.10+，运行时只用标准库：

```bash
export PYTHONPATH="$PWD/src"
python3 -m carla_agent --help
python3 -m carla_agent skills list --category sensors
python3 -m carla_agent skills show carla-camera-dvs
python3 -m carla_agent schema capture.run
```

这些命令不连接 CARLA。`skills list --query` 匹配短关键词或完整 blueprint，空格分隔的词需全部命中；完整自然语言请求由宿主根据 skill description 路由。返回的 `file` 是相对插件根的指引路径，`cli_operations` 只列已封装子集。

## 配置已有 CARLA 实例

将 `profiles/examples/local.json` 复制到自己的配置位置：

- `client_python`：安装匹配 CARLA PythonAPI 的 Python 解释器绝对路径，Python 3.8+。
- `output_root`：独立输出目录的绝对路径，不能写进插件缓存。
- `host` / `port`：现有服务端地址；默认本机 2000。
- `session_policy`：初次保持 `inspect_only`。

先检查连接和版本，再读世界：

```bash
python3 -m carla_agent connection doctor --profile /absolute/path/local.json
python3 -m carla_agent world inspect --profile /absolute/path/local.json
python3 -m carla_agent blueprints list --profile /absolute/path/local.json --params '{"filter":"sensor.*"}'
```

版本字符串匹配只是必要检查，不证明 wheel 包含全部 sprint42 定制接口。CARLA 服务未运行、解释器缺 wheel 或版本不匹配时，按实际错误处理，不自动安装其他 wheel 或启动/结束进程。

## 执行短采集

只有明确的采集任务才切换到独占配置：确认专用实例，将 `session_policy` 设为 `exclusive`，填写实际 `expected_server_version`。先查当前地图和车辆 blueprint，再修改 [RGB](../examples/rgb-capture.json) 或 [LiDAR](../examples/lidar-capture.json) recipe；其中 Town05 和车辆 ID 都只是示例。

```bash
python3 -m carla_agent sensors describe --profile /absolute/path/local.json --params '{"blueprint":"sensor.camera.rgb"}'
python3 -m carla_agent capture run --profile /absolute/path/local.json --request examples/rgb-capture.json
```

sprint42 RGB 若暴露 `send_data_stream`，在 recipe 的 sensor_attributes 显式设为 `true`；未暴露则不添加。capture 只接受 RGB 与标准 RayCast LiDAR，并自行管理单车、单 sensor、session 与清理，不需要先手动 `session open`。

当前 custom-mems profile 只放开对应挂载，不扩展 capture 支持范围。多源和其他 sensor 的原生流程见各专项，不能借用活跃 CLI lease 或绕过 ownership 拒绝。

输出核对退出码、原始文件、frame/timestamp、缺帧/超时和清理状态。RGB 为 BGRA8，RayCast 为 float32 XYZI；以产物 metadata 为准。成功清理不代表采集成功。

## 下一步

- 学习路径：[carla-onboarding](../skills/carla-onboarding/SKILL.md)。
- 任务边界：[完整目录](skill-catalog-sprint42.md)。
- 研究计划、阈值与预算：[研究契约](../references/carla-research.md)。
- 已验证范围：[status](status.md)。
- 将来的正式安装：[演示计划](installation-demo.md)，当前暂缓。
