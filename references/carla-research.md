# 研究闭环

入口拆分：计划与阈值 → [research-plan](../skills/carla-research-plan/SKILL.md)；固定测量 → [benchmark](../skills/carla-benchmark/SKILL.md)；只读证据复核 → [compare](../skills/carla-compare/SKILL.md)；候选/预算/恢复 → [parameter-search](../skills/carla-parameter-search/SKILL.md)。四项共用当前控制器，旧 carla-research 仅做兼容路由。

研究开始前将问题缩成可证伪假设、观测量、对照条件和有界预算。区分仿真输出指标与现实设备性能；不能靠扩大 `channels` 或换传感器证明物理规格。使用用户真实目标选择指标，不替换成“命令成功率”。

## Plan v1

先读取 `carla-agent schema research.start` 确认以下字段已实现，再准备 plan 文件；实现未就绪不能按设计文本声称可执行。

| 字段 | 意义与来源 |
|---|---|
| `schema_version` | `1` |
| `profile` | 实际 profile 文件路径 |
| `workload` | 固定 RayCast LiDAR capture recipe；不是任意 Python 或源码 patch |
| `allowed_attributes` | 明确允许研究改变的 sensor attribute 名称 |
| `candidates` | 每项含 `id` 与 `sensor_attributes` 覆盖；不得修改未声明属性 |
| `objective` | `metric: tick_to_sensor_callback_ms`、`unit: ms`、`direction: minimize` |
| `validity_contract` | `mode: tradeoff`、`min_points_per_frame`、`require_finite_points: true`、`threshold_source` |
| `comparison_policy` | `repeats` 至少 2、明确 `min_improvement_fraction`、`max_pair_relative_spread`、`threshold_source` |
| `confirmation` | `repeats` 至少 2 的独立确认 |
| `budget` | 明确 `max_trials`、`max_seconds`、`trial_timeout_seconds` |

质量底线、最小改善和允许波动来自用户/已批准实验依据；不补“通用 5%”、不从一次试跑倒推最有利阈值。缺阈值来源时，先准备可核对的条件与缺失项，再只澄清会改变判断的值。预算须覆盖 baseline/candidate 的独立重复与确认；不够就报告预算不足，不能用同一 trial 的多个帧伪装成独立重复。

`tick_to_sensor_callback_ms` 取同一帧的 tick 起点与 callback 接收时刻，trial 内聚合后再跨独立 trial 比较。该量是本机软件路径延迟代理，不能写成 GPU 执行时间、真实传感器延迟或端到端应用延迟。点数/有限坐标底线不证明几何、检测性能或语义等价；缺少 geometry oracle 时拒绝 `semantic_preserving`。Tradeoff 的 keep/推荐仅对已声明 workload、阈值和延迟代理成立。

## 执行与报告

先运行 `carla-agent research validate --plan plan.json`：只读 plan/profile，规范化路径并校验研究前提与 schema，返回选择轮数、确认轮数和最坏轮数预算是否足够；不连接 CARLA、不创建 run、不验证实时能力。预算数量充足不保证 wall time 足够；`simulator_checked:false` 明确保留。校验不会替用户补阈值或改变计划。

从实际 schema 读取研究请求结构。Start/resume 前核实 profile 的 `server_pid`、client/server version、地图、episode identity 与独占使用条件；身份不匹配就保留记录并报告阻塞，不自动接管另一实例。每次实验必须复用 `capture.run` 等已有操作；recipe 不允许 shell 片段、任意 Python 或无限重试。

预算应包括轮数/参数候选、每轮 frames/warmup、超时与总量限制，具体名称按当前 schema。明确停止条件：预算耗尽、用户停止、能力缺失、身份变化或不可恢复错误。失败轮次保留 error code、阶段和已产生证据；不能丢弃失败只报告最佳成功样本。

Status/report 必须从持久记录读取，区分 running、stopped、failed、completed 等实现真实返回状态。Stop 请求发出不等于 worker 已停止或资源已恢复；报告当前观测，必要时用原研究 status 再核实。Resume 延用原记录和剩余预算，不把重复执行算作新证据或重置预算。

报告包含原始问题、实际条件、执行/失败轮数、观测结果与对应产物、清理结果、仍无法下结论的部分。给出最接近问题的一组真实对照；数据不足、能力缺失或所有轮次失败就写未得结论，不生成貌似完成的最优参数。教学研究按 [教学参考](carla-learning.md) 展示真实样例，保留用户预测与实际差异。

`carla-agent research compare --run /absolute/run` 只读终态产物，读取既有 writer lock，与写入者互斥，不创建锁或改 state/events/report。server 已停止也可复核；COMPLETED 要通过冻结输入、逐轮产物和最终结果核验，其他终态保留 incomplete/not_evaluated。活跃 run 使用 status，不因 compare 拒绝而自动 stop。独立 capture、旧 metrics 或任意表格不是当前研究 run，不能通过补写 state 文件使其通过。

独立 benchmark 采样复用 capture.run；正式配对 trial 只能由控制器组织。目前没有独立 benchmark CLI 或通用跨 sensor 研究接口。控制器仍未证明完整 scene/weather/seed provenance，现有门槛只对记录的 workload 与观测范围有效。
