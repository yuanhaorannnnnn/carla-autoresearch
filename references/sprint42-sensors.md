# sprint42 传感器适配

源码参考 `2075f526dec86362fe058a6fff939e6832876759`。运行时应以实际 blueprint
为准；相同版本字符串不证明二进制来自这份源码。

- `sensor.camera.rgb` 的 `send_data_stream` 在该参考树默认 false。若实时
  `sensors describe` 有这个字段，采集时显式设为 `true`。server 内显示有图或
  SensorDisplay 队列满不证明 client 已收到数据。2026-11-02 在已有0.10.0包中，
  默认关闭出现回调超时；仅改该属性后收到3帧640×360 BGRA8。
- `image_type` 保持与采集器支持的4字节 RGBA 路径一致。开启发送前先检查属性，
  不把此定制字段发给未支持的上游 server。
- 该树 stream ID 使用 `role_name + blueprint ID`。同类型多个sensor要显式给
  不同 role_name。首版capture只创建一个sensor，手动组合仍需考虑这一点。
- 标准 RayCast 直接序列化发送，不使用 camera 的发送开关。不把相机诊断推广
  成 LiDAR 修复，不凭少量点数判断物理正确性。
- 当前 capture worker 仅支持 RGB 与标准 RayCast 的已定义原始布局。MEMS
  即使blueprint存在也不在此版capture支持范围；原子inspect/attach按能力校验，
  不用标准RayCast替代MEMS来报告成功。

可定位源码：`ActorBlueprintFunctionLibrary.cpp` 中 `send_data_stream` 定义和
`SetCamera`；`SceneCaptureCamera.cpp` 中 `NeedSendDataToStream`；
`SensorFactory.cpp` 的 stream ID 构造。它们位于 CARLA Unreal plugin。
