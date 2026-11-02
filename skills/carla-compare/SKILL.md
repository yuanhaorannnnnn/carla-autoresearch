---
name: carla-compare
description: 离线比较已有 CARLA 研究 run，核对冻结输入、原始产物与独立配对后重算结果；用于检查改善、波动或证据篡改。不启动仿真、不补跑、不应用获胜参数。
metadata:
  category: research
  execution: cli
  operations: research.compare,research.status,research.report
---

# 只读研究比较

先读[研究契约](../../references/carla-research.md)。输入是现控制器创建的绝对 run 目录，含 manifest、冻结 plan/profile、state、writer.lock 和 trials；独立 capture 目录、旧版本 metrics.json、手写表格不能假装成研究 run。

```bash
carla-agent schema research.compare
carla-agent research compare --run /absolute/run
```

命令只读已结束的 run，不要求 server 在线；读取现有 writer lock 防止与状态写入冲突，不创建锁文件，不写 state/events/report。活跃 run 使用 `research status` 看进度；compare 拒绝运行中状态，不能为比较自动停止研究。

完成 run 会核对冻结 plan/profile 摘要、trial 身份/计划、原始产物摘要及原始测量，再复用原比较逻辑。文件缺失或变更时保留错误；不能改回摘要让检查通过。非完成的终态保留失败/停止/预算状态，并展示可核验的配对事实；整体保持 not_evaluated，不把已完成的一部分候选当完整最优结论。

解释结果要分开 execution、validity、verdict。eligible 只是满足选择阶段条件，keep 还需独立确认；inconclusive 反映波动或证据不足。结论限定在该 binary/workload、有限坐标/点数底线和回调延迟代理，不证明几何等价、真实设备精度或源码构建归因。

对普通离线数据的描述统计可以另做明确标注的分析，但不能冒用本命令的完整研究验收结论。需要补跑或新候选时转 [research-plan](../carla-research-plan/SKILL.md)/[parameter-search](../carla-parameter-search/SKILL.md)，保留原 run 不修改。

依据：`src/carla_agent/research.py` compare/_verify_completed/_verify_final/_decision。
