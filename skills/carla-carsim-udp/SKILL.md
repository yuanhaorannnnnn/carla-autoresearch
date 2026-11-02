---
name: carla-carsim-udp
description: 配置 CARLA CarSim UDP peer IP/port、substep 与状态回传；用于该专属外部动力学协议接入，须核对 peer、构建和报文，不与其他 UDP 后端混称。
metadata:
  category: runtime
  execution: conditional
  operations: ''
---

# CarSim UDP 动力学

先读 [共享规则](../../references/carla-agent-shared.md)；原生 API 分支按 [连接、独占生命周期与证据约定](../../references/runtime-native.md) 执行。metadata 是主要操作路径，不表示全部能力均已封装。

先核对 wheel 的 `enable_carsim_udp_physics`、server 对应组件与外部 peer 版本、IP/port、socket 拓扑和专属报文定义。只观察 socket 可用不能证明状态映射正确；不发送猜测探测包。这是外部 CarSim peer 协议，不使用插件 simfile 路线，也不借由端口可达宣称 CarSim 接通。

独立原生任务创建自有车辆，`vehicle.enable_carsim_udp_physics(max_substeps=n,max_substep_delta_time=dt,ip=peer_ip,port=peer_port)`；n/dt 正值、port 为明确目标端口。组件内包含单位/坐标转换与运动状态写回，运行前逐项核对报文字段顺序、字节宽度、端序、坐标和时间基准，记录源版本；此 skill 不虚构统一 wire schema。

以有界 handshake/状态接收窗口观测 server 日志、收发计数和车辆 frame/位姿，区分无包、畸形包、旧包、peer 发错坐标与运动控制竞争。超时停止本任务，禁止不断重启/占用同一 socket；不要重置其他用户 peer。

内部 DisableCarsimUdpPhysics 名称即使复用也不表示协议相同；Python 没有公开对应 disable/restore 绑定。结束清理本任务车辆并必要时重建默认后端；未能确认恢复就报告未恢复，不以无异常当作模型切换成功。

## 交接与证据

[carla-vehicle-control](../carla-vehicle-control/SKILL.md)；[carla-vehicle-physics](../carla-vehicle-physics/SKILL.md)；[carla-clock](../carla-clock/SKILL.md)；[carla-actors](../carla-actors/SKILL.md)。

基线 `sprint42@2075f526dec86362fe058a6fff939e6832876759`；源码相对 CARLA 根：`PythonAPI/carla/src/Actor.cpp`、`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Vehicle/MovementComponents/CarSimUdpComponent.cpp`。本文依据源码绑定，未执行 CARLA 实机验证；wheel、server、资产和外部依赖是否支持仍需现场检测。
