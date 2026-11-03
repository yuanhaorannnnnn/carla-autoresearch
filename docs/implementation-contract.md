# Implementation contract

Approved baseline: CARLA sprint42 2075f526dec86362fe058a6fff939e6832876759.
Single plugin; domain skills follow the Lark pattern of help/schema first,
explicit domain routing, and composable atomic operations. No CARLA build/release.

The approved granular catalog now owns skill boundaries (see
`skill-catalog-sprint42.md`). SKILL metadata distinguishes wrapped CLI operations,
native API workflows, and conditional engineering paths. A native workflow cannot
take over a CLI/research lease or bypass an ownership/episode rejection. Research
continues to use the shared bridge and capture controller only.

## Shared interface

Controller package: src/carla_agent, Python >=3.10, stdlib only initially.
Worker: src/carla_agent/worker.py, directly runnable on Python >=3.8, stdlib +
the user's matching carla wheel. It must not import the controller.

Worker protocol: JSON stdin object `{operation, profile, parameters, output_dir}`;
JSON stdout `{ok: true, result: {...}}` or
`{ok: false, error: {code, message, details}}`. Diagnostic logs go to stderr.
Exit 0 success, nonzero failure. No simulation process is started automatically.

Profile: schema_version=1, client_python absolute executable, host default
127.0.0.1, port default2000, timeout_seconds default10, output_root absolute,
session_policy inspect_only or exclusive, expected_server_version optional for
read-only and required for mutations, capability_profile standard/custom-mems,
server_pid optional for basic operations but required for research identity.
Unknown fields rejected by controller. No embedded shell commands.

Operations (CLI uses spaces in place of the dot; 17 base operations):
- connection.doctor: import/client/server diagnostics; no mutation.
- world.inspect: current map, settings, snapshot/frame/time.
- blueprints.list: filter string, default `*`.
- actors.list: filter string, default `*`.
- sensors.describe: blueprint string, inspect attributes.
- map.inspect: limit integer 1..500, default20; current map and indexed spawn
  points, no map loading or tick.
- weather.inspect: numeric fields actually exposed by the current weather object;
  an explicit allowlist includes sprint42 snow/environment lighting fields.
- actors.inspect: actor_id; transform/velocity/acceleration and bounding_box when
  exposed; no session creation or mutation.
- spectator.inspect: current spectator transform only.
- vehicle.control: session_id, actor_id, control object with throttle/brake [0,1],
  steer [-1,1], hand_brake/reverse/manual_gear_shift booleans, gear int32 >=-1;
  omitted fields use neutral defaults. Owned vehicle only, no implicit tick;
  submitted=true means the RPC returned, not proof of physics advancement.
- session.open: fixed_delta_seconds number default0.05, expected_map optional;
  require exclusive policy/version, record original settings and episode identity,
  acquire instance lock; never load another map. Return session_id.
- session.close: session_id; remove only owned actors, restore only if ownership
  and world identity still match; no killing the borrowed server.
- actors.spawn: session_id, blueprint string, spawn_index int default0;
  return actor_id, persist ownership before later operations.
- actors.destroy: session_id, actor_id; refuse actors outside this session.
- sensors.attach: session_id, parent_id (owned actor), blueprint, attributes dict,
  transform optional `{x,y,z,pitch,yaw,roll}` in CARLA meters/degrees; default z2.5.
- world.tick: session_id, frames int default1, bounded.
- capture.run: recipe object; one owned vehicle and sensor, bounded frames/warmup,
  default fixed step0.05, map required, sensor_blueprint required,
  sensor_attributes dict, vehicle_blueprint optional, spawn_index default0,
  frames default10, warmup_frames default2. RGB and RayCast LiDAR supported;
  MEMS only explicit profile with capabilities. Sensor/frame matching, bounded
  timeout/queue, persist raw outputs and frame/timestamp/receive timing. Clean up
  owned resources on errors; no claims of cleanup across changed episodes.

Recipe validation belongs to worker; controller validates operation shape before
invoking worker. Worker must defensively validate mutation fields too.

Skill discovery is offline: `skills list [--query TEXT] [--category GROUP]
[--execution MODE]` and `skills show NAME`. The generated package index contains
the description, primary execution path, real wrapped operation subset and
plugin-relative SKILL path; it does not claim runtime support or load CARLA.
`scripts/update_skill_catalog.py --check` checks metadata, operation references,
portable Markdown links and index freshness (PyYAML is a dev-only dependency).

Research commands add two read-only paths to the existing controller:
- `research validate --plan FILE`: plan/profile validation and trial budget
  quantities only; no simulator query, run creation or file writes.
- `research compare --run ABS_DIR`: terminal-run frozen-input/artifact checks
  and recomparison, taking a shared lock on the existing writer.lock; no server
  required and no writes. Partial terminal runs remain not_evaluated overall.
The existing start/status/stop/resume/report commands remain compatible.

Main agent owns protocol.py, bridge.py, cli.py, __init__/__main__, pyproject,
migration and root documentation. Worker agent owns worker.py and tests/test_worker.py.
Skills agent owns skills/, references/ and evals/skills cases, not root CLI.
Research later owns research.py and tests/test_research.py, composes bridge.invoke:
`invoke(profile: dict, operation: str, parameters: dict, output_dir: Path|None)`
returns result dict or raises protocol.AgentError(code,message,exit_code=4,details=None).
`load_profile(path)` returns validated dict. No component edits another's files.
