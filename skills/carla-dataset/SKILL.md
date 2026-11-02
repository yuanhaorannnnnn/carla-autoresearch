---
name: carla-dataset
description: 将已有 CARLA capture 原始文件、帧身份、标定和真值组织成可追溯数据集，检查配对与缺失；用于离线导出或整理训练样本。不会为了补数据自动运行仿真。
metadata:
  category: data
  execution: workflow
  operations: ''
---

# 采集产物到数据集

先读[共享规则](../../references/carla-agent-shared.md)。这是离线组织流程，当前 CLI 没有 `dataset export` 命令，也没有内置 KITTI/COCO 转换器。目标格式决定标签、坐标和单位；需求没有指定格式时先产出保留原信息的 manifest，不宣称兼容某个训练框架。

输入必须来自可定位的 capture manifest 和原始文件。检查 `capture.json` 的请求、实际 frames、sensor ID/blueprint、frame/timestamp、编码、尺寸/stride、清理与错误记录。以 manifest 引用为准，不按文件名排序推断帧对应。缺少格式字段时回到对应 [sensor 专项](../../docs/skill-catalog-sprint42.md)，不要猜数据布局。

- 关联主键保留 episode、sensor identity、frame 和 simulation timestamp。不同 episode 的同号 frame 不是同一帧；接收时间不能替代仿真时间。
- 图像、点云、标签各自记录编码与单位；相机内参、父对象相对外参、采样时世界位姿须区分。未保存的动态外参不能从当前 actor 姿态补写成历史值。
- RGB 不自带类别/实例标签。语义/实例图用对应 camera 的契约；全局 actor 真值由 [ground-truth](../carla-ground-truth/SKILL.md) 提供。2D bbox 投影还要相机内外参、可见性和裁剪规则，不能仅凭 3D bbox 宣称检测标注正确。
- 连续帧 sensor 检查重复/缺帧；低频 sensor 按采样周期配对；事件流允许空事件集合。写出 missing/unmatched/invalid 清单，不悄悄删除失败样本。

输出到新的目录，原始采集保持只读；写 schema version、转换版本、源文件路径/摘要、过滤与坐标转换规则。检查输出条数与索引引用，错误时保留未完成状态而不覆盖原数据。新采集需转 [capture](../carla-capture/SKILL.md)；性能/质量对比转 [compare](../carla-compare/SKILL.md)。

输入格式依据：`src/carla_agent/worker.py` capture manifest 与原始帧输出；不同 sensor 的 schema 见各专项。此 skill 不把文件完整性当作标注准确率证据。
