# 工程操作：sprint42 执行与证据边界

适用于工程 skills。先遵守 [共享规则](carla-agent-shared.md) 的 CLI/原生操作、实例独占、lease、episode 与有界恢复约束；工程技能不绕过共享执行层拒绝。源码依据固定为 CARLA `sprint42@2075f526dec86362fe058a6fff939e6832876759`；各 skill 的 Source 路径相对用户选定的 CARLA checkout，不是插件目录。本插件没有工程 CLI；`operations: ''` 表示不能构造 `carla-agent <工程命令>`。`native-api` 表示原生 UE/Python 操作路径存在；`conditional` 表示需先补齐所列条件；`workflow` 表示编排现有工具或开发步骤，均不代表已在当前设备实机验证。

## 定位与授权

先确定用户的 CARLA checkout、实际分支、UE fork 路径、Content 来源、Build 目录与目标 Python；不要从插件仓库执行 CARLA 命令。示例中的 `CARLA_ROOT`、`UE_ROOT`、`BUILD_DIR`、`PYTHON`、`PACKAGE_ROOT`、`RPC_PORT` 均为本任务核实的值；源码命令使用相对路径时先进入 `CARLA_ROOT`。`git -C "$CARLA_ROOT" rev-parse --show-toplevel` 和 `git -C "$CARLA_ROOT" worktree list` 用于核实 checkout。不得把个人机器路径写成运行依赖。

只读诊断不隐含安装、下载、configure、编译、cook、启动、修改资产或发布授权。只有用户明确要求构建 Editor/运行 lunch.sh，才进入 `carla-build-editor`；只有明确要求 Shipping/package.sh，才进入 `carla-build-shipping`。需要 Content 的编译、打包和运行必须在含匹配 Content 的正式主 checkout 上；工作树可做源码开发及已授权且不依赖 Content 的检查。只有主分支负责最终打包和发布；打包成功不自动授权发布。禁止为了满足前置而切分支、覆盖脏文件、清理他人产物。

执行前读当前 checkout 的 AGENTS.md 与即将运行的脚本。使用工作树内原有 `build-editor`/`build-shipping` 规则时，只读取其指令并执行实际 shell，不再调用本插件同名 skill 形成递归。本插件正文已包含必要流程，不依赖个人安装的 skill。脚本有清 cache、清 Package、全量依赖或启动副作用时提前列明，保留现有产物并限定目标；不能把 `--skip-prerequisites` 理解成只检查环境。

## 资产与恢复

UE Editor 操作先列出目标 package/level/asset、当前 dirty 状态和预计写入，再在副本或可恢复版本中操作。不要全工程 save-all 夹带他人编辑。对于原生方法内部会保存其他 dirty packages 的情况，先隔离 Editor 会话；无法隔离时只交付操作方案和阻塞点。产物失败可能已经部分写入；按本任务实际写过的路径恢复备份，禁止清空 Content、Saved 或 Intermediate 作为通用修复。CLI 返回 0 不能替代读取输出文件/UE 日志；UE 函数声明存在不能替代资产或插件已安装。

报告只承诺已取得的层：源码接线 → 配置 → 编译 → Editor/运行 → 产物 → 分发。地图 cook 不等于独立地图包；factory 列表变化不等于已保存且运行时可发现；cluster 通信不等于完整多机调度；协议发出不等于 peer 收到。
