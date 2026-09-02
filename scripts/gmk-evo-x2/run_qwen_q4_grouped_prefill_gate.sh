#!/usr/bin/env bash
# Gate an opt-in grouped Q4_K/Q5_K long-prefill MoE candidate on GMKtec EVO-X2.
#
# This controller proves a real completion from the protected normal service,
# stops it only after that preflight, runs vector and grouped component screens
# on the original Qwen Q4_K_M expert bytes, and restores a completion-capable
# normal service on every exit path.  It is intentionally not an API-TPS claim:
# only a parity-passing component winner can advance to a protected API gate.

set -euo pipefail

# The caller must provide a new directory.  The controller creates it itself so
# an accidental pre-created directory cannot invalidate immutable evidence.
readonly ARTIFACT_DIR="${1:?usage: run_qwen_q4_grouped_prefill_gate.sh ARTIFACT_DIR}"
readonly SOURCE_DIR="${FREETOKEN_Q4_SOURCE_DIR:?set FREETOKEN_Q4_SOURCE_DIR}"
readonly ROOT_DIR="/home/david/freetoken-amd"
readonly RECOVERY_SOURCE="${ROOT_DIR}/source-qwen-recovery-d6ee8cef479c"
readonly MODEL_PATH="${ROOT_DIR}/models/controls/qwen36-35b-a3b-unsloth-a483e9e6/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
readonly BENCHMARK="${SOURCE_DIR}/benchmarks/gmk_evo_x2/bench_qwen_q4_grouped_prefill.py"
readonly EXTENSION_CACHE="${ROOT_DIR}/cache/torch_extensions-q4-grouped-prefill-f1baf13"
readonly TRITON_CACHE="${ROOT_DIR}/cache/triton-q4-grouped-prefill-f1baf13"
readonly NORMAL_REQUEST='{"model":"qwen3.6-35b-a3b-nvfp4-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":4,"temperature":0,"stream":false}'

[[ ! -e "${ARTIFACT_DIR}" ]] || { echo "artifact directory already exists: ${ARTIFACT_DIR}" >&2; exit 2; }
mkdir -p "${ARTIFACT_DIR}"

# Return an HTTP status only while retaining the full completion response for
# recovery evidence and human inspection.
normal_status() {
    local output="$1"
    curl -sS -m 45 -o "${output}" -w '%{http_code}' \
        -H 'Content-Type: application/json' -d "${NORMAL_REQUEST}" \
        http://127.0.0.1:1919/v1/chat/completions
}

# Restore the protected service even if an extension build, Triton compilation,
# parity assertion, or timing run fails.  A models-list probe is insufficient:
# recovery requires a real completion response.
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

# Validate every static prerequisite before taking ownership of service recovery.
for required in "${MODEL_PATH}" "${BENCHMARK}" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh"; do
    [[ -f "${required}" ]] || { echo "missing required file: ${required}" >&2; exit 2; }
done

trap recover_normal_service EXIT

# Do not interrupt an already unhealthy production service.
preflight_code="$(normal_status "${ARTIFACT_DIR}/preflight.json" || true)"
[[ "${preflight_code}" == "200" ]] || { echo "normal API unavailable before grouped gate: ${preflight_code}" >&2; exit 1; }
"${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh" \
    >"${ARTIFACT_DIR}/normal-stop.txt" 2>&1
mkdir -p "${EXTENSION_CACHE}" "${TRITON_CACHE}"

# The vector reference keeps grouped dispatch disabled.  It builds and warms
# the native extension before events begin, producing an output artifact for
# the candidate parity assertion.
PYTHONPATH="${SOURCE_DIR}/python" TORCH_EXTENSIONS_DIR="${EXTENSION_CACHE}" \
TRITON_CACHE_DIR="${TRITON_CACHE}" PYTORCH_ROCM_ARCH=gfx1151 \
FREETOKEN_Q4_GROUPED_PREFILL_MIN_TOKENS=0 \
"${ROOT_DIR}/.venv/bin/python" "${BENCHMARK}" \
    --model "${MODEL_PATH}" --mode vector --tokens 1024 --warmup 8 --repetitions 20 \
    --json "${ARTIFACT_DIR}/vector.json" --save-output "${ARTIFACT_DIR}/vector-output.pt" \
    >"${ARTIFACT_DIR}/vector.log" 2>&1

# The grouped run compiles and warms route alignment before timing.  It must
# match the saved vector output under explicit tolerances before it can record
# a passed component result.
PYTHONPATH="${SOURCE_DIR}/python" TORCH_EXTENSIONS_DIR="${EXTENSION_CACHE}" \
TRITON_CACHE_DIR="${TRITON_CACHE}" PYTORCH_ROCM_ARCH=gfx1151 \
FREETOKEN_Q4_GROUPED_PREFILL_MIN_TOKENS=1024 \
"${ROOT_DIR}/.venv/bin/python" "${BENCHMARK}" \
    --model "${MODEL_PATH}" --mode grouped --tokens 1024 --warmup 8 --repetitions 20 \
    --json "${ARTIFACT_DIR}/grouped.json" --reference-output "${ARTIFACT_DIR}/vector-output.pt" \
    >"${ARTIFACT_DIR}/grouped.log" 2>&1

# A passed marker means both runs completed, grouped output matched the saved
# vector reference, and timing evidence exists.  It makes no API claim.
printf 'real_q4_grouped_prefill_parity_and_timing=passed\n' >"${ARTIFACT_DIR}/result.txt"
