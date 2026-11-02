# 目标传感器、雷达和事件输出

执行与缩写见 [native acquisition](sensors-native-acquisition.md)。先用Python对象字段，只有确需原始二进制才读取完整struct和serializer。Target/Oasis/mmwave的struct不是统一packed float32点云，不能盲目reshape。

## Oasis 与 target 的区别

`D/RadarOasisData.h` 的RadarOasisDetection是object_idx/object_type（uint32）加float32几何/运动字段。P:1047的Python字段为object_id/object_type、x/y/z、pitch/yaw/roll、velocity_x/y/z、angular_velocity_x/y/z、length/width/height、min_distance、relative_velocity、rcs。S/RadarOasis.cpp:350–450 中 x/y/z实际上由sensor inverse transform得到（m），不是名称world_X所暗示的world坐标；姿态是sensor相对degrees，线速度经sensor逆旋转并换算m/s，尺寸是全长m；角速度来自actor接口degrees/s，代码未统一旋转到与线速度相同坐标，right_hand分支还做符号/安装变换，应分别记录。min_distance为射线最近距离m，relative_velocity是径向m/s。rcs是按tag查表/默认值的模型参数，不能当实测RCS校准证据。

`D/TargetData.h` 的TargetDetection包含上述float32几何字段，另有sub_type/sim_id（uint32）、acceleration_x/y/z（float32）、road_section_num/section_size（int）、5组lane字段（m/l/r/ll/rr；ID/type/color/validity为int，width/c0/c1/c2/c3为double），traffic_light_num/traffic_light_validty/t_id/state/junction_id/type/cycle（int），distance/forward_angle/countdown（float），elapsed_time（double）。Python主车道组省略m_前缀，c0..3对应m_x0..3，保留真实拼写traffic_light_validty。lane validity决定该组能否解释，不能把未填/无效字段当观测。c0..c3是多项式各阶系数，不可全部标为meters；坐标约定、有效区间需由LaneInfoFit/写入处确认。不同object_type对应不同有效字段，不按每条记录全部有效导出。

S/TargetSensor.cpp:684–757把object位置/姿态变到sensor局部（m/degrees）；right_hand转换与Oasis分支不完全一样；速度/加速度/角速度逐一核对赋值，不能用变量world_X推断世界坐标。尺寸m、径向速度m/s、距离m；灯态为枚举/计时而非像素语义标签。对象ID、sim_id和外部消息ID分开保存。未确认填充值/单位的字段输出原值并标明待核验，不能发明真实精度。

## mmwave

Blueprint为sensor.radar.millimeter_wave，A:3800定义全为Float：F0_GHz（GHz）、Pt_dBm（dBm）、Gt_dBi/Gr_dBi（dBi）、Ts_K（K）、Fn_dB/L0_dB/SNR_min_dB（dB）、Delay、FovVertial/FovHorizional/ResVertial/ResHorizional（degrees）、Range（m）。拼写Vertial/Horizional必须保留，Delay单位/生效链由实际setter和依赖模型确认，不能擅自说是ms。源FRadarParameter有额外字段不代表已作为blueprint attributes暴露。

P:1144：MillimeterWaveRadarMeasurement可迭代；detection.objidx/objtype是uint32，distance/azimuth/elevation/radialvelocity/rcs/existenceprobability是double。distance=m、radialvelocity=m/s、azimuth=degree（与普通radar的radians不同），RCS单位以RadarModel约定核验。`Unreal/CarlaUnreal/Plugins/Sensors/Source/Sensors/Radar/MillimeterWaveRadar.cpp:144–155`将ObjType=0、Elevation=0、ExistenceProbability=1，不能把它们作为有效类别/测高/已校准置信度。依赖Sensors与RadarModel/FFTW可用性，源码存在不证明当前wheel/server可执行。

## 连续距离与事件

- ultrasonic：registry用UltraSonicSerializerV2；Z/UltraSonicSerializer.h是MsgPack float distance，Python UltraSonicMeasurementV2.distance（meters）。旧UltraSonicMeasurement/raw_data/Detection四字段仍绑定但不是此sensor当前数据。无命中输出模型的post range，不把等于range当具体障碍。noise_std经d(gen)*1e-2加入m距离，配置值尺度为cm；noise_seed不一定控制这里新建random_device的噪声，不能承诺固定seed可重现。
- obstacle：ObstacleDetectionEvent.actor/other_actor与float distance（m）；有sweep命中才发送；distance/hit_radius设置为meters后在server换算cm。only_dynamics与静态通道策略改变命中对象集合。
- collision：CollisionEvent.actor/other_actor、normal_impulse为Vector3D float32（kg·m/s），不是力/加速度；OnCollisionEvent按frame+actor pair去重，另有overlap检测路径，不能推断单回调等于全部接触点。
- lane invasion：LaneInvasionEvent.actor、crossed_lane_markings（LaneMarking列表，有type/color/lane_change/width等实际绑定属性）。客户端依据vehicle bounding-box四角与地图车道线计算；NoopSerializer意味着不等待服务器TCP事件包。没有vehicle parent不会正常监听；不要对行人/任意actor承诺可用。无越线时不发回调，地图标线缺失/不准确也影响结果。

源码：S/RadarOasis.cpp、TargetSensor.cpp、MillimeterWaveRadarSensor.cpp、UltraSonicSensor.cpp、ObstacleDetectionSensor.cpp、CollisionSensor.cpp；LibCarla/source/carla/client/LaneInvasionSensor.cpp；D/RadarOasisData.h、TargetData.h、MillimeterWaveRadarData.h；P:862–1144；各Z serializer与SensorRegistry.h。
