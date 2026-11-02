---
name: carla-walker-pose
description: 读取 CARLA walker 骨骼 world/component/relative transform，设置、混合、显示姿态和采样动画；不负责 AI 导航、过街或行人位置控制。
metadata:
  category: runtime
  execution: native-api
  operations: ''
---

# 行人骨骼姿态

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

读取 `pose=walker.get_bones()`，迭代 `pose.bone_transforms`；每项 `name/world/component/relative` 分别表示不同参考系，不能把 world transform 当输入相对骨骼姿态。保存实际骨名和 frame，不猜骨架层级。

独立原生任务自有 walker 设置 `walker.set_bones(carla.WalkerBoneControlIn([(bone_name,relative_transform),...]))`；输入采用基线 WalkerBoneControlIn 的 `(name,Transform)` 列表。`blend_pose(blend)` 控制 [0,1] 混合，`show_pose()`/`hide_pose()` 切换，`get_pose_from_animation()` 从当前动画采样；不是返回新 actor 或自动播放完整动作。

读回骨骼位置并在需要时采集视觉证据；未知骨名、坐标系错误或动画持续覆盖须定位，不能整副骨架置零“修复”。导航/动画状态会改变后续姿态，先记录采样条件。退出 hide_pose/恢复本任务保存姿态仅在相同骨架有效；完整动画内部状态不能据这些 API 声称已恢复，优先清理本任务 walker。

## 交接与证据

[carla-walker-navigation](../carla-walker-navigation/SKILL.md)；[carla-actors](../carla-actors/SKILL.md)；[carla-ground-truth](../carla-ground-truth/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`、`PythonAPI/carla/src/Control.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
