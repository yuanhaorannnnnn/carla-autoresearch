# Camera 契约

执行与缩写见 [native acquisition](sensors-native-acquisition.md)。只有需要本段时加载；各相机的实际 describe 优先。

## 常规 pinhole camera 属性

`A:332 MakeCameraDefinition` 给 RGB/depth/semantic/instance/flow/DVS/stereo 提供 image_size_x/y（Int pixels）、fov（Float degrees）、sensor_tick（Float seconds）、send_data_stream（Bool，源码推荐 False）。fx/fy/cx/cy（Float pixels）、use_custom_projection_matrix（Bool）、horizontal_mirror（Bool）、k1–k6/p1/p2（Float 系数）、distortion_model（String，按实时推荐模型）、lens_circle_falloff/multiplier、lens_k/kcube、lens_x_size/y_size（Float 模型参数），image_type（String，定义推荐 RGBA/YUV420）。属性存在不证明每个派生 camera 使用相同发送开关或图像路径。

RGB、DVS、stereo 的定义启用可修改后处理：enable_postprocess_effects/open_awe/enable_ao/enable_ssr/enable_bloom/enable_eye_adaptation/enable_tonemapper（Bool）；gamma、motion_blur_intensity/max_distortion/min_object_screen_size、bloom_intensity、exposure_compensation、shutter_speed、iso、fstop/min_fstop、exposure_min_bright/max_bright/hist_log_min/hist_log_max/speed_up/speed_down、sensor_width、focal_distance、temp/tint（Float），blade_count（Int），exposure_mode（String manual/histogram）。保留真实拼写 shadow_constrast_scale。sensor_width 是 mm；shutter_speed 是曝光时间的倒数（1/s），focal_distance 的 UE 参数单位要核对 setter 后使用，不能与安装距离混用。后处理属性太多时只提交与请求有关的配置，保存整份 describe 供重现。

`D/Image.h` 中 Image=ImageTmpl<Color>，Color 的内存顺序是 BGRA8（D/Color.h）。image_type 选择 YUV 时不能 reshape 为 H×W×4；需核对 pixel_format、raw_data 长度、PixelReader 中转换与 plane 布局。默认四通道才使用 `np.frombuffer(image.raw_data, dtype=np.uint8).reshape(image.height,image.width,4)`，RGB 预览取 `[..., :3][..., ::-1]`。转换和着色可破坏原始标签/深度，原始 bytes 先保存。

## 深度、标签与法线

深度 RGB24 编码在 BGRA buffer 中对应 R=byte2/G=byte1/B=byte0：normalized=(R+256G+65536B)/16777215；标准材质下 meters=1000×normalized，PixelReader.cpp:731–735 也采用此公式。Linux 使用 DepthEffectMaterial_GLSL，材质资产/实际二进制未核验时报告缩放假设；ColorConverter.Depth 是显示灰度，不是米值文件。不要先做 palette 再解码。

semantic 红通道是类别 ID，palette 只用于显示；标准instance语义在R，实例编码在G/B；本fork材质资产的高低字节方向未由C++证明，先保留(G,B)二元组，核验后再合成uint16。instance ID 不自动等于 Actor.id，不承诺跨 reload/重生稳定。标签名称用 `LibCarla/source/carla/rpc/CityObjectLabel.h` 与 `LibCarla/source/carla/image/CityScapesPalette.h` 对照；定制分类不能直接套上游色表。材质资产内容不在 C++ 类型绑定中，若要求像素级证明，需原始图和已知 actor 对照。

NormalsImage 在 `D/Image.h` 是 `ImageTmpl<Color>` 的 alias，与 Image 是同一个 C++ 模板类型；Z/NormalsImageSerializer 返回此 alias，P 只有 Image 的该模板绑定。没有独立 Python NormalsImage 构造器，也不是 FloatImage。通常把 RGB 映射到 [-1,1] 作为法线候选 `2*rgb/255-1`；确切轴向、空间和材质缩放要核对 NormalsEffectMaterial 或用已知面验证，不能因三通道长得像法线就声称 world-space。S/NormalsCamera.cpp 明确关闭16bit并读取 FColor。

## Optical flow

P:794 OpticalFlowImage；D/Color.h 的 OpticalFlowPixel 为两个 float32 x/y，raw_data 每像素8字节。`np.frombuffer(...,np.float32).reshape(H,W,2)`。S/OpticalFlowCamera.cpp 从渲染值减0.5再乘4，输出 normalized screen displacement；需转 pixel displacement 时结合宽高及实际材质约定，不能当 m/s。get_color_coded_flow() 返回用于显示的 FakeImage，不能回解为原始数值流。

## GBuffer

PythonAPI/carla/src/Sensor.cpp 提供 listen_to_gbuffer/stop_gbuffer/is_listening_gbuffer，texture ID 见 P 的 GBufferTextureID。GBuffer Uint8/Float 是内部 registry 类型，不是可 spawn 的 sensor blueprint；按实际纹理类型解码，不将它们注册成两种相机。仅在自有 camera 上按本次请求监听并在结束时取消各 texture listener。

## 专用 serializer

- DVS：D/DVSEvent.h packed x/y uint16、t int64、pol bool，13 bytes/event，t 为纳秒；SensorData.timestamp 仍是秒。非空发送条件见 S/DVSCamera.cpp:204；不能要求每 tick 一条空事件包。
- fisheye：D/ImageCube.h 与 D/ImageTmplCube.h、Z/ImageSerializerCube.h、P:776；即使合并结果看起来像2D，仍按 ImageCube 解释，不强制承诺6幅 face 总在 raw_data。
- stereo：D/StereoImageData.h 与 Z/StereoCameraSerializer.h、S/PixelReader.cpp:715–807。left/right 是 Image，left_depth_image/left_disparity_image 是 ImageUint16；enable_depth=false 时后两项为 None。深度 uint16 mm，视差 uint16 的1/100 pixel；producer 直接 cast，无饱和保护，不能把超量程结果解释成可信距离。depth>65.535m 或 disparity>655.35px 已超 uint16 表达范围。各子图继承同 frame/timestamp，RGB/YUV格式取左右Image的pixel_format；ImageUint16绑定未提供pixel_format。
