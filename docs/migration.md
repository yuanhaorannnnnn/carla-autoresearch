# 从 CARLA Auto Research 迁移

开发从 `feature/carla-lidar-autoresearch@1874fe8` 延续，CARLA适配参考
`sprint42@2075f526d`。两者属于不同仓库。原 checkout 文件、既有 Git 历史和
README/program 未提交修改保留；GitHub 默认分支名称保持，开发预览以正常快进更新。

| 旧位置 | 新位置/处理 |
|---|---|
| 原训练脚本、Notebook、Torch依赖、uv.lock | `legacy/training/`，内容原样保留 |
| 原 controller/benchmark/loop/shell | `legacy/carla-v0/carla_autoresearch/`，历史参考 |
| 原 CARLA 测试 | `legacy/carla-v0/tests/`；agent 工作上下文仅留本地与既有 Git 历史，不再次分发 |
| 本机 README/program 未提交正文 | 原工作区保持，迁移副本仅作本地备份，不随公开仓库分发 |
| 原命令入口 | 显式迁移响应；不使用作者默认路径或隐式构建 |
| 公共工具与协议 | `src/carla_agent/`，独立于 CARLA wheel 的控制器 |
| 新技能 | 根 `skills/`，相对引用 `references/` |

旧 YAML 和 metrics 缺少运行/版本/帧身份，不自动恢复或升级为可信 baseline。
保留旧目录，用新 profile/recipe 重采。旧指标 `scan_latency_ms_median` 测到
tick→callback，不与其他口径结果混排。

`python -m carla_autoresearch.experiment --profile PROFILE --recipe RECIPE` 将
明确的 capture recipe 转交新入口。recipe 文件正文不含外层 `recipe`。
旧 `--headless-build`、`--workspace` 和loop参数返回 `migration_required`；
不支持的参数不会忽略。旧 loop 需转新 research 命令，不恢复不可信身份。
这些兼容入口在开发 checkout 可用；轻量发行包只安装 `carla_agent`。

当前 GitHub 更新公开开发预览的源码、文档和品牌资产；不重命名仓库、不切换默认分支、不代表发行包发布或插件上架。
产品历史继续沿用 CARLA 工具分支，不能使用跟踪 Karpathy upstream 的旧本地 `master` 替换。
仅正式主分支负责产品打包；干净安装与真实演示按 [已记录计划](installation-demo.md) 后续完成。
