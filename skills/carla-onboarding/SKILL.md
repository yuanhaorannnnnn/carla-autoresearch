---
name: carla-onboarding
description: 带新手按具体目标学习 CARLA，从真实连接、世界观测到一次有界操作并解释结果；用于入门、理解仿真时间或认识传感器。普通任务直接使用领域 skill，不强制上完整课程。
metadata:
  category: learning
  execution: workflow
  operations: connection.doctor,world.inspect,blueprints.list,sensors.describe,world.tick,capture.run
---

# 用实际结果入门

读[教学参考](../../references/carla-learning.md)和[共享规则](../../references/carla-agent-shared.md)，先选用户要理解的一个对象。

| 学习目标 | 最短路径 | 可判断的结果 |
|---|---|---|
| 能否连接当前平台 | [connection](../carla-connection/SKILL.md) → [world](../carla-world/SKILL.md) | 真实 client/server version、地图、frame/time；失败则解释缺哪层依赖 |
| 世界时间如何推进 | world inspect → [clock](../carla-clock/SKILL.md) | 同一 episode 中预测与实际 frame/time 的变化；仅有授权时有界 tick |
| 什么能生成 | [blueprints](../carla-blueprints/SKILL.md) → 专项属性 | 实际 blueprint、可改属性及其单位，不猜车辆/传感器 ID |
| 如何看到图像/点云 | [RGB](../carla-camera-rgb/SKILL.md) 或 [raycast](../carla-lidar-raycast/SKILL.md) → [capture](../carla-capture/SKILL.md) | 一段真实文件、frame/timestamp 和清理结果 |
| 如何做一次对照实验 | [research-plan](../carla-research-plan/SKILL.md) → [benchmark](../carla-benchmark/SKILL.md) | 变化项、保持项、观测代理及结论适用范围 |

每轮只增加能解释当前问题的一步。先陈述预测，再展示实际结果；没有用户预测时不能伪造回答。命令完成只证明操作完成，“已理解/能独立复现”需要用户解释或实际复现反馈。

失败对照使用真实存在的缺 blueprint、版本不匹配或采集超时；不为了课堂效果制造故障。用户只想了解概念时，以当前只读输出说明即可，不自动生成车辆或开始研究。
