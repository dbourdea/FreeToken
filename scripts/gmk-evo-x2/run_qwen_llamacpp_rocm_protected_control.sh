#!/usr/bin/env bash
# Run a same-model ROCm llama.cpp control while protecting the normal Qwen API.
#
# The controller uses only isolated loopback endpoints. It proves a real normal
# completion before releasing the GPU, delegates matching single and four-client
# workloads to llama.cpp, and restores a real normal completion through an EXIT
# trap on success, error, or interruption. It deliberately does not change swap
# policy or require an interactive sudo credential.

set -euo pipefail

# Require an immutable caller-owned evidence root and retain fixed host paths.
readonly ARTIFACT_DIR="${1:?usage: run_qwen_llamacpp_rocm_protected_control.sh ARTIFACT_DIR}"
readonly ROOT_DIR="/home/david/freetoken-amd"
# Permit a caller to name the current isolated source that supplies both the
# llama.cpp control and matching benchmark harness. The default preserves the
# historical harness checkout for installations that still use its layout.
readonly SOURCE_DIR="${FREETOKEN_LLAMA_CONTROL_SOURCE_DIR:-${ROOT_DIR}/source-qwen-harness-d6ee8ce}"
readonly RECOVERY_SOURCE="${ROOT_DIR}/source-qwen-recovery-d6ee8cef479c"
readonly CONTROL_SCRIPT="${SOURCE_DIR}/scripts/gmk-evo-x2/run_qwen_llamacpp_rocm_control.sh"
readonly NORMAL_STOP="${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh"
readonly NORMAL_START="${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh"
readonly NORMAL_REQUEST='{"model":"qwen3.6-35b-a3b-nvfp4-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":4,"temperature":0,"stream":false}'

# Refuse collision or incomplete static setup before touching the normal API.
[[ ! -e "${ARTIFACT_DIR}" ]] || { echo "artifact directory already exists: ${ARTIFACT_DIR}" >&2; exit 2; }
for required in "${CONTROL_SCRIPT}" "${NORMAL_STOP}" "${NORMAL_START}" \
    "${SOURCE_DIR}/benchmarks/gmk_evo_x2/run_concurrent_api_control.py"; do
    [[ -f "${required}" ]] || { echo "missing required file: ${required}" >&2; exit 2; }
done
mkdir -p "${ARTIFACT_DIR}"

# Retain every completion body while returning a concise status for lifecycle gates.
normal_status() {
    local output="$1"
    curl -sS -m 45 -o "${output}" -w '%{http_code}' -H 'Content-Type: application/json' \
        -d "${NORMAL_REQUEST}" http://127.0.0.1:1919/v1/chat/completions
}

# Restore from the protected recovery checkout and require a true completion.
recover_normal_service() {
    "${NORMAL_START}" >"${ARTIFACT_DIR}/recovery-start.txt" 2>&1 || true
    for attempt in $(seq 1 600); do
        code="$(normal_status "${ARTIFACT_DIR}/recovery-probe.json" || true)"
        if [[ "${code}" == "200" ]]; then
            printf 'normal_api_ready=1 attempts=%s\n' "${attempt}" >"${ARTIFACT_DIR}/cleanup.txt"
            return 0
        fi
        printf 'attempt=%s status=%s\n' "${attempt}" "${code}" >>"${ARTIFACT_DIR}/recovery-progress.txt"
        sleep 1
    done
    printf 'normal_api_ready=0 attempts=600\n' >"${ARTIFACT_DIR}/cleanup.txt"
    return 1
}

# Own recovery only after all static validation has passed.
trap recover_normal_service EXIT
preflight_code="$(normal_status "${ARTIFACT_DIR}/preflight.json" || true)"
[[ "${preflight_code}" == "200" ]] || { echo "normal API unavailable before llama.cpp control: ${preflight_code}" >&2; exit 1; }
"${NORMAL_STOP}" >"${ARTIFACT_DIR}/normal-stop.txt" 2>&1

# Run the existing exact Q4_K_M ROCm 10 control plus deterministic visible-output
# and synchronized C4 measurement in its own artifact directory.
GMK_EVO_X2_QWEN_QUALITY_SUITE=1 GMK_EVO_X2_QWEN_CONCURRENT_CLIENTS=4 \
GMK_EVO_X2_LLAMA_PARALLEL_SLOTS=4 \
GMK_EVO_X2_QWEN_COLD_PREFILL_CONTROL="${GMK_EVO_X2_QWEN_COLD_PREFILL_CONTROL:-0}" \
    bash "${CONTROL_SCRIPT}" "${ARTIFACT_DIR}/llamacpp-control" \
    >"${ARTIFACT_DIR}/llamacpp-control.log" 2>&1
printf 'llamacpp_quality_scheduler_and_concurrent=passed\n' >"${ARTIFACT_DIR}/result.txt"
