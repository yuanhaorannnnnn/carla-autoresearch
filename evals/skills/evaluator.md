# 独立技能行为评估

这些 cases 是合成环境的行为评估素材，不是 CARLA runtime 证据，也不是措辞匹配测试。

每轮给独立 evaluator 一个 case 的 `request`、`fixtures`、全部可发现 skill 的 name/description，以及被选中 skill 的正文和链接 reference。先隐藏 `rubric`，不要告诉 evaluator 应选哪个领域、预计失败点或作者修复意图。对 CLI 只使用隔离 fake adapter：按 fixtures 返回预置结果，记录 operation、参数、文件访问及 stdout/stderr；不得连接真实 server 或执行真实变更。当前接口 schema 应取自同版 `carla-agent schema`，不从本文猜字段。

运行后由独立 judge 结合完整动作 trace、产物和最终回答，对 rubric 每项标 pass/fail/insufficient-evidence，并引用具体动作或数据。所有必需行为成立且没有 forbidden action 才算该 case pass。只匹配关键词、SKILL.md 标题或最终回答措辞不能判定通过；工具没有输出或记录不完整时标 insufficient-evidence。

每 case 单独保存：插件 revision、实际加载的 skills/references、case ID、fake adapter 版本、动作 trace、判断与证据。别将预置失败响应当成实际 CARLA 错误。先执行一次独立 forward-test，只有确有行为问题时再改技能；文本 quick_validate 通过不替代这一步。
