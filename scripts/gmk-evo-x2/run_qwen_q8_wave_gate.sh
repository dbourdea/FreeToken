#!/usr/bin/env bash
# Gate one intermediate dense-Q8 HIP wave count and restore the normal API.
#
# This controller protects the normal GMKtec EVO-X2 service by requiring a real
# completion before it stops that service and by owning a completion-based
# recovery trap. It first records one-wave real-tensor reference outputs, then
# runs exactly one requested two- or four-wave candidate in a separate native
# extension cache. Candidate timing exists only when both Qwen dense tensors
# pass the configured numerical parity test.

set -euo pipefail

readonly ARTIFACT_DIR="${1:?usage: run_qwen_q8_wave_gate.sh ARTIFACT_DIR WAVE_COUNT}"
readonly WAVE_COUNT="${2:?usage: run_qwen_q8_wave_gate.sh ARTIFACT_DIR WAVE_COUNT}"
readonly SOURCE_DIR="${FREETOKEN_Q8_SOURCE_DIR:?set FREETOKEN_Q8_SOURCE_DIR}"
readonly ROOT_DIR="/home/david/freetoken-amd"
readonly RECOVERY_SOURCE="${ROOT_DIR}/source-qwen-recovery-d6ee8cef479c"
readonly MODEL_PATH="${ROOT_DIR}/models/controls/qwen36-35b-a3b-unsloth-a483e9e6/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
readonly BENCHMARK="${SOURCE_DIR}/benchmarks/gmk_evo_x2/bench_qwen_q8_wave_component.py"
readonly NORMAL_REQUEST='{"model":"qwen3.6-35b-a3b-nvfp4-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":4,"temperature":0,"stream":false}'

[[ "${WAVE_COUNT}" == "2" || "${WAVE_COUNT}" == "4" ]] || {
    echo "WAVE_COUNT must be 2 or 4" >&2
    exit 2
}
[[ ! -e "${ARTIFACT_DIR}" ]] || {
    echo "artifact directory already exists: ${ARTIFACT_DIR}" >&2
    exit 2
}
mkdir -p "${ARTIFACT_DIR}"

# Treat a full completion as readiness because the model listing endpoint can
# become available while model loading or scheduler initialization continues.
normal_status() {
    curl -sS -m 45 -o "$1" -w '%{http_code}' -H 'Content-Type: application/json' \
        -d "${NORMAL_REQUEST}" http://127.0.0.1:1919/v1/chat/completions
}

# The EXIT handler makes recovery independent of benchmark success, parity
# failure, compiler failure, or a lost interactive command connection.
recover_normal_service() {
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh" \
        >"${ARTIFACT_DIR}/recovery-start.txt" 2>&1 || true
    for attempt in $(seq 1 600); do
        code="$(normal_status "${ARTIFACT_DIR}/recovery-probe.json" || true)"
        if [[ "${code}" == "200" ]]; then
            printf 'normal_api_ready=1 attempts=%s\n' "${attempt}" >"${ARTIFACT_DIR}/cleanup.txt"
            return 0
        fi
        sleep 1
    done
    printf 'normal_api_ready=0 attempts=600\n' >"${ARTIFACT_DIR}/cleanup.txt"
    return 1
}

for required in "${MODEL_PATH}" "${BENCHMARK}" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh"; do
    [[ -f "${required}" ]] || { echo "missing required file: ${required}" >&2; exit 2; }
done

trap recover_normal_service EXIT
preflight_code="$(normal_status "${ARTIFACT_DIR}/preflight.json" || true)"
[[ "${preflight_code}" == "200" ]] || { echo "normal API unavailable: ${preflight_code}" >&2; exit 1; }
"${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh" >"${ARTIFACT_DIR}/normal-stop.txt" 2>&1

# Each specialization receives a unique cache, ensuring no binary compiled
# under the other wave count can satisfy the production-kernel import.
for tensor in blk.0.attn_qkv.weight blk.0.ssm_out.weight; do
    label="${tensor//./_}"
    PYTHONPATH="${SOURCE_DIR}/python" TORCH_EXTENSIONS_DIR="${ROOT_DIR}/cache/torch_extensions-q8-wave-one" \
    PYTORCH_ROCM_ARCH=gfx1151 FREETOKEN_GGUF_Q8_MMV_WARPS=1 \
    "${ROOT_DIR}/.venv/bin/python" "${BENCHMARK}" --model "${MODEL_PATH}" --tensor "${tensor}" \
        --json "${ARTIFACT_DIR}/baseline-${label}.json" --save-output "${ARTIFACT_DIR}/baseline-${label}.pt" \
        >"${ARTIFACT_DIR}/baseline-${label}.log" 2>&1
    PYTHONPATH="${SOURCE_DIR}/python" TORCH_EXTENSIONS_DIR="${ROOT_DIR}/cache/torch_extensions-q8-wave-${WAVE_COUNT}" \
    PYTORCH_ROCM_ARCH=gfx1151 FREETOKEN_GGUF_Q8_MMV_WARPS="${WAVE_COUNT}" \
    "${ROOT_DIR}/.venv/bin/python" "${BENCHMARK}" --model "${MODEL_PATH}" --tensor "${tensor}" \
        --json "${ARTIFACT_DIR}/candidate-${label}.json" --reference-output "${ARTIFACT_DIR}/baseline-${label}.pt" \
        >"${ARTIFACT_DIR}/candidate-${label}.log" 2>&1
done

printf 'q8_wave_component_parity_and_timing=passed wave_count=%s\n' "${WAVE_COUNT}" >"${ARTIFACT_DIR}/result.txt"
