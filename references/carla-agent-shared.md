# CARLA Agent 共享规则

适用于本插件所有领域 skill。此文件是连接配置、权限边界、输出解释的单一来源。命令的实时 schema 是字段与限制的最终依据；下文不替代 schema。

## 调用与配置

先用 `carla-agent --help` 确认安装，再读目标操作 schema；不靠记忆猜参数。

```bash
carla-agent schema world.inspect
carla-agent world inspect --profile profile.json --params '{}'
```

原子操作通用形式：`carla-agent <domain> <action> --profile PROFILE --request REQUEST.json`。`--request` 文件内容是该操作的参数对象，不含外层 `operation/profile/parameters`。小请求也可用 `--params '{...}'`；二者不同时传。Research 使用 plan/run 文件接口，见 [研究参考](carla-research.md)。需要保存证据时按实际 `--help` 选择输出选项，不编造 flag。路径作为独立 argv 传递，不拼接 shell；recipe 和 profile 不接受 shell 命令。

Profile 由用户提供或根据其明确环境配置：`schema_version: 1`、匹配 CARLA wheel 的绝对路径 `client_python`、绝对路径 `output_root`；连接可配置 `host`、`port`、`timeout_seconds`。默认连接 `127.0.0.1:2000`，超时 10 秒。`session_policy` 为 `inspect_only` 或 `exclusive`；`expected_server_version` 对变更操作必需。`capability_profile` 为 `standard` 或 `custom-mems`；研究还要求 `server_pid`。未知字段会被拒绝；用 profile/schema 的实际验证结果定位问题，不修改解释器全局安装来碰运气。

CLI worker 借用已运行的 CARLA server，不自动启动、构建、打包、切换地图或结束该进程。用户请求实例生命周期时转 `carla-server`，工程构建转对应 build skill。连接失败时报告缺失项、原始错误与可核实的下一步；不自动找进程杀端口。

## CLI 与原生操作

领域 skill 的 `metadata.execution` 表示主要执行路径：`cli` 为已有命令，`native-api` 为匹配版本的 PythonAPI/Editor/工程脚本流程，`conditional` 表示还需构建、资产或外部组件，`workflow` 组合其他操作，`alias` 仅做旧入口路由。它不表示整个领域已自动化或已实机通过。`operations` 只列现有 CLI 操作；先查 schema，再按该 skill 的任务范围调用。

没有 CLI 封装的能力，可以使用该 skill 引用的 sprint42 原生接口。先核对源版本、实际方法签名/blueprint 和依赖，再把输入、输出、状态影响、失败恢复写进一个有界脚本；不得把源码存在写成当前服务端支持。只读请求不执行变更。条件缺失时保留明确缺口，不用名字相似的接口替代。

原生变更脚本必须在用户授权的专用实例上独立拥有完整生命周期：记录 server/version、episode、原 settings 与自建 actor，设置超时/步数，`try/finally` 清理自有资源并按身份核验恢复。运行前核实没有活跃 CLI/research lease；不能与 CLI session 混用、操作其 actor 或编辑 lease 文件。无法确认实例独占时仅做只读准备。以 CLI 开始的流程继续走同一执行层，不能用原生脚本绕过 `actor_not_owned`、`episode_changed` 等拒绝。

加载/重置世界会改变整个 episode，需明确用户意图与专用实例；保存旧地图名不能保证恢复旧 actor 状态。外部动力学未暴露恢复接口时，不虚构 disable 方法；停止自有流程并报告实际恢复范围。工程脚本可能包含 clone、删除 cache、编译、安装或启动等多步，先检查真实步骤，不因脚本名为 setup/launch 就隐式执行全部动作。

## 只读与变更

| 只读操作 | 会改变仿真状态的操作 |
|---|---|
| 以 `schema` 返回的 `mutates_world: false` 为准，包括连接/世界/blueprint/actor/sensor 查询 | 会话、生成/销毁、挂载、控制、推进与采集以各 operation schema 为准 |

只读操作无需为了“准备环境”打开 session。用户问世界、传感器或蓝图信息时，只读结果足够就结束，不顺手采集。Research 的 start/resume 组合执行变更；status/report 读记录；stop 请求停止并可能执行自有资源清理，因此也需绑定原研究身份。

用户明确授权的实验范围可覆盖所需变更，无需每条命令重复确认；只有“看看/解释/诊断”不授权 spawn、tick、改同步模式或 capture。缺授权时完成可用的只读取证，再说明缺失决定。`exclusive` 配置是技术前提，不能替代用户授权。

变更前核对目标 server/version、地图与独占使用条件；用 `session.open` 获得 `session_id`，后续手工变更传同一 ID。`session.close` 仅删除该 session 拥有的 actor，且只在 ownership 与 episode identity 仍匹配时恢复 settings。禁止操作非自有 actor；世界已变化时，不声称恢复了旧世界或已清理所有资源。`capture.run` 自行管理有界 session，不额外手工打开 session。

## 输出与证据

检查退出码和 JSON 信封：成功为 `{"ok": true, "result": {...}}`；失败为 `{"ok": false, "error": {"code": "...", "message": "...", "details": ...}}`。错误信封、非零退出或不完整输出都不能写成成功；诊断日志走 stderr。保留失败阶段和实际 error，不将超时改写成“空数据正常完成”。

写入后结果不明时先用原 session/研究记录和只读查询核对，避免重复 spawn 或启动第二项研究。清理失败与实验失败分别报告；不能用成功清理覆盖采集失败。

报告按实际证据限定：schema/本地假客户端测试证明接口行为；`doctor` 证明其观测到的连接层；实际 server 响应与原始帧证明对应运行结果。一次成功不证明用户已学会，不证明物理传感器特性，不证明所有 CARLA 版本兼容。

## 能力与领域路由

- 连接、profile、wheel/version 问题 → `carla-connection`。
- 地图加载/重置 → `carla-world`；道路/Waypoint → `carla-map`；同步与步长 → `carla-clock`；所有权/恢复 → `carla-session`。
- Blueprint → `carla-blueprints`；actor 生命周期 → `carla-actors`；车辆控制/动力学按对应专项分流。
- 传感器类型/属性/数据解释 → 各 sensor 专项；挂载/安装位姿 → `carla-sensor-rig`。
- 有界采集 → `carla-capture`；离线组织/标注 → `carla-dataset`；学习路径 → `carla-onboarding`。
- 实验条件 → `carla-research-plan`；试验执行 → `carla-benchmark`；只读结果比较 → `carla-compare`；候选搜索/预算/恢复 → `carla-parameter-search`。

完整名单和边界见 [sprint42 目录](../docs/skill-catalog-sprint42.md)。旧 `carla-sensors`、`carla-research` 保留为兼容路由，不承接全部领域操作。

标准能力与定制能力分开：RGB 与 RayCast LiDAR 可按实际蓝图检查；MEMS 必须显式选择 `custom-mems` 并观察到所需蓝图/属性。MEMS 缺失不能自动降级成 RayCast、换 blueprint 或改假设以凑成功。用户决定换传感器后，作为新条件记录。
