---
name: carla-blueprint-reparent
description: 修复指定目录内 Blueprint 或 AnimBlueprint 的 parent class；仅处理明确父类与命名范围，不扫描修复整个工程。
metadata:
  category: engineering
  execution: native-api
  operations: ''
---

# carla-blueprint-reparent

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：资产目录、已确认的新父 UClass、BLUEPRINT 或 ANIMBLUEPRINT、名称过滤与目标列表。备份目标资产，先手动列出命中项并核对类兼容性。源码的路径构造从 GameUserDeveloperDir 反推磁盘位置，header 提示与默认值不完全一致；按当前项目验证解析出的 FullPath，不能直接相信包含 /Game 的注释。

在 Editor 使用 `ABlueprintParentClassFixer` utility actor，设置 `ClassToFix`、`NewParentClass`、`PathToSearchClassOn`（必须以 `/` 结尾）与非空 `ContainsStringCondition`，只对批准的窄目录调用 CallInEditor `FixBlueprints()`。过滤为多个 substring 的 OR；任意匹配就改，空过滤实际不会执行修改，不代表零资产需要修复。父类修改通过 `ParentClass=...`、CompileBlueprint(SkipSave)、RefreshAllNodes、MarkBlueprintAsModified 完成。

此工具只标脏，不保存；输出应分别记录命中、编译错误和未保存状态。先检查每个 Blueprint/AnimBlueprint 的编译结果、父类、组件与动画引用，再仅保存目标 assets、重载回读。源码先检验新建临时 BP 指针后再 Cast 已加载 Obj，缺少充分 cast 检查；遇无法加载或类型异常的资产不要批量继续，应缩小范围先修源/资产。

产物：实际改过的 asset list、前后父类、编译/保存/重载结果。失败恢复本次副本/版本，不能全工程 reparent 或 save-all。

路由：车辆注册 → `carla-vehicle-assets`；新 C++ 类型 → `carla-actor-extension`；Editor 缺失 → `carla-editor-launch`。

Source：`Unreal/CarlaUnreal/Plugins/CarlaTools/Source/CarlaTools/Public/BlueprintParentClassFixer.h` 及 `Private/BlueprintParentClassFixer.cpp`。
