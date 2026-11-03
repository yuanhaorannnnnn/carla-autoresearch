# CARLA Agent：sprint42 skill 清单与边界

日期：2026-11-02。CARLA 基线：`sprint42@2075f526dec86362fe058a6fff939e6832876759`。

本目录的粒度已获用户批准，并已落实为领域 SKILL.md。源码证据说明对应能力在哪里；实际 CLI 封装、原生流程和条件缺口由各 skill metadata、共享规则及实时 schema 区分。编写技能没有运行其描述的 CARLA/Editor/构建操作。

下文源码位置相对于匹配 `sprint42@2075f526dec86362fe058a6fff939e6832876759` 的 CARLA 源码根目录；插件路径相对于本仓库根目录。不得把上游同名接口直接当作此定制基线的实现。

已落实 **107 个领域/组合 skill + 2 个旧名兼容路由**，另有 **4 个外部接入预留**未创建空壳 skill。完整指引覆盖不等于 107 项 CLI 自动化或实机验证；当前基础工具层为 17 个原子 operation。离线索引通过 `carla-agent skills list/show` 查询，未安装或发布。

| 能力组 | 数量 | 查阅位置 |
|---|---:|---|
| 连接、世界、地图、actor | 15 | 下文运行时第一表 |
| 车辆控制、动力学、工程车辆 | 14 | 下文运行时第二表 |
| 行人、交通、环境、真值、显示 | 15 | 下文运行时第三表 |
| 传感器 | 25 | 9 camera + 5 LiDAR + 3 radar + 8 其他专项 |
| 环境、构建、运行实例 | 10 | 工程第一表 |
| 资产、地图制作、扩展开发 | 17 | 工程第二表 |
| 原生插件协议及条件集成 | 3 | cluster、debug-port、ROS2 native |
| 采集、数据集、入门、Auto Research | 8 | 插件组合层 |
| 外部接入预留（单列） | 4 | ScenarioRunner、Leaderboard、ROS bridge、SUMO |

## 拆分规则与调用关系

一个 skill 对应一个能独立完成的专业任务：有自己的配置或数据契约、操作路径和失败判断。它可以包含多个原子命令。单个属性、CRUD 方法、型号预设、序列化工具不再各建 skill。

所有 skill 采用同一结构：适用请求、前置能力、原子操作、输入输出、状态影响、失败恢复、相邻 skill 路由、源码与版本依据。领域 skill 负责专业知识；共享执行层负责连接、错误、资源所有权和命令协议；workflow 只组合这些操作。

```text
用户请求 → 领域 skill / workflow skill
                ↓
        共享原子操作与 schema
                ↓
       CARLA worker / 工程工具适配器
                ↓
             sprint42

Auto Research → 同一操作层 → 固定实验条件、采集、比较、恢复
```

证据标记：**S**＝sprint42 源码/绑定存在；**C**＝依赖编译选项、外部组件或资产；**L**＝旧路径/示例与现基线不一致；**P**＝插件组合/开发职责。S 只表示静态证据；操作封装状态看各 skill 与 schema，不按现有 RGB/LiDAR 采集覆盖裁剪专业知识。

## 运行时、场景、交通与车辆

源码缩写：`P/`＝`PythonAPI/carla/src/`；`N/`＝`PythonAPI/carla/agents/navigation/`；`U/`＝`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/`；`L/`＝`LibCarla/source/carla/`。

### 连接、世界、地图与 actor

| 建议 skill | 负责什么 | 边界与交接 | 源码依据 |
|---|---|---|---|
| `carla-connection` | profile、Python API/服务端版本、timeout、ready、连接诊断 | 服务器进程生命周期交 server；world tick 交 clock | S：P/Client.cpp:340,378；插件已有 doctor |
| `carla-session` | 独占会话、保存 settings、资源所有权、episode 身份、关闭恢复 | 复用连接；不接管或销毁其他用户资源，不代替进程管理 | P：插件 docs/implementation-contract.md 的 session.open/close |
| `carla-world` | 地图列表、load/reload/unload、加载状态、reset_settings、地图层 | ODR 生成交 opendrive-world；时间策略交 clock | S：P/Client.cpp:346,351；P/World.cpp:470,518 |
| `carla-clock` | sync/async、fixed delta、substep、tick/wait/callback、free tick、secondary tick、pause/resume/debug_step | 唯一 tick owner；TM 同步须联动，回调数据齐备交 capture | S：P/World.cpp:287,495,542；P/Client.cpp:375 |
| `carla-runtime-assets` | 文件基目录、required files/request file、import_asset、static mesh 检查 | 运行时资产传输；UE 资产制作/cook/package 交工程层 | S：P/Client.cpp:347,380 |
| `carla-map` | spawn points、Waypoint、road/lane/s、topology、junction、crosswalk、坐标地理转换、地图导出/缓存 | 路线搜索交 route-planning；动态信号控制另项 | S：P/Map.cpp:131,162 |
| `carla-map-landmarks` | 地图标志 ID/类型/朝向/有效车道/分组、沿 Waypoint 查询、映射到运行时标志 | 静态道路语义；灯态/相位交 traffic-signals | S：P/Map.cpp:143,184,195；P/World.cpp:524 |
| `carla-opendrive-world` | ODR 导入/生成、map_name/map_type、生成地图查删、程序化树木/建筑、默认相位表 | 已有地图加载归 world；OSM 转换另项；旧 config.py 参数不适用 | S/L：P/Client.cpp:334,354 |
| `carla-osm-conversion` | OSM→ODR、投影/偏移/居中、道路过滤、车道宽、高程、信号生成规则 | 转换结果交 opendrive-world；不能据转换成功宣称道路运行正确 | S/C：P/OSM2ODR.cpp:36；P/PythonAPI.cpp:54 |
| `carla-route-planning` | 道路拓扑采样、建图、A*、换道连接、RoadOption 路径 | 不驱动车辆；交 navigation-agent 或 TM | S：N/global_route_planner.py:19,84,124,223,287,326 |
| `carla-navigation-agent` | Basic/Behavior/ConstantVelocity、destination/global plan、local planner、PID、run_step/done | 客户端闭环；与服务端 TM 和手动控制划清接管权 | S：N/basic_agent.py:22,141；N/local_planner.py:192,297；N/controller.py:15 |
| `carla-blueprints` | 筛选、属性类型/推荐值/可修改性、合法生成参数 | 专项 sensor 属性由对应 skill 解释；UE 蓝图制作另项 | S：P/Blueprint.cpp:58 |
| `carla-actors` | spawn/try_spawn、parent/attachment、查找、alive/active/dormant、destroy | 通用身份与生命周期；运动/控制/传感器输出分流 | S：P/World.cpp:278,332,483；P/Actor.cpp:177,232 |
| `carla-actor-batch` | 批量命令、SpawnActor.then/FutureActor、逐项 Response/error、do_tick、部分失败处置 | do_tick 必须经 clock 的 tick 所有权检查/协调；复用业务 schema，不假定批操作原子回滚 | S：P/Commands.cpp:60；P/Client.cpp:373 |
| `carla-actor-motion` | transform/velocity/acceleration、恒速/恒加速度、力/冲量/扭矩、重力/碰撞/物理开关 | 车辆模型参数交 vehicle-physics；道路轨迹控制另项 | S：P/Actor.cpp:207 |

### 车辆控制、动力学与工程车辆

| 建议 skill | 负责什么 | 边界与交接 | 源码依据 |
|---|---|---|---|
| `carla-vehicle-control` | VehicleControl、油门/制动/转向、user/local control、控制值回读 | 与 Ackermann、轨迹、TM、外部模型明确唯一控制源 | S：P/Actor.cpp:285,298,325；P/Control.cpp:291 |
| `carla-ackermann-control` | Ackermann 输入、横纵分控、速度/加速度 PID 配置和回读 | 普通踏板与轨迹协议各自负责 | S：P/Actor.cpp:294,310；P/Control.cpp:363 |
| `carla-trajectory-control` | DriverControl/ValidFlag、Trajectory 点列、plan points、user trajectory、body parameters、world batch | TM route、导航路径不是该协议；perfect backend 另项；不同入口输入类型分开 | S：P/Actor.cpp:47,67,297,326；P/Control.cpp:312,458；P/World.cpp:172,543 |
| `carla-vehicle-physics` | Chaos/轮胎/悬架/传动/质心 PhysicsControl、车轮角、RPM、failure、telemetry | 不能将默认物理参数强套外部模型 | S：P/Actor.cpp:303,313,324,335；P/Control.cpp:483 |
| `carla-vehicle-accessories` | 车灯、车门、镜面、方向盘视觉角、灯态查询 | 场景照明和道路信号各有 owner | S：P/Actor.cpp:236,300,339；P/World.cpp:473 |
| `carla-carsim` | plugin CarSim、simfile、道路模型、运动组件切换/恢复 | 依赖 CarSim 安装/构建；UDP 版本独立 | S/C：P/Actor.cpp:318；U/Vehicle/MovementComponents/CarSimManagerComponent.cpp:18,113 |
| `carla-chrono` | vehicle/powertrain/tire JSON、base path、substep、地形、组件切换 | 依赖 Chrono 和模型资产；不管理其他动力学后端 | S/C：P/Actor.cpp:320；U/Vehicle/MovementComponents/ChronoMovementComponent.cpp:21,142,285 |
| `carla-carsim-udp` | CarSim peer IP/port、substep、报文与运动状态、切换/恢复 | 外部 peer 协议和运行依赖；不能与 plugin CarSim 混称 | S/C：P/Actor.cpp:321；U/Vehicle/MovementComponents/CarSimUdpComponent.cpp:20,185,325 |
| `carla-simulink-udp` | Simulink peer、专属报文、状态映射与恢复 | 入口相似不代表与 CarSim/Dspace 报文兼容 | S/C：P/Actor.cpp:322；U/Vehicle/MovementComponents/SimulinkUdpComponent.cpp:21,217,400 |
| `carla-dspace-udp` | `enable_udp_physics` 对应的 Dspace peer、报文、状态写入与恢复 | 不能泛化成任意 UDP dynamics | S/C：P/Actor.cpp:323；U/Vehicle/MovementComponents/DspaceUdpComponent.cpp:23,271,419 |
| `carla-perfect-control` | perfect movement backend、substep、直接状态/轨迹执行、恢复默认组件 | 轨迹数据由 trajectory-control 提供；不宣称动力学真实 | S：P/Actor.cpp:329；U/Vehicle/MovementComponents/PerfectControlMovementComponent.cpp:93,224,576 |
| `carla-semi-truck` | 半挂识别、trailer transform、articulation angle、拖车绑定/安装关系 | 行驶复用 vehicle-control，安装 sensor 复用 rig | S：P/Actor.cpp:336,346 |
| `carla-mining-truck` | 容量、载荷、举升/下降耗时、bucket/overall/driving state、lift/lower | 道路行驶复用车辆控制；挖机操作另项 | S：P/Actor.cpp:351 |
| `carla-excavator` | bucket/load、挖点/卸点、start/stop、矿卡绑定/解绑、装载进度 | 复用矿卡状态，避免再实现矿卡或行驶控制 | S：P/Actor.cpp:381 |

### 行人、交通、环境、真值与显示

| 建议 skill | 负责什么 | 边界与交接 | 源码依据 |
|---|---|---|---|
| `carla-walker-navigation` | WalkerControl、AI controller、目标/速度、导航随机点、过街比例/seed | actor 创建清理复用 lifecycle；骨骼姿态另项 | S：P/Actor.cpp:416,428；P/Control.cpp:399；P/World.cpp:475,522 |
| `carla-walker-pose` | 骨骼 world/component/relative、pose 设置/读取/blend、显示、动画采样 | 不负责导航和过街行为 | S：P/Actor.cpp:419；P/Control.cpp:412 |
| `carla-traffic-manager` | TM port/autopilot、sync/seed/hybrid physics、dormant respawn、速度/距离/换道/碰撞/忽略概率/灯态、set_path/set_route 与 buffer/actions | 生命周期、行为和 TM 路径属于同一任务，不再机械拆三项；地图路线搜索另项，信号相位另项 | S：P/Client.cpp:377；P/Actor.cpp:312；P/TrafficManager.cpp:81–112 |
| `carla-traffic-signals` | 路口/ODR ID、状态/倒计时/cycle、影响车道/stop waypoint、相位组表、freeze/reset | 此基线无上游 set_state/set_red_time 绑定；单灯 freeze 实际冻结全部灯 | S/L：P/Actor.cpp:436,467；P/World.cpp:516,524；L/client/TrafficLight.cpp:41 |
| `carla-weather` | rain/fog/wind/sun/dust、雪降水/积雪、环境 lighting gain、预设/启停 | 配置天气；sensor 响应与标定属于各 sensor 专项 | S：P/Weather.cpp:37；P/World.cpp:479 |
| `carla-scene-objects` | 环境对象标签/ID/name/transform/bbox、启停、level BB、static objects | 动态 actor 生命周期另项；射线查询另项 | S：P/World.cpp:323,363,532,538,544；P/Actor.cpp:486 |
| `carla-scene-query` | cast_ray、project_point、ground_projection、带标签 hit | 几何查询不能替代真实 sensor 输出；道路语义查询归 map | S：P/World.cpp:400,535 |
| `carla-scene-materials` | Color/FloatColor texture、像素与材质通道、Actor/object/list 贴图 | UE 材质资产制作归工程；World 旧入口有 deprecated 标记 | S：P/World.cpp:419,546；P/Actor.cpp:77,229 |
| `carla-scene-lights` | LightManager、灯组、强度/颜色/active、批量灯态、日夜循环 | 车辆灯归 accessories，交通灯归 signals | S：P/LightManager.cpp:306；P/World.cpp:530 |
| `carla-recorder` | recorder start/stop/additional data、记录查询、按时间回放、follow/sensor replay、倍速/ignore/keep_actors | 录制与回放为一套文件契约；sensor 原始数据采集仍归 capture；不保证重演完全确定 | S：P/Client.cpp:363–372 |
| `carla-ground-truth` | WorldSnapshot/ActorSnapshot/Timestamp、listen_actors、GroundTruthOutput、OASIS 真值与发布路径 | 与局部 target sensor、OSI 数据分开；标签数据集组织交 dataset | S：P/Snapshot.cpp:31；P/World.cpp:262,337,482,515；U/Sensor/WorldObserver.cpp:396,862,915 |
| `carla-osi` | OSI GroundTruth/TrafficUpdate、对象/道路/逻辑车道/环境映射、protobuf 版本与发布边界 | 不推断全量 OSI 字段均完整；外部接收链需核验 | S/C：P/World.cpp:347,514；U/Sensor/WorldObserver.cpp:653,921；U/Util/OsiWrapper.h:1506,1640 |
| `carla-spectator` | spectator 位姿、ego follow、ego role/reclaim、观察视角 | 不创建用于训练/采集的 camera sensor；窗口设备映射交 display | S：P/World.cpp:476,489,519 |
| `carla-display` | quality、窗口、secondary HDMI/device/Xserver viewport、本地显示配置 | 依赖显示环境/插件；sensor 成像/采集归专项；server 部署另项 | S/C：P/World.cpp:490,503,539；CarlaDisplayUtil/XWindowForCarla 插件 |
| `carla-debug` | DebugHelper 标绘、UE console、主/次服 console、debug mode、命令行诊断 | 调试工具入口；不代替工程调试端口协议，不把任意控制台命令写成已验证操作 | S：P/World.cpp:494,509,520,540,566 |

这里有三类名字相似但契约不同的输入，必须分别记录：`send_user_trajectory` 接收 `list[Trajectory]`；`VehicleBodyParameter` 通过 `update_vehicle_parameter` 更新且源字段为 `vehicle_witdh`；`World.send_trajectory_batch` 接收 `dict[ActorId, DriverControl]`。坐标/几何类型本身放 shared reference，不另造“Vector skill”。

## 传感器：25 个专项 skill

源文件缩写：`Sensor/`＝`Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Sensor/`；`A`＝同插件 `Actor/ActorBlueprintFunctionLibrary.cpp`；`P`＝`PythonAPI/carla/src/SensorData.cpp`；`R`＝`LibCarla/source/carla/sensor/SensorRegistry.h`。

| 建议 skill | Blueprint / 职责 | 边界与交接 | 源码依据 |
|---|---|---|---|
| `carla-camera-rgb` | `sensor.camera.rgb`；内参、畸变、曝光、后处理、像素格式、图像输出 | YUV/镜头/曝光作为本 skill 的参数与参考；深度、事件流另有数据契约 | S：Sensor/SceneCaptureCamera.cpp:28；A:332；P:728 |
| `carla-camera-depth` | `sensor.camera.depth`；深度编码、距离解码与可视化 | 不沿用 RGB 的颜色解释；Linux 材质路径单独说明 | S：Sensor/DepthCamera.cpp:13；P:728 |
| `carla-camera-semantic` | `sensor.camera.semantic_segmentation`；类别标签、调色板、标注输出 | 实例身份交给 instance；标签源与材质属于共享参考 | S：Sensor/SemanticSegmentationCamera.cpp:11 |
| `carla-camera-instance` | `sensor.camera.instance_segmentation`；实例 ID、语义关联、标注输出 | 区分跨帧身份与单帧颜色编码；不替代全局 actor 真值 | S：Sensor/InstanceSegmentationCamera.cpp:15 |
| `carla-camera-normals` | `sensor.camera.normals`；法线编码、方向解释和显示 | 使用颜色图像存储，不能假设存在独立 Python NormalsImage/FloatImage | S：Sensor/NormalsCamera.cpp:11；A:1195；R:88 |
| `carla-camera-optical-flow` | `sensor.camera.optical_flow`；二维流、帧运动、彩色显示 | 不按 BGRA 解码；真值速度归 ground-truth | S：Sensor/OpticalFlowCamera.cpp:17；P:794 |
| `carla-camera-dvs` | `sensor.camera.dvs`；阈值、噪声、不应期、事件时间和极性 | DVSEventArray；空事件集与丢帧分开判断 | S：Sensor/DVSCamera.cpp:40；P:1114 |
| `carla-camera-fisheye` | `sensor.camera.fisheye`；多种投影、k1–k6、cube face、拼接、ImageCube | Kannala_Brandt/Conti/Equidistant/Scaramuzza 是本 skill 的模型选项；语义模式不再单建 | S：Sensor/FisheyeSensor.cpp:145；A:3149；P:776 |
| `carla-camera-stereo` | `sensor.camera.stereo`；基线、左右图、深度/视差、16 bit 输出 | 一组立体结果的内在一致性归本 skill；跨传感器同步归 capture | S：Sensor/StereoCameraSensor.cpp:26；P:758 |
| `carla-lidar-raycast` | `sensor.lidar.ray_cast`；通道、扫描、FOV、dropoff、BRDF、噪声、XYZI | 几何正确性与强度模型分开；不解码 semantic/MEMS 数据 | S：Sensor/RayCastLidar.cpp:68；A:1739；P:811 |
| `carla-lidar-semantic` | `sensor.lidar.ray_cast_semantic`；point、cos_inc_angle、object_idx、object_tag | 不是 XYZI；标签映射交共享真值参考 | S：Sensor/RayCastSemanticLidar.cpp:83；P:828 |
| `carla-lidar-mems` | `sensor.lidar.ray_cast_mems`；CSV 扫描轨迹、运动畸变、beam_index、点与强度 | CSV 资产路径/列格式是显式前置；不同 pattern 为配置，不各建 skill | S/C：Sensor/RayCastMemsLidar.cpp:90,135；A:1863；P:845 |
| `carla-lidar-at128` | `sensor.lidar.at128`；CPU 三组扫描、256 点包、时间/CRC/UDP | CPU AT128 与 GPU AT128 的执行和报文边界不同，分开管理 | S：Sensor/RayCastAT128.cpp:89,117,438；R:103 |
| `carla-lidar-gpu` | `sensor.lidar.sc_lidar`；SceneCapture GPU 路径、数据源、噪声、stream/UDP | mechanical/AT128/M1/Pandar64 是预设；不能虚构 `sensor.lidar.gpu` Blueprint | S/C：Sensor/SceneCapture_Lidar.cpp:183,730,796,907；A:2460；R:111 |
| `carla-radar-raycast` | `sensor.other.radar`；FOV/range/PPS、径向速度、方位/仰角/距离 | 点检测格式；不按目标级 Oasis 格式解码 | S：Sensor/Radar.cpp:22；A:1386；P:896 |
| `carla-radar-oasis` | `sensor.other.radar_oasis`；遮挡、目标数、坐标方向、目标位姿/速度/尺寸/RCS | 目标级雷达数据；不混同 target 真值传感器 | S：Sensor/RadarOasis.cpp:45,91,398；A:1531；P:1029 |
| `carla-radar-mmwave` | `sensor.radar.millimeter_wave`；频率、功率、增益、热噪声、SNR、角分辨率、延迟 | Sensors/FFTW 依赖；当前 ExistenceProbability 常量不能作为已校准置信度 | S/C：Sensor/MillimeterWaveRadarSensor.cpp:58；A:3800；P:1144 |
| `carla-ultrasonic` | `sensor.other.ultrasonic`；频率、换能器、衰减、角分辨率、水/泥、噪声 | 活跃 V2 serializer 输出单距离；旧数组绑定不作为当前输出契约 | S：Sensor/UltraSonicSensor.cpp:68,184；A:1622；R:99；P:1081 |
| `carla-imu` | `sensor.other.imu`；加速度、角速度、compass、轴向噪声/偏置 | 单位、坐标轴、重力含义在本 skill 解释；多源融合不属于原始 IMU 操作 | S：Sensor/InertialMeasurementUnit.cpp:39；A:1288；P:889 |
| `carla-gnss` | `sensor.other.gnss`；经纬高、噪声/偏置、地理参考 | 地图 geoReference 归 map 查询；不承诺真实 GNSS 传播/遮挡模型 | S：Sensor/GnssSensor.cpp:26；A:2023；P:882 |
| `carla-target-sensor` | `sensor.other.target`；视域/遮挡、目标、车道拟合、交通灯、端口输出 | 局部传感器输出；全世界 selector 归 ground-truth，OSI 标准输出归 osi | S：Sensor/TargetSensor.cpp:77,172,882,1987,2122；A:1444；P:918 |
| `carla-obstacle-sensor` | `sensor.other.obstacle`；前方距离、检测半径、only_dynamics、障碍事件 | 前方探测；已发生的物理碰撞归 collision | S：Sensor/ObstacleDetectionSensor.cpp:25；A:2408；P:869 |
| `carla-collision-sensor` | `sensor.other.collision`；碰撞对象、normal_impulse、通道与事件 | 无事件不等于数据链路故障；不负责提前避障 | S：Sensor/CollisionSensor.cpp:26；P:862 |
| `carla-lane-invasion-sensor` | `sensor.other.lane_invasion`；车体边界穿越车道线事件 | 客户端计算、要求 vehicle parent；不按服务端连续流排障 | S：Sensor/LaneInvasionSensor.cpp:10；LibCarla/source/carla/client/LaneInvasionSensor.cpp:108；P:876 |
| `carla-rss` | `sensor.other.rss`；RSS response、路由、车辆 dynamics、Restrictor | 专项完整安全链，避免另建重复 RSS 控制 skill；要求对应构建和依赖 | S/C：Sensor/RssSensor.cpp:15；PythonAPI/carla/src/PythonAPI.cpp:54；AdRss.cpp:179 |

注册覆盖依据：`R:85–113` 和 `Sensor/SensorFactory.cpp:31–94`。25 个可生成定义之外，`FWorldObserver`、`FCameraGBufferUint8`、`FCameraGBufferFloat` 是内部注册项，不作为三个可生成传感器 skill。GBuffer 公共监听接口放进 camera/shared reference；取得独立数据集工作流后再评估是否单列。

## 工程、资产、地图制作与集成

源码缩写：`CT/`＝`Unreal/CarlaUnreal/Plugins/CarlaTools/Source/CarlaTools/`；`CTPy/`＝`Unreal/CarlaUnreal/Plugins/CarlaTools/Content/Python/`；`MP/`＝`Unreal/CarlaUnreal/Plugins/MapOptTool/Source/MapOptTool/Private/`；其他路径相对基线根目录，`U/` 延用前文。

### 环境、构建与运行实例

| 建议 skill | 负责什么 | 边界与交接 | 源码依据 |
|---|---|---|---|
| `carla-environment-setup` | OS/toolchain/UE/Python 前置、安装与环境定位 | setup 脚本包含后续动作，不能把检查环境等同于授权全量 build/install/launch | S/C：CarlaSetup.sh:72,98；README.md:129 |
| `carla-content-sync` | 独立 Content 资源来源、目录、代码/资产版本配对、完整性和同步 | 目录存在不证明资源完整；不构建/启动 | S/C：CarlaSetup.sh:84；Unreal/CMakeLists.txt:643 |
| `carla-build-configure` | CMake toolchain、Python、client/server、feature flags | 生成配置；开关存在不证明功能已接通，编译由各 build skill 完成 | S：CMakeLists.txt:79；CMake/Options.cmake:17 |
| `carla-build-libcarla` | C++ client/server 库及依赖构建 | 不负责 Editor、wheel、Shipping | S：CMakeLists.txt:87；LibCarla/CMakeLists.txt:210,385 |
| `carla-build-python-api` | 指定 Python 的 wheel 构建/安装、绑定版本核对 | 不隐式升级全局 Python；连接验证交 connection | S：PythonAPI/CMakeLists.txt:118,169；buildpyapi.sh:9 |
| `carla-build-editor` | 明确要求时编译 CarlaUnrealEditor | 复用已有 build-editor 规则，不新增第二套构建流程；启动另项 | S：Unreal/CMakeLists.txt:440；lunch.sh:7 |
| `carla-editor-launch` | Content 检查、launch-only、打开项目/地图 | build+launch 必须识别为构建动作；后续场景操作交领域 skills | S/C：Unreal/CMakeLists.txt:643 |
| `carla-build-shipping` | build/cook/stage/archive/package、包与代码对应证据 | 复用已有 build-shipping 规则；最终打包发布在正式主分支，发布另行完成 | S：Unreal/CMakeLists.txt:502,597；package.sh:7 |
| `carla-map-cook` | 指定地图 cook、检查 cooked 输出 | `single_map_package.sh` 只有 cook，不等于独立可分发地图包 | S：single_map_package.sh:1 |
| `carla-server` | 已有 Shipping 包的启动配置、端口/进程身份、日志、ready、拥有实例的停止 | 不编译/打包；不接管借用实例；独占实验生命周期交 session | S/P：UE5_BUILD_README.md:84；插件进程所有权/安全停止封装为拟新增能力 |

### 资产与地图制作

| 建议 skill | 负责什么 | 边界与交接 | 源码依据 |
|---|---|---|---|
| `carla-fbx-import` | FBX/maps/props package JSON 导入、材质整理、地图准备 | UE4_ROOT/UE4Editor 旧链路须适配；USD/Houdini 独立；不直接运行旧全链路 | S/L：Util/BuildTools/Import.py:64,199,220,284,344,426 |
| `carla-map-materials` | imported map 的 road painter、decals、语义目录与 cook 前地图整理 | 可从导入中独立恢复；不编写 shader，不执行 package | S/C：U/Commandlet/LoadAssetMaterialsCommandlet.h:62；MoveAssetsCommandlet.h:48；PrepareAssetsForCookingCommandlet.h:118 |
| `carla-vehicle-assets` | 已有车辆 Blueprint→factory 定义、命名/generation/可发现性 | 不做建模或动力学标定；Python helper 只有 append，无 save，持久化必须补证 | S/C：CTPy/add_vehicle_to_vehicle_factory.py:24；U/Actor/Factory/VehicleActorFactory.cpp:103 |
| `carla-prop-assets` | static mesh→static.prop.*、factory/package JSON、保存 | runtime spawn/control 交 actors；碰撞质量须单独检查 | S：CTPy/add_prop_to_prop_factory.py:60 |
| `carla-actor-extension` | 新 actor 的 factory parameters、definition cache、Blueprint 入口与绑定扩展 | 既有资产注册交上两项；新 sensor 全链路另项 | S：U/Actor/CarlaActorFactoryParameters.cpp:25,124；U/Actor/CarlaActorFactorySystem.cpp:40；CT/Private/CarlaAssetFactory.cpp:219 |
| `carla-sensor-extension` | 新 sensor 的 definition/factory、UE actor、serializer、registry、Python data binding、专项 schema | 服务于开发者扩展类型；使用现有 sensor 归 25 个专项；不把内部类各建 skill | S/P：LibCarla/source/carla/sensor/SensorRegistry.h:78；U/Sensor/SensorFactory.cpp:31；PythonAPI/carla/src/SensorData.cpp:678 |
| `carla-blueprint-reparent` | 指定目录/资产的 Blueprint/AnimBlueprint parent 修复 | 明确目标父类和资产范围；不自动扫描并修复整个工程 | S：CT/Private/BlueprintParentClassFixer.cpp:23,88 |
| `carla-opendrive-authoring` | Editor 内 ODR 地图制作入口与可用步骤诊断 | 当前 GenerateRoadMesh/GenerateLaneMarks/CreateTerrain 为空、GenerateSpawnPoints 调用被注释；不能承诺完整道路产物。与运行时 opendrive-world 分开 | S/C：CT/Private/OpenDriveToMap.cpp:146,268,489；CT/Public/OpenDriveToMap.h:197 |
| `carla-large-map` | main map、tile map、元信息、tile 坐标、子地图衔接 | 运行时 streaming/dormancy 交 world/actors；navmesh/package 独立 | S/C：CT/Private/MapGeneratorWidget.cpp:58,745,855,1443 |
| `carla-terrain` | heightmap/terrain、平滑、tile 接缝、碰撞重算 | 不覆盖土壤物理拟合；可驾驶/可行走由运行验证判断 | S/C：CT/Private/OpenDriveToMap.cpp:177；CT/Private/MapGeneratorWidget.cpp:228,1455 |
| `carla-map-dressing` | 植被、misc actors、ROI、水体、map weather actor 的离线布置与保存 | runtime weather/lights 交环境层；删除操作必须限定对象 | S/C：CT/Private/MapGeneratorWidget.cpp:83,459,569,1156,1231 |
| `carla-houdini-import` | 已有 Houdini 产物接入 large-map sublevels、分块移动、坐标调整 | UE 后处理入口；Houdini 建模/graph 执行在外部 | S/C：CT/Public/HoudiniImporterWidget.h:25 |
| `carla-navmesh` | 场景碰撞/FBX→OBJ、XODR crosswalk、Recast→导航 bin | Walker 导航网格；不是 TM 路网；旧 tiled Recast 链路被禁用 | S/C/L：Unreal/CarlaUnreal/Plugins/CarlaExporter/Source/CarlaExporter/Private/CarlaExporter.cpp:63；Util/DockerUtils/dist/build.sh:7；Util/BuildTools/Import.py:495 |
| `carla-tm-map-cache` | TM 地图 binary/cache 生成 | 运行时 TM 行为另项；不与 Walker navmesh 合并 | S/C/L：Util/BuildTools/Import.py:573；旧 import/toolchain 适配前不能承诺完整入口 |
| `carla-map-optimize` | mesh/material/asset/tag/path 统计、重复对象筛选、选定对象 ISM 合并 | 审计与修改是同一 skill 的不同操作；移除原对象须显式范围，性能改善由 benchmark 判定 | S：MP/MapOptToolBPLibrary.cpp:27,398,490,841,989,1031 |
| `carla-usd-import` | USD prop/vehicle、lights/wheels、车辆 Blueprint；交资产注册 | 当前构建接线未完成；不泛称通用 USD 地图导入 | S/C：CT/Private/USDImporterWidget.cpp:42,436,610；CT/CarlaTools.Build.cs:123–134 启用分支抛 NotImplementedException；U/MapGen/USDImporterActor.cpp:19 为空 |
| `carla-gltf-load` | 条件编译的 GLTF 车辆/static mesh 加载 | factory 注册/runtime spawn 另项；依赖插件齐备尚未验证 | S/C：CMake/Options.cmake:146；U/Actor/StaticMeshFactory.cpp:156；U/Actor/Factory/VehicleActorFactory.cpp:103 |

### 插件协议与外部系统

| 建议 skill | 负责什么 | 边界与交接 | 源码依据 |
|---|---|---|---|
| `carla-cluster` | member registration、heartbeat、类型化消息、RPC 绑定、协议连通 | 当前证据是协议组件，不承诺完整多机/multiGPU 调度；实例启动交 server | S/C：Unreal/CarlaUnreal/Plugins/CarlaCluster/Source/CarlaCluster/Private/CarlaClusterProxy.cpp:14,107,203；CarlaClusterSubSystem.cpp:55,121 |
| `carla-debug-port` | UDP ConnectTest/List/Data、port/magic、受限命令查询与执行 | 专属协议；查询与执行 console command 分权限；普通调试标绘交 debug | S/C：Unreal/CarlaUnreal/Plugins/CarlaDebugPort/Source/CarlaDebugPort/Private/CarlaDebugPortSystem.cpp:119,313,341 |
| `carla-ros2-native` | 已支持二进制的 ROS2 stack、publisher、RViz；缺构建能力交 configure | 当前顶层 Ros2Native add_subdirectory 注释，不能承诺开箱可用 | S/C：PythonAPI/examples/ros2/README.md:12；Ros2Native/CMakeLists.txt:12；CMakeLists.txt:95–97；LibCarla/CMakeLists.txt:260 |

下面四项是**外部接入预留目录**，不计为 sprint42 已有能力。列出它们是为了明确边界；外部仓版本、兼容补丁和数据契约仍需另行调查后才能定义可执行操作。

| 预留 skill | 独立责任 | sprint42 证据及缺口 |
|---|---|---|
| `carla-scenario-runner` | 外部场景定义/执行、固定依赖、结果接收 | README.md:47 外部链接；未证明此定制基线兼容 |
| `carla-leaderboard` | 外部评测 agent 契约、评测任务、评分结果 | README.md:48 外部链接；不与通用 scenario 执行合并 |
| `carla-ros-bridge` | 外部 ROS bridge 的版本/消息/坐标/同步接入 | README.md:49 外部链接；与原生 ROS2 构建路线分开 |
| `carla-sumo-cosim` | 外部 SUMO 的时钟、对象映射、控制权及双向同步 | 本轮未定位基线实现入口；保持候选，不称现成能力 |

NuRec 在本项目中仍是产品设计参考；本次基线盘点没有建立 NuRec 可执行集成证据，暂不创建“已支持 NuRec”的 skill。NuRec、Houdini 等外部产品本身的能力不借由命名进入本插件承诺。

## 采集、入门与 Auto Research：插件组合层

以下是建立在 sprint42 操作之上的插件职责，不是 sprint42 原生 skill。现有 `capture.run` 只覆盖有限的单车单传感器 recipe，research 控制器也只有有限参数比较；下表描述已落实的 skill 职责；未封装部分仍需按各 skill 的原生/条件流程执行。

| 建议 skill | 负责什么 | 不负责什么 / 交接 | 依据与状态 |
|---|---|---|---|
| `carla-sensor-rig` | 多传感器配置、父 actor、安装位姿/外参、挂载/拆卸、配置保存 | 各类 sensor 参数/解码归 25 个专项；生命周期通过共享 actor/session 操作执行 | P，底层 S：PythonAPI/carla/src/Sensor.cpp:45；World spawn 接口；当前插件仅有单次 attach |
| `carla-capture` | 有界采集、warmup、frame/timestamp 对齐、不同频率与事件流、队列/超时、原始文件与 manifest | 不承包各 sensor 物理模型；数据质量结论依赖对应专项；不选择实验最优参数 | P，底层 S：PythonAPI/examples/sensor_synchronization.py:57；插件 docs/implementation-contract.md |
| `carla-dataset` | 将采集产物与标签/标定/坐标对应关系组织成有 schema 的数据集，检查缺帧/配对/文件完整性 | 不重新运行实验，不把检测结果当真值；首版公开格式待选，不承诺已支持 KITTI/COCO 等 | P，组合 capture、ground-truth、camera semantic/instance；当前未实现通用数据集导出 |
| `carla-onboarding` | 按目标选最短学习路径：连接→观察→操作→看到结果→解释差异 | 教学组合已有 skill；不复制操作实现，不另建万能问答知识库 | P：插件 references/carla-learning.md；当前教学规则在 reference 中 |
| `carla-research-plan` | 定义可证伪问题、workload、允许变化项、有效性/比较条件、预算与独立确认 | 不直接跑实验；阈值来源必须明确；跨构建/源码改写不自动纳入 | P：插件 src/carla_agent/research.py:60；references/carla-research.md |
| `carla-benchmark` | 在冻结条件下执行 baseline/candidate trial、重复采样、记录观测与失败 | baseline 和 candidate 是同一执行能力的角色，不各建 skill；不把回调延迟称 GPU 内核时间 | P：插件 src/carla_agent/research.py:283,306,487；现控制器内部已有有限实现，独立公开命令待拆 |
| `carla-compare` | 只读验证实验产物、可比条件、有效性、波动与改善，给出有条件结论/证据不足 | 不偷偷重跑或改变阈值；不自动应用获胜参数 | P：插件 src/carla_agent/research.py:358,392,415；只读入口为 research.compare |
| `carla-parameter-search` | 编排有界候选试验、独立确认、预算、状态、停止/恢复和建议参数 | 复用 benchmark/compare；不另写传感器操作；不默认修改 C++、构建或发布 | P：插件 src/carla_agent/research.py:463,487,633；现仅 RayCast LiDAR 有限属性与延迟代理 |

完整例子：“比较两种 MEMS 扫描配置”由 research-plan 固定目标和条件 → lidar-mems 校验 pattern/属性 → sensor-rig 挂载 → benchmark 调 capture → compare 判断 → parameter-search 管预算与独立确认。专项知识、采集机制和实验判断各自只有一个 owner。

边界例子：DVS 某时段没有事件，capture 应依据事件流契约记录空集合；不能套用 RGB 的每帧图像规则直接判丢帧。研究比较若只有点数/有限坐标底线，只能对这些指标下结论，不能据此宣称感知精度或物理等价。

## 现有六个 skill 如何迁移

以下映射已落实到 SKILL.md；connection/world/actors/capture 在原路径收窄职责，sensors/research 保留兼容路由。原文件副本保存在本地变更前快照，既有 CLI 命令保留。

| 现有入口 | 目标 |
|---|---|
| `carla-connection` | 保留连接诊断职责；工程安装/构建、运行实例管理、会话所有权分别路由到对应专项 |
| `carla-world` | 拆到 world、clock、map、weather、scene、lights、spectator、truth 等；原入口作为迁移期路由说明 |
| `carla-actors` | 通用生命周期与 blueprints 留在各自入口；车辆控制/动力学、工程车辆、walker、TM 逐项拆开 |
| `carla-sensors` | 迁移为 sensor-rig 的挂载与配置职责，加上 25 个专项；通用生命周期和解码工具复用 |
| `carla-capture` | 保留采集窗口和原始产物职责；数据集组织转 dataset；实验判断转 benchmark/compare |
| `carla-research` | 拆 research-plan、benchmark、compare、parameter-search；原入口保留导航和迁移说明 |

各 skill 的执行状态区分为 CLI、原生 API、条件流程和组合流程；原子命令验证与指定环境实机演示分别记录。先完成 103 项基础指引，再接 4 项 Auto Research；研究始终复用公共采集。尚未封装的原生流程及条件组件不能标成已自动化或已实机通过。

## 共享能力的所有权

| 共享内容 | 放在哪里 | 领域 skill 的责任 |
|---|---|---|
| 环境 profile、版本与能力探测、JSON 协议、错误结构 | shared reference + 执行层 | 声明所需能力，缺能力时给具体原因 |
| actor/session 所有权、清理、episode 变化 | session/actor 操作层 | 只释放本任务拥有的资源 |
| sensor spawn/attach/listen/stop/destroy | sensor 生命周期操作 + shared reference | 每个专项提供合法属性、安装要求、解码与故障判断 |
| frame/timestamp、回调队列、背压、stream 开关 | shared stream 实现；capture 负责采集窗口 | 说明连续帧、低频采样、事件流各自的有效输出规则 |
| 坐标、单位、内参/外参、原始 stride/endian | shared reference + 专项 schema | 不在不同 skill 复制矛盾的解码器 |
| GBuffer、渲染线程、WorldObserver、RPC、序列化 | 开发参考/内部库 | 专项 skill 引用，不为每种内部类型建 skill |

`Sensor.cpp:45–77`（PythonAPI binding）给出通用生命周期；事件传感器不能一律以“每个世界 frame 必须一个 callback”验收。Normals 与 Image 共用颜色图像模板（`LibCarla/source/carla/sensor/data/Image.h:16–30`）；Ultrasonic 以活跃 Registry/serializer 为准；mmwave 依赖插件 `Sensors` 和 FFTW，其模型存在概率目前固定为 1。
