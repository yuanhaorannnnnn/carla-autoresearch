# Findings

## Verified Facts

- CARLA target repo: `/media/yhr/2T/CarlaUE5`
- Build entry: `/media/yhr/2T/CarlaUE5/package.sh`
- Server entry: `/media/yhr/2T/CarlaUE5/Build/Package/Carla-0.10.0-Linux-Shipping/Linux/CarlaUnreal.sh`
- Existing Python reference client: `/media/yhr/2T/CarlaUE5/Build/Package/Carla-0.10.0-Linux-Shipping/PythonAPI/examples/manual_control.py`
- `RayCastLidar` is a thin specialization over `RayCastSemanticLidar`; key hot path is in `SimulateLidar`, `ShootLaser`, `ComputeAndSaveDetections`
- Existing client already exposes `sensor.lidar.ray_cast` and explicit lidar attributes
- 真实联调已验证：服务端和客户端都优先在真正的新桌面终端里运行；客户端必须先激活 `py38`，否则结果不可靠
- 正式 `benchmark_client.py` 路径下已验证通过一次点云点数一致性复测，`point_count_all_equal=true`
- 自动化流程 guardrail 已沉淀：
  - 不要用临时内联脚本绕过正式入口
  - 当前已有活跃 `CarlaServer` 时优先复用，不重复启动第二个实例
  - 若未来改动扩到 `LibCarla` / `PythonAPI`，则 `package` 后客户端启动前必须 force-reinstall 新 wheel
- `CarlaUE5` 当前性能优化改动承接到分支 `feature/carla-lidar-optimization`
- 第一轮性能补丁内容：在 `RayCastSemanticLidar::SimulateLidar` 外层 hoist `GetTransform()/Rotator()/Range`，减少每条射线内的重复读取
- 第一轮性能补丁的正式对比结果：
  - baseline: `runs/retest-20260326-102715/metrics.json`
  - current: `runs/test-20260326-124609/metrics.json`
  - `scan_latency_ms_median` 改善约 `33.7%`
  - `scan_latency_ms_p95` 明显下降
  - 两次 run 内部点数一致性都保持成立
- 自动化 `package` 仍存在流程不稳定问题：Python 直接拉起 `gnome-terminal` 并传 payload 不可靠；当前代码已改成 launcher `.sh` 方案，但本轮先退化为用户手动执行 `package`
- 第二轮恢复全自动后又发现一个明确实现问题：launcher 里若使用相对日志路径，在脚本内部 `cd /media/yhr/2T/CarlaUE5` 后会导致 shell 重定向失败，从而出现只写出 `build.exitcode`、不生成 `build.log` 的现象。现已修复为统一使用绝对路径。
- 第二轮全自动重试又发现一个更前置的问题：在 `gnome-terminal` 拉起的裸 shell 中，launcher 不能依赖 `conda info --base` 先找到 `conda.sh`；现已改成固定使用 `/home/lkshpc/anaconda3/etc/profile.d/conda.sh`。
