#!/usr/bin/env bash
# Run the isolated real-weight dense-Q8 kernel screen and restore Qwen afterward.
#
# This controller is deliberately suitable for `nohup` execution.  Its cleanup
# trap belongs to the detached controller rather than the SSH connection that
# starts it, so a caller disconnect cannot strand the protected normal service.
# The controller never contacts llama-swap or any non-GMKtec EVO-X2 endpoint.

set -euo pipefail

# Require an empty artifact root so no failed or incomplete run can overwrite
# prior evidence.  All controller, kernel, and recovery files stay below it.
readonly ARTIFACT_DIR="${1:?usage: run_qwen_q8_dense_timeshare.sh ARTIFACT_DIR}"
readonly ROOT_DIR="/home/david/freetoken-amd"
# The recovery source must be an explicit exact checkout whose native cache has
# already been validated.  This prevents silently recovering with an arbitrary
# newer experiment source after the normal service has been stopped.
readonly RECOVERY_SOURCE_DIR="${FREETOKEN_RECOVERY_SOURCE_DIR:?set FREETOKEN_RECOVERY_SOURCE_DIR}"
readonly MODEL_PATH="${FREETOKEN_Q4_MODEL_PATH:-${ROOT_DIR}/models/controls/qwen36-35b-a3b-unsloth-a483e9e6/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf}"
readonly VENV_PYTHON="${ROOT_DIR}/.venv/bin/python"
readonly START_SCRIPT="${RECOVERY_SOURCE_DIR}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh"
readonly STOP_SCRIPT="${RECOVERY_SOURCE_DIR}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh"
readonly BENCHMARK="${RECOVERY_SOURCE_DIR}/benchmarks/gmk_evo_x2/bench_qwen_q8_dense_kernel.py"
readonly KERNEL_CACHE_DIR="${ROOT_DIR}/cache/kernel-cache-rocm-gfx1151-$(git -C "${RECOVERY_SOURCE_DIR}" rev-parse --short=12 HEAD)"
readonly CONTROLLER_LOG="${ARTIFACT_DIR}/controller.log"
readonly CLEANUP_LOG="${ARTIFACT_DIR}/cleanup.txt"
readonly RECOVERY_LOG="${ARTIFACT_DIR}/recovery-start.txt"

# A successful controller only marks the normal API ready after an actual model
# completion returns HTTP 200.  `/v1/models` is intentionally not sufficient
# because it can return success while expert loading is still in progress.
wait_for_normal_completion() {
    local attempt http
    for attempt in $(seq 1 600); do
        http="$(curl -s -o "${ARTIFACT_DIR}/recovery-probe.json" -w '%{http_code}' \
            -H 'Content-Type: application/json' \
            -d '{"model":"qwen3.6-35b-a3b-nvfp4-amd","messages":[{"role":"user","content":"Return exactly READY."}],"stream":false,"max_tokens":4,"temperature":0,"reasoning_effort":"none"}' \
            http://127.0.0.1:1919/v1/chat/completions || true)"
        if [[ "${http}" == "200" ]]; then
            printf 'normal_api_ready=1 attempts=%s\n' "${attempt}" >>"${CLEANUP_LOG}"
            return 0
        fi
        sleep 1
    done
    printf 'normal_api_ready=0 attempts=600\n' >>"${CLEANUP_LOG}"
    return 1
}

# Always attempt normal-service recovery after its dedicated process group has
# been stopped.  The original kernel-screen status is retained unless recovery
# itself fails, because an unverified recovery is the higher-severity failure.
recover_normal_service() {
    local original_status="$1"
    if [[ ! -f "${ARTIFACT_DIR}/normal-stopped.txt" ]]; then
        printf 'normal_service_was_not_stopped=1 exit_status=%s\n' "${original_status}" >"${CLEANUP_LOG}"
        return "${original_status}"
    fi
    if ! bash "${START_SCRIPT}" >"${RECOVERY_LOG}" 2>&1; then
        printf 'normal_recovery_launch=failed original_status=%s\n' "${original_status}" >"${CLEANUP_LOG}"
        return 70
    fi
    if ! wait_for_normal_completion; then
        printf 'normal_recovery_completion=failed original_status=%s\n' "${original_status}" >>"${CLEANUP_LOG}"
        return 71
    fi
    printf 'normal_recovery_completion=passed original_status=%s\n' "${original_status}" >>"${CLEANUP_LOG}"
    return "${original_status}"
}

# The trap runs in the detached controller process, not in its interactive SSH
# parent.  It therefore remains responsible for recovery after disconnects.
cleanup() {
    local status="$?"
    recover_normal_service "${status}"
    exit "$?"
}
trap cleanup EXIT INT TERM

# Refuse malformed deployment inputs before stopping the normal service.
test ! -e "${ARTIFACT_DIR}"
test -d "${RECOVERY_SOURCE_DIR}"
test -d "${KERNEL_CACHE_DIR}"
test -f "${MODEL_PATH}"
test -x "${VENV_PYTHON}"
test -f "${START_SCRIPT}"
test -f "${STOP_SCRIPT}"
test -f "${BENCHMARK}"
mkdir -p "${ARTIFACT_DIR}"

# Record immutable source and cache provenance before allocating or releasing
# the GPU.  These fields make a later result traceable to one exact native ABI.
{
    printf 'recovery_source=%s\n' "${RECOVERY_SOURCE_DIR}"
    printf 'recovery_revision=%s\n' "$(git -C "${RECOVERY_SOURCE_DIR}" rev-parse --short=12 HEAD)"
    printf 'kernel_cache=%s\n' "${KERNEL_CACHE_DIR}"
    printf 'model=%s\n' "${MODEL_PATH}"
} >"${ARTIFACT_DIR}/manifest.txt"

# Confirm a genuine model completion before releasing the dedicated normal
# service group.  This prevents a controller from masking an existing outage.
initial_http="$(curl -s -o "${ARTIFACT_DIR}/preflight.json" -w '%{http_code}' \
    -H 'Content-Type: application/json' \
    -d '{"model":"qwen3.6-35b-a3b-nvfp4-amd","messages":[{"role":"user","content":"Return exactly READY."}],"stream":false,"max_tokens":4,"temperature":0,"reasoning_effort":"none"}' \
    http://127.0.0.1:1919/v1/chat/completions)"
[[ "${initial_http}" == "200" ]]

# Stop only the verified normal service.  The helper checks both model identity
# and dedicated process group before it sends a signal.
bash "${STOP_SCRIPT}"
touch "${ARTIFACT_DIR}/normal-stopped.txt"

# Reuse the known native cache and forbid JIT.  A missing specialization is a
# test failure, not authorization to compile an untracked binary during timing.
export PYTHONPATH="${RECOVERY_SOURCE_DIR}/python"
export TORCH_EXTENSIONS_DIR="${ROOT_DIR}/cache/torch_extensions"
export FREETOKEN_KERNEL_CACHE_DIR="${KERNEL_CACHE_DIR}"
export FREETOKEN_DISABLE_JIT=1
export ROCM_PATH="/opt/rocm-10.0"
export HIP_PATH="/opt/rocm-10.0"
export ROCM_HOME="/opt/rocm-10.0"

# Two real dense Q8_0 shapes cover the 2,048-to-8,192 attention projection and
# the 4,096-to-2,048 state-space output projection observed in the Qwen GGUF.
"${VENV_PYTHON}" "${BENCHMARK}" \
    --model "${MODEL_PATH}" \
    --tensor "blk.0.attn_qkv.weight" \
    --json "${ARTIFACT_DIR}/attn_qkv.json" \
    >"${ARTIFACT_DIR}/attn_qkv.log" 2>&1
"${VENV_PYTHON}" "${BENCHMARK}" \
    --model "${MODEL_PATH}" \
    --tensor "blk.0.ssm_out.weight" \
    --json "${ARTIFACT_DIR}/ssm_out.json" \
    >"${ARTIFACT_DIR}/ssm_out.log" 2>&1

printf 'kernel_screen=passed\n' >"${ARTIFACT_DIR}/result.txt"
