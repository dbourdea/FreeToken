#!/usr/bin/env bash
# Screen one fused-GDN pipeline-depth candidate while protecting the normal API.
#
# The controller proves the normal API works before claiming the GPU, measures
# the qualified three-stage kernel and one bounded candidate in isolated caches,
# requires exact output and state equality, and restores a real completion on
# every exit path. It intentionally makes no API-performance claim.

set -euo pipefail

# Require an immutable caller-owned evidence directory and an isolated source.
readonly ARTIFACT_DIR="${1:?usage: run_qwen_gdn_stage_component_gate.sh ARTIFACT_DIR CANDIDATE_STAGE}"
readonly CANDIDATE_STAGE="${2:?usage: run_qwen_gdn_stage_component_gate.sh ARTIFACT_DIR CANDIDATE_STAGE}"
readonly SOURCE_DIR="${FREETOKEN_GDN_STAGE_SOURCE_DIR:?set FREETOKEN_GDN_STAGE_SOURCE_DIR}"
readonly ROOT_DIR="/home/david/freetoken-amd"
readonly RECOVERY_SOURCE="${ROOT_DIR}/source-qwen-recovery-d6ee8cef479c"
readonly MODEL_PATH="${ROOT_DIR}/models/controls/qwen36-35b-a3b-unsloth-a483e9e6/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
readonly BASE_CACHE="${ROOT_DIR}/cache/torch_extensions-gdn-stage3-f1baf13"
readonly CANDIDATE_CACHE="${ROOT_DIR}/cache/torch_extensions-gdn-stage${CANDIDATE_STAGE}-f1baf13"
readonly NORMAL_REQUEST='{"model":"qwen3.6-35b-a3b-nvfp4-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":4,"temperature":0,"stream":false}'

# Restrict this controller to the two reviewed candidates before service stop.
[[ "${CANDIDATE_STAGE}" == "2" || "${CANDIDATE_STAGE}" == "4" ]] || { echo "candidate stage must be 2 or 4" >&2; exit 2; }
[[ ! -e "${ARTIFACT_DIR}" ]] || { echo "artifact directory already exists: ${ARTIFACT_DIR}" >&2; exit 2; }
mkdir -p "${ARTIFACT_DIR}"

# Submit a real completion and return only its HTTP status for lifecycle checks.
normal_status() {
    local output="$1"
    curl -sS -m 45 -o "${output}" -w '%{http_code}' -H 'Content-Type: application/json' \
        -d "${NORMAL_REQUEST}" http://127.0.0.1:1919/v1/chat/completions
}

# Restart and prove a complete response before returning controller ownership.
recover_normal_service() {
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh" >"${ARTIFACT_DIR}/recovery-start.txt" 2>&1 || true
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

# Verify all static prerequisites before affecting the protected normal service.
for required in "${MODEL_PATH}" "${SOURCE_DIR}/benchmarks/gmk_evo_x2/bench_qwen_gdn_decode_stage.py" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh"; do
    [[ -f "${required}" ]] || { echo "missing required file: ${required}" >&2; exit 2; }
done

# Own recovery after all static checks pass, including interrupts and failures.
trap recover_normal_service EXIT
preflight_code="$(normal_status "${ARTIFACT_DIR}/preflight.json" || true)"
[[ "${preflight_code}" == "200" ]] || { echo "normal API unavailable before GDN gate: ${preflight_code}" >&2; exit 1; }
"${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh" >"${ARTIFACT_DIR}/normal-stop.txt" 2>&1
mkdir -p "${BASE_CACHE}" "${CANDIDATE_CACHE}"

# Create the qualified reference before compiling the isolated candidate cache.
PYTHONPATH="${SOURCE_DIR}/python" TORCH_EXTENSIONS_DIR="${BASE_CACHE}" PYTORCH_ROCM_ARCH=gfx1151 \
FREETOKEN_GDN_NUM_WARPS=1 FREETOKEN_GDN_NUM_STAGES=3 "${ROOT_DIR}/.venv/bin/python" \
    "${SOURCE_DIR}/benchmarks/gmk_evo_x2/bench_qwen_gdn_decode_stage.py" --model "${MODEL_PATH}" \
    --warmup 30 --repetitions 300 --json "${ARTIFACT_DIR}/baseline.json" \
    --save-output "${ARTIFACT_DIR}/baseline-output.pt" >"${ARTIFACT_DIR}/baseline.log" 2>&1

# Compile and measure one candidate only after the source-matched baseline exists.
PYTHONPATH="${SOURCE_DIR}/python" TORCH_EXTENSIONS_DIR="${CANDIDATE_CACHE}" PYTORCH_ROCM_ARCH=gfx1151 \
FREETOKEN_GDN_NUM_WARPS=1 FREETOKEN_GDN_NUM_STAGES="${CANDIDATE_STAGE}" "${ROOT_DIR}/.venv/bin/python" \
    "${SOURCE_DIR}/benchmarks/gmk_evo_x2/bench_qwen_gdn_decode_stage.py" --model "${MODEL_PATH}" \
    --warmup 30 --repetitions 300 --json "${ARTIFACT_DIR}/candidate.json" \
    --reference-output "${ARTIFACT_DIR}/baseline-output.pt" >"${ARTIFACT_DIR}/candidate.log" 2>&1
printf 'gdn_stage_component_parity_and_timing=passed candidate_stage=%s\n' "${CANDIDATE_STAGE}" >"${ARTIFACT_DIR}/result.txt"
