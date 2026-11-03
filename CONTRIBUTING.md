# 参与 CARLA Agent

欢迎围绕具体任务改进 skill、原子操作和验证证据。提交问题时附上 CARLA client/server 版本、对应源码/二进制身份、操作及最小输入、期望与实际结果；分享配置前去掉凭证、个人路径和其他私有信息。

## 改动边界

- 领域 skill 维护参数/数据契约与失败判断；共享机制放 references 或公共执行器，避免重复采集实现。
- `metadata.operations` 只列真实命令；原生 API 和条件能力明确标注。注册在源码里不代表当前二进制支持。
- 新操作要校验参数、资源所有权和 episode；不得增加任意 shell/eval 入口或按端口杀进程。
- 研究复用公共 capture；保持冻结输入、独立重复、失败记录和预算。没有正确性 oracle，不宣称语义保持。
- 保留已有未提交改动，按文件限定提交范围。不要把 profiles、runs、私人迁移副本或 agent 工作目录加入公开变更。

## 检查

开发环境与测试入口见 [status](docs/status.md)。修改 SKILL.md 后刷新并检查离线索引：

```bash
python3 scripts/update_skill_catalog.py
python3 scripts/update_skill_catalog.py --check
```

该脚本需要开发依赖 PyYAML，控制器运行时不需要它。结构检查不代替实际任务演练；涉及状态或数据逻辑的改动提供对应测试。CARLA/Editor 构建与真实仿真应使用明确授权和匹配环境，不为修改文档而运行。

提交说明应写明：用户可观察变化、验证层次、实际结果和剩余限制。图标/文档中的视觉示意不作为运行截图或性能证据。
