---
name: carla-tm-map-cache
description: 根据指定 XODR 生成 Traffic Manager 的 in-memory map binary/cache；不生成 Walker navmesh，也不运行旧 UE4 全量 import。
metadata:
  category: engineering
  execution: native-api
  operations: ''
---

# carla-tm-map-cache

先读 [工程执行边界](../../references/engineering-execution.md)，核实 CARLA checkout；以下不是 carla-agent CLI 子命令。

输入：MapName、有效 XODR 文本、匹配 sprint42 的 Python API、目标输出路径与写授权。它可离线用 `carla.Map(name,xodr_content)`，不要求启动 server；不要为 cook cache 改正在运行的 world。保留旧 bin 与输入 XODR 的版本/摘要，确认输出目录可写且唯一。

实际 Python API：

```python
from pathlib import Path
import carla
xodr = Path(xodr_path).read_text(encoding="utf-8")
road_map = carla.Map(map_name, xodr)
road_map.cook_in_memory_map(str(output_bin))
```

`xodr_path`、`map_name`、`output_bin` 为本次确认值。旧 `Util/BuildTools/Import.py::build_binary_for_tm(package_name,dirname,maps)` 使用相同 API 并写 `Unreal/CarlaUnreal/Content/<Package>/Maps/<Map>/TM/<Map>.bin`；可复用其路径契约，但完整 Import.py 的 UE4_ROOT/UE4Editor launcher 未适配，不能运行整链制造 TM cache。当前 Python 绑定明确存在 cook_in_memory_map；缺此方法说明 wheel 不匹配，交 connection/Python build，不偷换上游 wheel。

产物：精确 bin 路径/大小、代码与 XODR 身份、执行日志；检查新输出确实出现，不覆盖有用旧 cache 直到生成成功。没有 return 状态时以异常、日志与输出共同判断。静态成功或 bin 非空不证明 TM 可加载/车辆行为正确；需要 runtime 验证另行授权。失败恢复本次 bin，不重导地图资产。

路由：运行时 TM → `carla-traffic-manager`；地图语义 → `carla-map`；Walker → `carla-navmesh`；cook/package → 对应工程 skill。

Source：`Util/BuildTools/Import.py` 的 build_binary_for_tm；`PythonAPI/carla/src/Map.cpp` 的 Map(name,xodr_content)/cook_in_memory_map；`LibCarla/source/carla/client/Map.cpp`。
