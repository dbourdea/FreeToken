#!/usr/bin/env bash
# Run the real-weight grouped-versus-vector Q4 numerical differential safely.
#
# This controller owns only the isolated diagnostic window. It proves the
# protected normal OpenAI-compatible Qwen service can return a real completion,
# stops that service after the proof, runs one immutable component artifact,
# and restores a completion-capable normal service through every exit path.
# The Python diagnostic records numerical differences only. It makes no API TPS
# claim and cannot change the normal service configuration.

set -euo pipefail

# Require a caller-chosen, previously nonexistent evidence directory. The
# controller creates it before service ownership so each invocation remains
# independently auditable and never overwrites a prior result.
readonly ARTIFACT_DIR="${1:?usage: run_qwen_q4_grouped_differential_gate.sh ARTIFACT_DIR [differential arguments...]}"
shift
# Keep optional Python-harness parameters explicit and positional. This permits
# targeted numerical diagnoses, such as one repeated expert, without changing
# the guarded service ownership or artifact lifecycle in this controller.
readonly -a DIFFERENTIAL_ARGS=("$@")
# SOURCE_DIR is deliberately supplied by the caller, allowing the test to use
# a detached candidate checkout without editing the protected recovery source.
readonly SOURCE_DIR="${FREETOKEN_Q4_SOURCE_DIR:?set FREETOKEN_Q4_SOURCE_DIR}"
readonly ROOT_DIR="/home/david/freetoken-amd"
readonly RECOVERY_SOURCE="${ROOT_DIR}/source-qwen-recovery-d6ee8cef479c"
readonly MODEL_PATH="${ROOT_DIR}/models/controls/qwen36-35b-a3b-unsloth-a483e9e6/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
readonly BENCHMARK="${SOURCE_DIR}/benchmarks/gmk_evo_x2/bench_qwen_q4_grouped_differential.py"
# A commit-qualified cache prevents a header-level arithmetic candidate from
# reusing a previously compiled HIP module. It also keeps all test products
# separate from the protected normal-service cache.
readonly CANDIDATE_REVISION="$(git -C "${SOURCE_DIR}" rev-parse --short HEAD)"
readonly EXTENSION_CACHE="${ROOT_DIR}/cache/torch_extensions-q4-grouped-differential-${CANDIDATE_REVISION}"
readonly TRITON_CACHE="${ROOT_DIR}/cache/triton-q4-grouped-differential-${CANDIDATE_REVISION}"
readonly NATIVE_BUILD_LOG="${ARTIFACT_DIR}/native-extension-build.log"
readonly NATIVE_IMPORT_LOG="${ARTIFACT_DIR}/native-extension-import.txt"
readonly NORMAL_REQUEST='{"model":"qwen3.6-35b-a3b-nvfp4-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":512,"temperature":0,"stream":false}'

[[ ! -e "${ARTIFACT_DIR}" ]] || { echo "artifact directory already exists: ${ARTIFACT_DIR}" >&2; exit 2; }
mkdir -p "${ARTIFACT_DIR}"

# Save the complete response body while returning only HTTP status to the
# caller. A health or models-list probe is insufficient proof of recovery.
normal_status() {
    local output="$1"
    curl -sS -m 45 -o "${output}" -w '%{http_code}' \
        -H 'Content-Type: application/json' -d "${NORMAL_REQUEST}" \
        http://127.0.0.1:1919/v1/chat/completions
}

# Require a completed model response, rather than treating a listening socket,
# HTTP 200, or a reasoning-token length cutoff as proof that the protected
# service is ready for the next owner. The response body remains in the named
# artifact for later inspection when this check fails.
normal_completion() {
    local output="$1" code
    code="$(normal_status "${output}" || true)"
    [[ "${code}" == "200" ]] || return 1
    python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["choices"][0]["finish_reason"])' "${output}" \
        | grep -qx 'stop'
}

# Start the maintained recovery service and require one actual completion. The
# loop is bounded, records every failed readiness probe, and executes from the
# EXIT trap even when the diagnostic or HIP extension build fails.
recover_normal_service() {
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh" \
        >"${ARTIFACT_DIR}/recovery-start.txt" 2>&1 || true
    for attempt in $(seq 1 600); do
        if normal_completion "${ARTIFACT_DIR}/recovery-probe.json"; then
            printf 'normal_api_ready=1 attempts=%s\n' "${attempt}" >"${ARTIFACT_DIR}/cleanup.txt"
            return 0
        fi
        printf 'attempt=%s completion=not-ready\n' "${attempt}" >>"${ARTIFACT_DIR}/recovery-progress.txt"
        sleep 1
    done
    printf 'normal_api_ready=0 attempts=600\n' >"${ARTIFACT_DIR}/cleanup.txt"
    return 1
}

# Refuse to stop the normal service unless all static prerequisites are present.
for required in "${MODEL_PATH}" "${BENCHMARK}" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh"; do
    [[ -f "${required}" ]] || { echo "missing required file: ${required}" >&2; exit 2; }
done

# Once this trap is armed, controller termination must attempt recovery before
# it returns control to the caller.
trap recover_normal_service EXIT

# Do not take GPU ownership from an unhealthy protected service.
normal_completion "${ARTIFACT_DIR}/preflight.json" \
    || { echo "normal API did not complete before differential gate" >&2; exit 1; }
mkdir -p "${EXTENSION_CACHE}" "${TRITON_CACHE}"

# A clean candidate checkout has no generated HIP extension. Build it in that
# checkout, with the candidate's Python package first on the import path, and
# preserve both build and import evidence before taking GPU ownership away
# from the protected service. A compiler or source-layout failure is therefore
# contained to the candidate and cannot trigger an unnecessary model reload.
if ! PYTHONPATH="${SOURCE_DIR}/python" "${ROOT_DIR}/.venv/bin/python" -c \
    'import freetoken.kernel._pinned_tensor' >/dev/null 2>&1; then
    (
        # setup.py declares its native source paths relative to its checkout.
        # Building from SOURCE_DIR keeps a fresh candidate self-contained and
        # avoids accidentally resolving paths beneath the SSH login directory.
        cd "${SOURCE_DIR}"
        ROCM_HOME=/opt/rocm-10.0 ROCM_PATH=/opt/rocm-10.0 HIP_PATH=/opt/rocm-10.0 \
        PYTHONPATH="${SOURCE_DIR}/python" "${ROOT_DIR}/.venv/bin/python" \
            setup.py build_ext --inplace
    ) >"${NATIVE_BUILD_LOG}" 2>&1
fi
PYTHONPATH="${SOURCE_DIR}/python" "${ROOT_DIR}/.venv/bin/python" -c \
    'import freetoken.kernel._pinned_tensor as pinned; print(pinned.__file__)' \
    >"${NATIVE_IMPORT_LOG}"

# The candidate can now import every required native module, so it is safe to
# hand GPU ownership over for the direct numerical computation.
"${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh" \
    >"${ARTIFACT_DIR}/normal-stop.txt" 2>&1

# The direct process sees only its own source checkout and caches. Its output
# JSON is the sole numerical evidence emitted by this controller.
PYTHONPATH="${SOURCE_DIR}/python" TORCH_EXTENSIONS_DIR="${EXTENSION_CACHE}" \
TRITON_CACHE_DIR="${TRITON_CACHE}" PYTORCH_ROCM_ARCH=gfx1151 \
"${ROOT_DIR}/.venv/bin/python" "${BENCHMARK}" \
    --model "${MODEL_PATH}" --json "${ARTIFACT_DIR}/differential.json" \
    "${DIFFERENTIAL_ARGS[@]}" \
    >"${ARTIFACT_DIR}/differential.log" 2>&1

printf 'grouped_q4_numerical_differential=completed\n' >"${ARTIFACT_DIR}/result.txt"
