# LiDAR 数据与扫描路径

执行与缩写见 [native acquisition](sensors-native-acquisition.md)。此文件专用于布局/扫描证据，运行 describe 仍是属性来源。

## 属性与单位

`A:1739 MakeLidarDefinition`：channels/points_per_second/noise_seed 为 Int；range 为 Float meters；rotation_frequency 为 Float Hz；upper_fov/lower_fov/horizontal_fov 为 Float degrees；atmosphere_attenuation_rate、dropoff_general_rate/intensity_limit/zero_intensity、noise_stddev 为 Float；simu_brdf/simu_motion_distortion 为 Bool。噪声沿射线扰动距离（m），dropoff 是概率/归一化强度参数，不能把 intensity 直接标成反射率或 dB。semantic 定义仅附加它所采用的几何扫描字段，不能将标准 raycast 的全部噪声/dropoff 列表照抄给 semantic。

`A:1863 MakeMemsLidarDefinition`：channels/beams_num/noise_seed 为 Int；range、rotation_frequency、atmosphere_attenuation_rate、dropoff_*、noise_stddev、distance_accuracy/distance_precision 为 Float；scanning_patterns 为 String；simu_brdf/simu_motion_distortion/sim_nearest_down_sample 为 Bool。CPU MEMS 未把 udp_ip/udp_port 放进定义，CPU AT128 才附加 String udp_ip/Int udp_port。default scanning_patterns=M1 只是字符串，不证明正确CSV存在，也不能把此默认当作型号支持证据。

`A:2460 MakeSCLidarDefinition` 还提供 image_size_x/y/channels/points_per_second/beams_num（Int；beams_num 推荐文本为10.0，类型仍为Int）、fov/range/min_range/rotation_frequency/upper_fov/lower_fov/horizontal_fov/horizontal_fov_offset/horizontal_angular_resolution/vertical_fov_interval/high_res_distance_threshold/high_res_intensity_threshold/distance_accuracy/distance_precision（Float）、wheel_mode/high_res_mode/udp_work_mode（Bool）、noise_mode/data_source_type/data_source/scanning_patterns/udp_ip（String）、udp_port（Int）。fov与角分辨率是degrees，range/min_range是meters。阈值和source名称按实际 loader/算法，不凭名字猜资产路径和单位。

## 已注册的 Python 输出

| Blueprint | Serializer → Python | 点/头部 |
|---|---|---|
| sensor.lidar.ray_cast | LidarSerializer → LidarMeasurement | packed point.xyz float32 m + intensity float32，16 bytes/point；header为horizontal_angle、channels、各channel点数 |
| sensor.lidar.ray_cast_semantic | SemanticLidarSerializer → SemanticLidarMeasurement | packed xyz float32 m + cos_inc_angle float32 + object_idx uint32 + object_tag uint32，24 bytes/point；不是XYZI |
| sensor.lidar.ray_cast_mems | MemsLidarSerializer → MemsLidarMeasurement | point.xyz/intensity float32，16 bytes/point；laser_beam_index uint32、channels、各channel点数 |
| sensor.lidar.at128 | MemsLidarSerializer → MemsLidarMeasurement | 同MEMS布局，不是独立AT128Measurement；scan/UDP包含额外协议，与Python raw_data分开 |
| sensor.lidar.sc_lidar | LidarSerializer → LidarMeasurement | XYZI 16 bytes/point；不能把GPU UDP整包reshape为XYZI |

horizontal_angle 为float radians，channels/点数是整数。优先迭代绑定对象，确认实际端序/ABI后再用NumPy。raw_data 已排除 serializer header；raycast/MEMS 可 `np.frombuffer(data.raw_data,np.float32).reshape(-1,4)`。semantic 用显式structured dtype `[('x','<f4'),('y','<f4'),('z','<f4'),('cos_inc_angle','<f4'),('object_idx','<u4'),('object_tag','<u4')]`，小端仅在实际平台确认后使用。D/MemsLidarData.h 的旧注释/PLY header 残留 SurfaceType 字段，实际结构仅 point+intensity；以成员、serializer、绑定为准，不按残留注释造第五列。

## 扫描资产与模型

CPU MEMS：S/RayCastMemsLidar.cpp:135 CreateLasers 打开 `ProjectContentDir()/Carla/Config/<scanning_patterns>`，跳过首行，逐行以逗号取0列Vertical/1列Horizontal（degrees），std::stof；没有自动加.csv。先验证文件可读、有header、至少两数值列、非空及角范围，再spawn；空文件/不合法行可能导致异常或无扫描。beams_num 会被CSV实际长度覆盖；声称改变beams_num就改变扫描轨迹之前先核对代码。

CPU AT128：S/RayCastAT128.cpp:157 加载 `Carla/Config/AT128Field1PointOrderTable.csv` 到3，三组角序，256点分块。检查实际 LoadPointOrderFile 的列顺序和全部三个资产。udp_ip非空且udp_port非0才创建sender；网络发送是额外输出，缺少接收证据不能称交付。时间/CRC/分组/序号按 D/MemsLidarData.h 和 S/RayCastAT128.cpp 的封包函数逐字段解码；不能把标准AT128外部手册当本fork完全一致的协议。

GPU：S/SceneCapture_Lidar.cpp 的 TryLoadLaserArray/BuildLidarDatas/BuildUdpLidarDatas 选择 mechanical、AT128/M1AT128/M1/Pandar64 路径；这是同一 sc_lidar 的配置与资产，不是多个blueprint。加载器可依赖 Sensors/Lidar 数据资产与材质/shader，describe和spawn只证明早期阶段。udp_work_mode改变stream/UDP分支，必须分别验证用户实际要的交付路径；接收端UDP不自带session所有权，sender清理由拥有它的独立原生任务的actor owner完成。

## 定位源码

A:1739–2013、2460–2705；S/RayCastLidar.cpp、RayCastSemanticLidar.cpp、RayCastMemsLidar.cpp、RayCastAT128.cpp、SceneCapture_Lidar.cpp；D/LidarData.h、SemanticLidarData.h、MemsLidarData.h；Z/LidarSerializer.h、SemanticLidarSerializer.h、MemsLidarSerializer.h；P:811–860、1100–1112；SensorRegistry.h:99–111。
