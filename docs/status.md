# 开发状态与验证范围

更新：2026-11-02。当前是 **development preview**，不是正式安装包发布或全平台运行认证。

## 已实现

- 107 项领域/组合 skill、2 项旧名兼容路由；覆盖 25 类传感器。另有 4 项外部集成仅列作预留，没有生成空壳 skill。
- 17 个基础原子 operation；每个 skill 明确已封装命令、原生流程或条件依赖。
- 离线 `skills list/show` 以及可查询的 operation schema。
- 有界 RGB/RayCast 采集、独占 session、资源所有权和恢复检查。
- RayCast 有限参数研究控制器，含冻结输入、配对试验、独立确认、预算和停止恢复。
- 离线 `research validate` 和终态产物只读 `research compare`。

技能指引完整不表示全部能力已封装。USD、原生 ROS2、旧 UE4 导入链和部分 Editor OpenDRIVE 制作路径存在明确依赖或实现缺口，详见对应 skill。

## 取得的证据

| 证据 | 范围 | 不能推导的结论 |
|---|---|---|
| 109 份结构、相对引用与索引一致性检查 | skill 可定位、元数据和命令引用一致 | 不能证明自然语言必然路由正确或服务端支持 |
| 50 项 worker/protocol 测试 | fake CARLA 下的输入、所有权、episode 与接口行为 | 不代表真实车辆/传感器运行 |
| 30 项研究测试 | synthetic capture 下的状态、预算、证据校验与恢复 | 不代表取得真实性能收益 |
| 5 项 catalog/研究 CLI 测试 | 离线发现、校验、比较和拒绝篡改 | 不代表宿主插件安装完成 |
| 6 项独立只读任务演练 | DVS、MEMS、单灯冻结、USD、ownership、跨 episode 数据配对 | 不是 107 项 workflow 的端到端覆盖 |
| 既有 0.10.0 包的短采集 | Town05 RGB 3 帧、RayCast 6 帧，以及自有资源清理/设置恢复 | 包的源码 commit 未核实，不能归因到 sprint42 构建 |

测试可在开发环境复现：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install '.[test]'
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/update_skill_catalog.py --check
```

以上是贡献者验证路径，不是插件安装演示。实验真实/模拟证据分别解释。

## 下一阶段

1. 按[已记录计划](installation-demo.md)完成干净插件安装与新会话引导。
2. 演示新增基础命令与有限研究的真实闭环。
3. 补齐 scene/weather/seed provenance，固定可复现 workload。
4. 核验支持矩阵，再从正式主线产出发行材料。

源码与文档的 GitHub 更新、插件本机安装、发行包、公共目录上架是不同交付状态。本次 GitHub 展示更新不宣称后面三项已完成。
