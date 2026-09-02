#!/usr/bin/env bash
# Screen a dense Q6_K two-wave candidate on a GMKtec EVO-X2 real GGUF tensor.
#
# The controller never makes an API performance claim.  It stops the protected
# normal service only after a real preflight completion, measures one-wave and
# two-wave production kernels on the original packed Q6_K output tensor, gates
# the candidate on numerical output parity, and restores the normal service in
# every exit path.

set -euo pipefail

# Require a caller-owned immutable artifact directory for all baseline,
# candidate, compiler, parity, and recovery evidence.
readonly ARTIFACT_DIR="${1:?usage: run_qwen_q6_component_gate.sh ARTIFACT_DIR}"
# Require the isolated source rather than permitting an accidental normal-source
# candidate build.
readonly SOURCE_DIR="${FREETOKEN_Q6_SOURCE_DIR:?set FREETOKEN_Q6_SOURCE_DIR}"
# Keep durable model assets and the virtual environment outside the source tree.
readonly ROOT_DIR="/home/david/freetoken-amd"
# Restore only from the known protected-service recovery checkout.
readonly RECOVERY_SOURCE="${ROOT_DIR}/source-qwen-recovery-d6ee8cef479c"
# Use the exact Q4_K_M GGUF that contains the real Q6_K output projection.
readonly MODEL_PATH="${ROOT_DIR}/models/controls/qwen36-35b-a3b-unsloth-a483e9e6/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
# Keep the component screen tied to the one Q6_K tensor found in that model.
readonly TENSOR_NAME="output.weight"
# Keep all native compilation caches revision-specific and separate from normal
# service extension artifacts.
readonly BASE_CACHE="${ROOT_DIR}/cache/torch_extensions-q6-one-f1baf13"
readonly CANDIDATE_CACHE="${ROOT_DIR}/cache/torch_extensions-q6-two-f1baf13"
# Use the same actual normal completion request for preflight and recovery.
readonly NORMAL_REQUEST='{"model":"qwen3.6-35b-a3b-nvfp4-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":4,"temperature":0,"stream":false}'

# Submit a real normal-service completion, retain its body, and print only its
# HTTP status so the caller can safely make an unambiguous lifecycle decision.
normal_status() {
    local output="$1"
    curl -sS -m 45 -o "${output}" -w '%{http_code}' \
        -H 'Content-Type: application/json' -d "${NORMAL_REQUEST}" \
        http://127.0.0.1:1919/v1/chat/completions
}

# Restore the normal service and require a real completion before controller
# exit, including failure or interrupt during HIP compilation or parity checks.
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

# Fail closed before normal service disruption when a source, model, helper, or
# benchmark prerequisite is missing.
for required in "${MODEL_PATH}" \
    "${SOURCE_DIR}/benchmarks/gmk_evo_x2/bench_qwen_q6_dense_kernel.py" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh"; do
    [[ -f "${required}" ]] || { echo "missing required file: ${required}" >&2; exit 2; }
done

# The recovery trap takes ownership only after static validation succeeds.
trap recover_normal_service EXIT

# Refuse to disrupt an already-unavailable normal service.
preflight_code="$(normal_status "${ARTIFACT_DIR}/preflight.json" || true)"
[[ "${preflight_code}" == "200" ]] || { echo "normal API unavailable before Q6 gate: ${preflight_code}" >&2; exit 1; }

# Release GPU memory after the preflight proves the service was functioning.
"${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh" \
    >"${ARTIFACT_DIR}/normal-stop.txt" 2>&1
mkdir -p "${BASE_CACHE}" "${CANDIDATE_CACHE}"

# Record an accepted one-wave output and device-time baseline before changing
# any launch geometry.
PYTHONPATH="${SOURCE_DIR}/python" TORCH_EXTENSIONS_DIR="${BASE_CACHE}" \
PYTORCH_ROCM_ARCH=gfx1151 FREETOKEN_GGUF_Q6_MMV_WARPS=1 \
"${ROOT_DIR}/.venv/bin/python" \
    "${SOURCE_DIR}/benchmarks/gmk_evo_x2/bench_qwen_q6_dense_kernel.py" \
    --model "${MODEL_PATH}" --tensor "${TENSOR_NAME}" --warmup 30 --repetitions 300 \
    --json "${ARTIFACT_DIR}/baseline.json" --save-output "${ARTIFACT_DIR}/baseline-output.pt" \
    >"${ARTIFACT_DIR}/baseline.log" 2>&1

# Time the two-wave candidate only after rebuilding it in its own cache and
# require numerical parity with the saved one-wave real-tensor output.
PYTHONPATH="${SOURCE_DIR}/python" TORCH_EXTENSIONS_DIR="${CANDIDATE_CACHE}" \
PYTORCH_ROCM_ARCH=gfx1151 FREETOKEN_GGUF_Q6_MMV_WARPS=2 \
"${ROOT_DIR}/.venv/bin/python" \
    "${SOURCE_DIR}/benchmarks/gmk_evo_x2/bench_qwen_q6_dense_kernel.py" \
    --model "${MODEL_PATH}" --tensor "${TENSOR_NAME}" --warmup 30 --repetitions 300 \
    --json "${ARTIFACT_DIR}/candidate.json" --reference-output "${ARTIFACT_DIR}/baseline-output.pt" \
    >"${ARTIFACT_DIR}/candidate.log" 2>&1

# Mark only a fully timed and parity-checked component screen as complete.
printf 'q6_component_parity_and_timing=passed\n' >"${ARTIFACT_DIR}/result.txt"
