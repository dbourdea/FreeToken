#!/usr/bin/env bash
# Gate the real Q4_K_M full-layer prefill-copy candidate on exact byte parity.
#
# This controller stops the protected normal API only after a successful real
# completion, runs both legacy and fused mapped-host components from separate
# native-extension caches, and restores a completion-capable normal API on all
# exit paths.  It does not claim end-to-end TPS: a candidate can proceed to that
# later stage only if it wins this transfer-specific gate without changing bytes.

set -euo pipefail

# Require a caller-owned unique artifact directory for every log and result.
readonly ARTIFACT_DIR="${1:?usage: run_qwen_q4_prefill_copy_gate.sh ARTIFACT_DIR}"
# Require an isolated Qwen-capable candidate source rather than the protected
# normal service checkout.
readonly SOURCE_DIR="${FREETOKEN_Q4_SOURCE_DIR:?set FREETOKEN_Q4_SOURCE_DIR}"
# Keep all host-local dependencies outside a candidate Git worktree.
readonly ROOT_DIR="/home/david/freetoken-amd"
# Restore only from the explicitly protected normal-service source.
readonly RECOVERY_SOURCE="${ROOT_DIR}/source-qwen-recovery-d6ee8cef479c"
# Keep the model fixed so benchmark bytes and quant geometry remain comparable.
readonly MODEL_PATH="${ROOT_DIR}/models/controls/qwen36-35b-a3b-unsloth-a483e9e6/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
# Use one exact normal completion for preflight and recovery verification.
readonly NORMAL_REQUEST='{"model":"qwen3.6-35b-a3b-nvfp4-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":4,"temperature":0,"stream":false}'
# Separate caches prevent one candidate's HIP compilation from making the other
# appear faster and preserve reproducible compiler provenance.
readonly LEGACY_CACHE="${ROOT_DIR}/cache/torch_extensions-q4-prefill-copy-legacy"
readonly FUSED_CACHE="${ROOT_DIR}/cache/torch_extensions-q4-prefill-copy-fused"
readonly BENCHMARK="${SOURCE_DIR}/benchmarks/gmk_evo_x2/bench_qwen_q4_prefill_copy.py"

# Return only the HTTP status of a real completion while saving the response body.
normal_status() {
    local output="$1"
    curl -sS -m 45 -o "${output}" -w '%{http_code}' \
        -H 'Content-Type: application/json' -d "${NORMAL_REQUEST}" \
        http://127.0.0.1:1919/v1/chat/completions
}

# Restore the normal endpoint and wait for a completed request, including on
# interruption, compiler failure, parity failure, or unexpected shell error.
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

# Verify all static prerequisites before taking ownership of the protected GPU.
for required in "${MODEL_PATH}" "${BENCHMARK}" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh"; do
    [[ -f "${required}" ]] || { echo "missing required file: ${required}" >&2; exit 2; }
done
[[ "${SOURCE_DIR}" == "${ROOT_DIR}/source-qwen-"* ]] || {
    echo "candidate source must be an isolated Qwen checkout" >&2
    exit 2
}
[[ ! -e "${ARTIFACT_DIR}" ]] || { echo "artifact directory already exists" >&2; exit 2; }
mkdir -p "${ARTIFACT_DIR}" "${LEGACY_CACHE}" "${FUSED_CACHE}"

# Install recovery before preflight and do not interrupt an already-unhealthy API.
trap recover_normal_service EXIT
preflight_code="$(normal_status "${ARTIFACT_DIR}/preflight.json" || true)"
[[ "${preflight_code}" == "200" ]] || {
    echo "normal API unavailable before prefill-copy gate: ${preflight_code}" >&2
    exit 1
}
"${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh" \
    >"${ARTIFACT_DIR}/normal-stop.txt" 2>&1

# Establish the real-weight legacy timing and exact destination-byte reference.
PYTHONPATH="${SOURCE_DIR}/python" TORCH_EXTENSIONS_DIR="${LEGACY_CACHE}" \
PYTORCH_ROCM_ARCH=gfx1151 FREETOKEN_PREFILL_FUSED_MAPPED_COPY=0 \
"${ROOT_DIR}/.venv/bin/python" "${BENCHMARK}" \
    --model "${MODEL_PATH}" --mode legacy --warmup 5 --repetitions 30 \
    --save-reference "${ARTIFACT_DIR}/legacy-output.pt" --json "${ARTIFACT_DIR}/legacy.json" \
    >"${ARTIFACT_DIR}/legacy.log" 2>&1

# Measure the candidate only after requiring its active fused path and compare
# every destination byte to the independent legacy result.
PYTHONPATH="${SOURCE_DIR}/python" TORCH_EXTENSIONS_DIR="${FUSED_CACHE}" \
PYTORCH_ROCM_ARCH=gfx1151 FREETOKEN_PREFILL_FUSED_MAPPED_COPY=1 \
"${ROOT_DIR}/.venv/bin/python" "${BENCHMARK}" \
    --model "${MODEL_PATH}" --mode fused --warmup 5 --repetitions 30 \
    --reference "${ARTIFACT_DIR}/legacy-output.pt" --json "${ARTIFACT_DIR}/fused.json" \
    >"${ARTIFACT_DIR}/fused.log" 2>&1

# Record only completed, exact-parity candidate evidence.  A subsequent API
# campaign must still independently establish quality and end-to-end prefill TPS.
printf 'real_q4_prefill_copy_parity_and_timing=passed\n' >"${ARTIFACT_DIR}/result.txt"
