# Progress

## 2026-03-25

- Fixed conversation id to `autoresearch` for future planning artifacts.
- Created failing tests for CARLA path defaults, command generation, metrics parsing, decision logic, and TSV results writing.
- Added initial `carla_autoresearch` package with controller, benchmark client, and experiment entrypoint.

## 2026-03-26

- 完成真实联调第一轮排查，确认：
  - 直接在 agent 当前 shell/PTY 中运行 CARLA 链路不可靠
  - 在真正的新桌面终端中运行服务端与客户端，并在客户端先激活 `py38`，链路可用
- 完成点数一致性复测，保存了逐帧 `point_count` 数据供人工核对，并在正式 `benchmark_client.py` 路径下确认过一次 `point_count_all_equal=true`
- 删除根目录 legacy planning 文件，仅保留 `.planning/conversations/autoresearch/`
- 为这次会话额外保存了 `.agent-state/conversations/autoresearch.md`
- 将多条流程 guardrail 写入 `.agent-state/rules/mistakes.md` 和 `docs/agent-system/mistake-patterns.md`
- 将性能优化改动切换到 `CarlaUE5` 的新分支 `feature/carla-lidar-optimization`
- 落下第一轮最小性能补丁：
  - `RayCastSemanticLidar::SimulateLidar` 外提 `HorizontalFov`、`HalfHorizontalFov`
  - 外提 `ActorTransform`、`LidarBodyLoc`、`LidarBodyRot`、`Range`
  - `ShootLaser` 改为接收这些预计算参数，减少每条射线中的重复读取
- 将 `runs/retest-20260326-102715/metrics.json` 作为基线，与 `runs/test-20260326-124609/metrics.json` 对比：
  - `scan_latency_ms_median` 从 `72.361193` 降到 `47.956637`
  - `point_count_all_equal` 在两次 run 内都为 `true`
  - 当前可把第一轮补丁暂定为 `opt1 keep`
- 调整 `autoresearch` 控制器：
  - 支持 `--reuse-existing-server`
  - 服务端/客户端流程与文档入口对齐
  - `package` 流程改为 launcher `.sh` 方案，并在 `py38` 环境里运行
- 当前轮次临时退化工作流：
  - 用户手动执行 `package`
  - 助手在其后接手测试与 benchmark
- 第二轮优化开始前，用户明确要求：
  - 每一轮优化无论成功还是失败，都必须记录到 planning / 文档
  - 分支名保持不变，但会话与 planning 命名统一为 `autoresearch`
- 已验证 `gnome-terminal -- bash <launcher.sh>` 这条路径可稳定执行并写出标记文件，因此第二轮开始恢复全自动流程：
  - `package` 由助手自动执行
  - 之后继续由助手自动执行服务端/客户端测试
- 第二轮全自动实验 `runs/opt2-20260326-130118/` 首次失败：
  - `build.exitcode=1`
  - `build.log` 未生成
  - 根因已定位为 launcher 中使用相对路径，脚本 `cd /media/yhr/2T/CarlaUE5` 后重定向目标 `runs/.../build.log` 失效
  - 已修复为在 build/server/client launcher 中统一使用绝对路径
- 第二轮全自动实验重试 `runs/opt2-rerun-20260326-130315/` 再次失败：
  - 仍然只有 `build.exitcode=1`，没有 `build.log`
  - 根因继续缩小为 launcher 中使用 `source "$(conda info --base)/etc/profile.d/conda.sh"`，在 `gnome-terminal` 拉起的裸 shell 中 `conda` 命令本身未必已可用
  - 已修复为直接使用绝对路径 `/home/lkshpc/anaconda3/etc/profile.d/conda.sh`
- 继续用 `bash -x` 直接跟踪 launcher 后，定位到更深一层根因：
  - `set -u` 与 conda activate hook 不兼容
  - 具体在 `/home/lkshpc/anaconda3/envs/py38/etc/conda/activate.d/libblas_mkl_activate.sh` 触发 `MKL_INTERFACE_LAYER: unbound variable`
  - 已将 launcher 头部从 `set -euo pipefail` 改为 `set -eo pipefail`
- 第二轮全自动实验重试 `runs/opt2-rerun-20260326-130658/` 进展：
  - `package` 已成功完成
  - 新的 `CarlaUnreal` 服务端已自动启动并进入 `EmptyGround`
  - benchmark 阶段失败在 `benchmark_client.py` 的 `client.load_world("Town05")`
  - 客户端错误为 `RuntimeError: std::exception`
- 对该失败做最小客户端探测后确认：
  - 在正确环境里，独立的 `get_world()` 成功
  - 独立的 `load_world("Town05")` 也成功
  - 更可能的根因是全自动流程里服务端刚拉起就过早启动 benchmark，客户端在 server ready 之前切图
  - 已修改自动化逻辑：`launch_server()` 不再只等新 pid，而是同时等待 `server.log` 出现 `Initialized CarlaServer` 与 `LoadMap Load map complete`
