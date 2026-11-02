# 架构：共享操作，分层知识与实验

CARLA Agent 连接外部 CARLA 实例。它将领域知识组织成 skills，将可重复执行的基础动作放进公共工具层，再由 Auto Research 组合采集和比较。当前交付是开发预览，安装与新增研究实机验证见 [status](status.md)。

## 执行路径

```text
用户任务
  ├─ 领域 skill ────────┐
  └─ 研究 skill → controller
                       ↓
                  CLI / schema
                       ↓
                  bridge.invoke
                       ↓
             独立 PythonAPI worker
                       ↓
                  CARLA server
                       ↓
            原始产物 / 帧身份 / 错误
```

| 层 | 拥有的职责 | 边界 |
|---|---|---|
| Skills | 任务路由、领域参数/数据解释、操作步骤、依赖与失败判断 | 不用文本声明替代实际工具结果 |
| CLI / protocol | 参数与 schema、JSON 信封、离线技能发现 | 不自动启动或编译 CARLA |
| Bridge | 选择 profile 的 Python、调用固定 worker、处理超时和身份 | 不把 recipe 字段当 shell/Python 程序执行 |
| Worker | 匹配 API 调用、session、资源所有权、帧收集和恢复 | 不决定实验目标，不控制他人 actor |
| Research controller | 冻结输入、trial 顺序、预算、状态、比较和确认 | 复用公共 capture，不实现第二套 sensor runner |

代码入口：[cli.py](../src/carla_agent/cli.py)、[protocol.py](../src/carla_agent/protocol.py)、[bridge.py](../src/carla_agent/bridge.py)、[worker.py](../src/carla_agent/worker.py)、[research.py](../src/carla_agent/research.py)。

## Skills 与执行能力的区别

已创建 107 个领域/组合 skill 和 2 个兼容路由。拆分依据是独立配置、操作与数据契约；一个 skill 可以包含多个原子动作，单个属性和内部序列化类型不各建 skill。

`metadata.execution` 表示主要路径：

- `cli`：已有结构化命令；完整支持范围仍以其 schema 为准。
- `native-api`：匹配版本的原生 API/Editor/脚本操作指引。
- `conditional`：依赖构建选项、资产、外部组件，或存在已知接线缺口。
- `workflow`：组合已有能力。
- `alias`：旧名称的兼容路由。

当前 CLI 提供 17 个基础 operation。一个 sensor 支持 describe/attach，不代表 capture 已支持其数据格式。`capture.run` 目前只封装 RGB 与标准 RayCast LiDAR。

原生流程不得接管 CLI/research lease 或绕过所有权拒绝。未封装的变更流程需独占实例、独立拥有完整资源生命周期、限制步数与等待，并按 server/episode 身份恢复状态。Auto Research 仅走公共工具层。完整边界见[共享规则](../references/carla-agent-shared.md)和[技能目录](skill-catalog-sprint42.md)。

## 两个 Python 环境

控制器要求 Python 3.10+，运行时只用标准库。worker 在 profile 指定的 Python 3.8+ 中独立执行，那里需要与 server 匹配的 `carla` wheel；worker 不导入控制器包。

这个分离使插件不必强迫用户重建已有 CARLA Python 环境。调用传递结构化 JSON，路径按独立 argv 处理，未知 profile/operation 字段拒绝。真实 CARLA API 的日志写 stderr，stdout 保留协议响应。

技能离线索引作为 package data 分发；CLI wheel 只提供索引和工具，完整 plugin 的 skills/references 由宿主加载。正式安装需要分别核对两部分，不能仅以 Python import 成功判定插件安装成功。

## 会话、控制和采集

只读查询不打开 session。变更要求明确任务授权、独占配置和匹配版本；session 记录 episode、原 settings 与本次 actor。

- spawn/attach 成功后登记所有权；destroy 只作用于所属 session。
- 世界已变化或设置不再匹配时，拒绝冒充恢复成功。
- `vehicle.control` 只提交自有车辆输入，不隐式 tick；submitted 表示 RPC 返回，不证明物理状态推进。
- 一项任务只有一个时间推进者；batch 的 do_tick 同样受所有权约束。
- capture 自管有界 session、warmup、队列、frame 匹配、文件输出与异常清理。

frame、simulation timestamp 与 callback 接收时间分别记录。连续流、低频采样和事件流采用各自的有效输出规则；无回调不能自动当作有效空事件。

## 研究状态与证据

当前研究是在同一构建内比较有限的 RayCast LiDAR 属性候选。计划冻结 workload、变化字段、质量底线、比较阈值、独立重复、确认和预算；控制器是 run 状态的唯一写入者。

```text
研究计划 → 离线 validate → start → 配对 trials → 选择 → 独立确认
                              ├─ status / stop / resume
                              └─ 终态产物 → 离线 compare
```

每个 trial 有独立目录和身份。恢复前核对冻结输入、原始产物、进程与 episode；中断 trial 在新目录重跑，不覆盖旧证据。控制器使用进程/实例锁避免重复执行，预算不会因 resume 重置。

`research validate` 只读 plan/profile，给出 trial 数量事实；不检查实时 server。`research compare` 读取已有 writer lock 并重验终态产物，不连接 CARLA、不写 state/events/report。部分终态只给可核对事实，整体保持 not_evaluated。

当前指标 `tick_to_sensor_callback_ms` 覆盖客户端推进与回调路径，不是 GPU kernel 时间。点数/有限坐标底线不是几何 oracle，不能据此声称语义保持。完整 scene/weather/seed provenance 和真实研究演示仍待补齐。详细约束见[研究契约](../references/carla-research.md)。

## 仓库与分发

```text
plugin.json                  portable 插件身份与展示信息
skills/                      107 专项/组合 + 2 兼容路由
references/                  按需加载的共享和领域知识
src/carla_agent/              protocol、CLI、bridge、worker、research、catalog
profiles/examples/           不含个人环境的配置示例
examples/                    有界采集 recipe
scripts/update_skill_catalog.py
tests/                      fake/synthetic 与接口行为验证
evals/skills/               独立技能任务演练素材
docs/                      入门、架构、契约、状态、迁移和演示计划
assets/branding/           图标与README横幅
legacy/                    不随新工具安装的历史源码
```

CARLA 本体不进入插件仓库。保留原 CARLA 工具历史与 URL，不使用旧预训练 upstream 的分支替代产品历史。私人迁移备份与 agent 工作记录不随公开源码分发。

源码/文档推送、本机安装、发行包与公共目录上架分别记录。正式打包由主分支完成；安装演示流程已保存并暂缓，见[计划](installation-demo.md)。
