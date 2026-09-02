#!/usr/bin/env bash
# Gate an eight-route HIP Q4_K/Q5_K vector-block candidate on GMKtec EVO-X2.
#
# The candidate preserves each route's packed-weight reads and XOR reduction,
# but schedules eight independent routes in one hardware block.  This script
# measures the actual Qwen GGUF tensors through the established component
# harness, requires elementwise output parity before a timing result can pass,
# and restores the protected normal API after every outcome.

set -euo pipefail

# Require a new caller-selected artifact directory so this run cannot overwrite
# evidence from the previous baseline or candidate component screen.
readonly ARTIFACT_DIR="${1:?usage: run_qwen_q4_route_block_gate.sh ARTIFACT_DIR}"
readonly SOURCE_DIR="${FREETOKEN_Q4_SOURCE_DIR:?set FREETOKEN_Q4_SOURCE_DIR}"
readonly ROOT_DIR="/home/david/freetoken-amd"
readonly RECOVERY_SOURCE="${ROOT_DIR}/source-qwen-recovery-d6ee8cef479c"
readonly MODEL_PATH="${ROOT_DIR}/models/controls/qwen36-35b-a3b-unsloth-a483e9e6/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
readonly BENCHMARK="${SOURCE_DIR}/benchmarks/gmk_evo_x2/bench_qwen_q4k_q5k_moe_kernel.py"
readonly BASE_CACHE="${ROOT_DIR}/cache/torch_extensions-q4-route-block-one"
readonly CANDIDATE_CACHE="${ROOT_DIR}/cache/torch_extensions-q4-route-block-eight"
readonly NORMAL_REQUEST='{"model":"qwen3.6-35b-a3b-nvfp4-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":4,"temperature":0,"stream":false}'

[[ ! -e "${ARTIFACT_DIR}" ]] || { echo "artifact directory already exists: ${ARTIFACT_DIR}" >&2; exit 2; }
mkdir -p "${ARTIFACT_DIR}"

# A real completion is the lifecycle criterion, rather than an endpoint that
# can be live before its scheduler and model are usable.
normal_status() {
    local output="$1"
    curl -sS -m 45 -o "${output}" -w '%{http_code}' \
        -H 'Content-Type: application/json' -d "${NORMAL_REQUEST}" \
        http://127.0.0.1:1919/v1/chat/completions
}

# The EXIT guard owns recovery only after static checks pass.  It waits for a
# completion response, preserving an auditable retry count whether the kernel
# build, parity comparison, or device timing succeeds or fails.
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

# Validate every source and recovery input before the normal service is stopped.
for required in "${MODEL_PATH}" "${BENCHMARK}" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh"; do
    [[ -f "${required}" ]] || { echo "missing required file: ${required}" >&2; exit 2; }
done

trap recover_normal_service EXIT
preflight_code="$(normal_status "${ARTIFACT_DIR}/preflight.json" || true)"
[[ "${preflight_code}" == "200" ]] || { echo "normal API unavailable before route-block gate: ${preflight_code}" >&2; exit 1; }
"${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh" \
    >"${ARTIFACT_DIR}/normal-stop.txt" 2>&1
mkdir -p "${BASE_CACHE}" "${CANDIDATE_CACHE}"

# Establish exact outputs and device timing for the one-route reference build.
PYTHONPATH="${SOURCE_DIR}/python" TORCH_EXTENSIONS_DIR="${BASE_CACHE}" \
PYTORCH_ROCM_ARCH=gfx1151 FREETOKEN_GGUF_MOE_ROUTE_BLOCK=1 \
"${ROOT_DIR}/.venv/bin/python" "${BENCHMARK}" \
    --model "${MODEL_PATH}" --warmup 30 --repetitions 300 \
    --json "${ARTIFACT_DIR}/baseline.json" --save-output "${ARTIFACT_DIR}/baseline-output.pt" \
    >"${ARTIFACT_DIR}/baseline.log" 2>&1

# Rebuild the candidate in a distinct cache and reject it immediately if any
# Q4_K gate/up or Q5_K down result differs from the saved reference tensors.
PYTHONPATH="${SOURCE_DIR}/python" TORCH_EXTENSIONS_DIR="${CANDIDATE_CACHE}" \
PYTORCH_ROCM_ARCH=gfx1151 FREETOKEN_GGUF_MOE_ROUTE_BLOCK=8 \
"${ROOT_DIR}/.venv/bin/python" "${BENCHMARK}" \
    --model "${MODEL_PATH}" --warmup 30 --repetitions 300 \
    --json "${ARTIFACT_DIR}/candidate.json" --reference-output "${ARTIFACT_DIR}/baseline-output.pt" \
    >"${ARTIFACT_DIR}/candidate.log" 2>&1

# This marker certifies real tensors, output comparison, and both timing files.
# It does not make an API-TPS or production-eligibility claim.
printf 'q4_route_block_component_parity_and_timing=passed\n' >"${ARTIFACT_DIR}/result.txt"
