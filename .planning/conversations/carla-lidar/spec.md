# CARLA LiDAR Optimization Spec

## Conversation ID

`carla-lidar`

## Summary

将 `autoresearch` 仓库改造成一个面向 CARLA `ray_cast` LiDAR 的外部实验控制器。目标 codebase 位于 `/media/yhr/2T/CarlaUE5`，控制器负责构建、启动服务端、运行静态 benchmark、提取指标，并基于单扫描延迟与点数完整性做 keep/discard 判定。

## Fixed Decisions

- Target map: `Town05`
- Sensor blueprint: `sensor.lidar.ray_cast`
- Runtime mode: Shipping package + headless server
- Benchmark mode: static ego + static lidar
- Primary metric: `scan_latency_ms_median`
- Correctness rule: point count must match baseline exactly
- Allowed optimization area: `RayCastLidar*`, `RayCastSemanticLidar*`, `LidarDescription.h`
