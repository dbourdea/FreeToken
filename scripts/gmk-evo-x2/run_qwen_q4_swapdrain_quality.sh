#!/usr/bin/env bash
# Qualify an isolated Q4 candidate after a reversible host swap drain.
#
# The controller exists for candidate residency diagnostics only.  It verifies
# the normal loopback API, stops it through its recovery helper, disables swap
# temporarily, starts the isolated Q4 server, runs one deterministic quality
# session, then restores swap and the normal API on every exit path.

set -euo pipefail

# Require a fresh evidence directory and an explicit isolated Qwen checkout.
readonly ARTIFACT_DIR="${1:?usage: run_qwen_q4_swapdrain_quality.sh ARTIFACT_DIR SOURCE_DIR}"
readonly SOURCE_DIR="${2:?usage: run_qwen_q4_swapdrain_quality.sh ARTIFACT_DIR SOURCE_DIR}"
# Keep all fixed host paths explicit for auditability and recovery safety.
readonly ROOT_DIR="/home/david/freetoken-amd"
readonly NORMAL_SOURCE_DIR="${ROOT_DIR}/source-qwen-c06-fc3346f"
readonly LAUNCHER="${ROOT_DIR}/source-qwen-bench-metrics-f1baf13/scripts/gmk-evo-x2/launch_qwen_gguf_qualified.sh"
readonly NORMAL_STARTER="${NORMAL_SOURCE_DIR}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh"
readonly NORMAL_STOPPER="${NORMAL_SOURCE_DIR}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh"
readonly QUALITY_RUNNER="${SOURCE_DIR}/scripts/gmk-evo-x2/run_qwen_gguf_endurance_battery.sh"
readonly EXTENSION_CACHE="${ROOT_DIR}/cache/torch_extensions-mmv-y4-05751ef"

# Remember which reversible host changes this controller owns.
normal_stopped=0
swap_disabled=0
original_swappiness=""

# Restore all scoped state even when a startup, quality, or signal failure occurs.
cleanup() {
    local status="$?"
    set +e
    FREETOKEN_Q4_SOURCE_DIR="${SOURCE_DIR}" FREETOKEN_Q4_EXTENSION_CACHE_DIR="${EXTENSION_CACHE}" \
        bash "${LAUNCHER}" stop "${ARTIFACT_DIR}" 0.25 0
    if [[ "${swap_disabled}" == "1" ]]; then
        sudo -n swapon -a
    fi
    if [[ "${normal_stopped}" == "1" ]]; then
        bash "${NORMAL_STARTER}" "${ARTIFACT_DIR}/normal-recovery"
    fi
    printf 'exit_status=%s\nrestored_swappiness=%s\n' "${status}" "${original_swappiness}" \
        >"${ARTIFACT_DIR}/cleanup.txt"
    exit "${status}"
}

trap cleanup EXIT INT TERM

# Reject unknown source paths and non-empty artifact directories before change.
[[ "${SOURCE_DIR}" == "${ROOT_DIR}/source-qwen-"* ]] || { echo "invalid source directory" >&2; exit 2; }
[[ ! -e "${ARTIFACT_DIR}" ]] || { echo "artifact directory already exists" >&2; exit 2; }
mkdir -p "${ARTIFACT_DIR}"

# Prove the protected service is healthy before claiming the GPU time-share slot.
curl -fsS --max-time 8 http://127.0.0.1:1919/v1/models >"${ARTIFACT_DIR}/normal-health-before.json"
original_swappiness="$(cat /proc/sys/vm/swappiness)"
printf 'original_swappiness=%s\n' "${original_swappiness}" >"${ARTIFACT_DIR}/swap-policy.txt"

# Stop the normal API, drain existing swapped pages, and retain capacity evidence.
bash "${NORMAL_STOPPER}"
normal_stopped=1
sudo -n swapoff -a
swap_disabled=1
free -h >"${ARTIFACT_DIR}/memory-after-swapoff.txt"

# Start the default-off four-row candidate with its isolated native cache.
FREETOKEN_Q4_SOURCE_DIR="${SOURCE_DIR}" FREETOKEN_Q4_EXTENSION_CACHE_DIR="${EXTENSION_CACHE}" \
FREETOKEN_GGUF_MMV_Y=4 bash "${LAUNCHER}" start "${ARTIFACT_DIR}" 0.25 0

# Wait for scheduler readiness, because the frontend models route appears early.
for _ in $(seq 1 120); do
    rg -Fq 'API server is ready to serve' "${ARTIFACT_DIR}/server.log" && break
    sleep 2
done
rg -Fq 'API server is ready to serve' "${ARTIFACT_DIR}/server.log"

# Run the canonical deterministic state suite and its process-scoped swap gate.
FREETOKEN_Q4_SOURCE_DIR="${SOURCE_DIR}" bash "${QUALITY_RUNNER}" "${ARTIFACT_DIR}/quality" 1 0
