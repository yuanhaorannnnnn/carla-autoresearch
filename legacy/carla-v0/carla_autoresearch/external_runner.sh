#!/usr/bin/env bash
set -eo pipefail

# Async server + benchmark launcher for autoresearch-loop.
# Launched in gnome-terminal (non-blocking to LLM process).
# The LLM polls STATUS_FILE to check completion.
#
# Usage: external_runner.sh <workspace> <status_file>
# Environment overrides (optional):
#   SERVER_SCRIPT    - path to CarlaUnreal.sh (default: see below)
#   CONDA_SH         - path to conda.sh (default: /home/lkshpc/anaconda3/etc/profile.d/conda.sh)
#   CONDA_ENV        - conda env name (default: py38)
#   BENCHMARK_DIR    - directory containing carla_autoresearch (default: /media/yhr/2T/autoresearch)
#   HOST, PORT, TOWN - server connection params
#   SENSOR_BLUEPRINT - lidar blueprint name
#   WARMUP_SCANS     - warmup scan count
#   MEASURED_SCANS   - measured scan count

WORKSPACE="${1:?Usage: $0 <workspace> <status_file>}"
STATUS_FILE="${2:?Usage: $0 <workspace> <status_file>}"

SERVER_SCRIPT="${SERVER_SCRIPT:-/media/yhr/2T/CarlaUE5/Build/Package/Carla-0.10.0-Linux-Shipping/Linux/CarlaUnreal.sh}"
CONDA_SH="${CONDA_SH:-/home/lkshpc/anaconda3/etc/profile.d/conda.sh}"
CONDA_ENV="${CONDA_ENV:-py38}"
BENCHMARK_DIR="${BENCHMARK_DIR:-/media/yhr/2T/autoresearch}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-2000}"
TOWN="${TOWN:-Town05}"
SENSOR_BLUEPRINT="${SENSOR_BLUEPRINT:-sensor.lidar.ray_cast_mems}"
WARMUP_SCANS="${WARMUP_SCANS:-20}"
MEASURED_SCANS="${MEASURED_SCANS:-100}"
SERVER_TIMEOUT="${SERVER_TIMEOUT:-60}"
BENCHMARK_TIMEOUT="${BENCHMARK_TIMEOUT:-180}"

mkdir -p "$WORKSPACE"
SERVER_LOG="$WORKSPACE/server.log"
BENCHMARK_LOG="$WORKSPACE/benchmark.log"
METRICS_PATH="$WORKSPACE/metrics.json"

write_status() {
    local state="$1"
    local reason="${2:-}"
    if [[ -n "$reason" ]]; then
        printf '{"state": "%s", "reason": "%s"}\n' "$state" "$reason" > "$STATUS_FILE"
    else
        printf '{"state": "%s"}\n' "$state" > "$STATUS_FILE"
    fi
}

# ---------- 1. Start server ----------
write_status "starting_server"

# Kill any existing server on the same port to avoid conflicts
fuser -k "${PORT}/tcp" 2>/dev/null || true

nohup bash -lc "cd $(dirname "$SERVER_SCRIPT") && ./$(basename "$SERVER_SCRIPT")" > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!

echo "[external_runner] Server PID: $SERVER_PID"
echo "[external_runner] Waiting for server ready (timeout ${SERVER_TIMEOUT}s)..."

server_ready=false
for ((i=0; i<SERVER_TIMEOUT; i++)); do
    if grep -q "Initialized CarlaServer" "$SERVER_LOG" 2>/dev/null && \
       grep -q "LoadMap Load map complete" "$SERVER_LOG" 2>/dev/null; then
        server_ready=true
        break
    fi
    sleep 1
done

if [[ "$server_ready" != true ]]; then
    write_status "failed" "server failed to start within ${SERVER_TIMEOUT}s"
    kill "$SERVER_PID" 2>/dev/null || true
    exit 1
fi

echo "[external_runner] Server ready."

# ---------- 2. Run benchmark ----------
write_status "running_benchmark"

BENCHMARK_CMD=(
    python3 -m carla_autoresearch.benchmark_client
    --host "$HOST"
    --port "$PORT"
    --sensor-blueprint "$SENSOR_BLUEPRINT"
    --map "$TOWN"
    --warmup-scans "$WARMUP_SCANS"
    --measured-scans "$MEASURED_SCANS"
    --output "$METRICS_PATH"
    --lidar-attr "range=200"
    --lidar-attr "simu_brdf=true"
    --lidar-attr "channels=64"
    --lidar-attr "beams_num=153600"
    --lidar-attr "scanning_patterns=scanningPattern_AT128.csv"
    --lidar-attr "rotation_frequency=10.0"
    --lidar-attr "noise_seed=0"
    --lidar-attr "noise_stddev=0.0"
    --lidar-attr "dropoff_general_rate=0.0"
    --lidar-attr "dropoff_zero_intensity=0.0"
    --lidar-attr "dropoff_intensity_limit=1.0"
)

echo "[external_runner] Running benchmark..."
bash -lc "
    source $(printf '%q' "$CONDA_SH")
    conda activate $(printf '%q' "$CONDA_ENV")
    cd $(printf '%q' "$BENCHMARK_DIR")
    ${BENCHMARK_CMD[*]} > $(printf '%q' "$BENCHMARK_LOG") 2>&1
" &
BENCH_PID=$!

bench_ok=false
for ((i=0; i<BENCHMARK_TIMEOUT; i++)); do
    if ! kill -0 "$BENCH_PID" 2>/dev/null; then
        wait "$BENCH_PID"
        bench_exit=$?
        if [[ $bench_exit -eq 0 && -f "$METRICS_PATH" ]]; then
            bench_ok=true
        fi
        break
    fi
    sleep 1
done

# Kill benchmark process if still running after timeout
if kill -0 "$BENCH_PID" 2>/dev/null; then
    kill "$BENCH_PID" 2>/dev/null || true
    wait "$BENCH_PID" 2>/dev/null || true
fi

# ---------- 3. Stop server ----------
echo "[external_runner] Stopping server (PID $SERVER_PID)..."
kill "$SERVER_PID" 2>/dev/null || true
wait "$SERVER_PID" 2>/dev/null || true

# ---------- 4. Write final status ----------
if [[ "$bench_ok" == true ]]; then
    write_status "success"
    echo "[external_runner] Benchmark completed successfully."
else
    write_status "failed" "benchmark did not complete successfully"
    echo "[external_runner] Benchmark failed."
    exit 1
fi
