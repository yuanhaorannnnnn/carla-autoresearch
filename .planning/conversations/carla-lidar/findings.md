# Findings

## Verified Facts

- CARLA target repo: `/media/yhr/2T/CarlaUE5`
- Build entry: `/media/yhr/2T/CarlaUE5/package.sh`
- Server entry: `/media/yhr/2T/CarlaUE5/Build/Package/Carla-0.10.0-Linux-Shipping/Linux/CarlaUnreal.sh`
- Existing Python reference client: `/media/yhr/2T/CarlaUE5/Build/Package/Carla-0.10.0-Linux-Shipping/PythonAPI/examples/manual_control.py`
- `RayCastLidar` is a thin specialization over `RayCastSemanticLidar`; key hot path is in `SimulateLidar`, `ShootLaser`, `ComputeAndSaveDetections`
- Existing client already exposes `sensor.lidar.ray_cast` and explicit lidar attributes
