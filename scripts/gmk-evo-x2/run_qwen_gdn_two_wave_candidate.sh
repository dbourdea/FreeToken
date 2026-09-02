#!/usr/bin/env bash
# Run one isolated two-wave gated-delta-rule Qwen Q4 candidate on a GMKtec EVO-X2.
#
# The controller deliberately runs only after a live normal-service completion
# succeeds.  It then stops that protected service, starts a loopback-only Q4
# candidate, requires a real candidate completion before scoring, collects the
# deterministic AIME quality gate and client-visible prefill/decode TPS, and
# finally restores the normal service through its EXIT trap on every outcome.

set -euo pipefail

# Require an immutable artifact directory so raw logs and JSON cannot overwrite
# a previous candidate run.
readonly ARTIFACT_DIR="${1:?usage: run_qwen_gdn_two_wave_candidate.sh ARTIFACT_DIR}"
# Accept only the two experimentally supported GDN launch shapes.  Defaulting
# to two waves preserves this script's optimization-focused behavior while a
# one-wave run provides a same-source control when explicitly requested.
readonly GDN_NUM_WARPS="${FREETOKEN_GDN_CANDIDATE_WARPS:-2}"
# Keep graph capture opt-in and bounded to the single-stream decode shape used
# by this benchmark.  Zero preserves eager execution and one captures only the
# fixed batch-one path, avoiding an unreviewed batch-shape expansion.
readonly CUDA_GRAPH_MAX_BS="${FREETOKEN_Q4_CUDA_GRAPH_MAX_BS:-0}"
# Keep all inputs below the host-owned FreeToken root rather than relying on the
# caller's working directory.
readonly ROOT_DIR="/home/david/freetoken-amd"
# Use a Qwen-capable benchmark revision with only the GDN launch change applied.
readonly SOURCE_DIR="${FREETOKEN_Q4_SOURCE_DIR:?set FREETOKEN_Q4_SOURCE_DIR}"
# Restore the separate, protected NVFP4 service from its known recovery source.
readonly RECOVERY_SOURCE="${ROOT_DIR}/source-qwen-recovery-d6ee8cef479c"
# Use the reviewed loopback lifecycle helper shipped with the candidate source.
readonly LAUNCHER="${SOURCE_DIR}/scripts/gmk-evo-x2/launch_qwen_gguf_qualified.sh"
# Keep normal-service lifecycle separate from candidate lifecycle.
readonly NORMAL_STOP="${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh"
readonly NORMAL_START="${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh"
# Name the Q4 candidate exactly as the isolated launcher advertises it.
readonly CANDIDATE_MODEL="qwen36-35b-a3b-q4km-gguf-amd"
# Permit a same-source control hash to replace an older incompatible absolute
# reference.  The override is evidence-based: it must be supplied explicitly
# from a preceding one-wave control artifact, never silently inferred.
readonly QUALITY_REFERENCE_SHA1="${FREETOKEN_GDN_REFERENCE_SHA1:-}"
# Use a real low-cost completion, not /v1/models, as readiness proof.
readonly NORMAL_REQUEST='{"model":"qwen3.6-35b-a3b-nvfp4-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":4,"temperature":0,"stream":false}'
readonly CANDIDATE_REQUEST='{"model":"qwen36-35b-a3b-q4km-gguf-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":4,"temperature":0,"stream":false}'

# Reject misspelled or unsupported launch choices before the protected service
# is stopped, preventing an accidental unreviewed Triton configuration.
[[ "${GDN_NUM_WARPS}" == "1" || "${GDN_NUM_WARPS}" == "2" ]] || {
    echo "FREETOKEN_GDN_CANDIDATE_WARPS must be 1 or 2" >&2
    exit 2
}
[[ "${CUDA_GRAPH_MAX_BS}" == "0" || "${CUDA_GRAPH_MAX_BS}" == "1" ]] || {
    echo "FREETOKEN_Q4_CUDA_GRAPH_MAX_BS must be 0 or 1" >&2
    exit 2
}

# Save a POST response and print only its status code, allowing callers to use
# the code as an unambiguous readiness gate while retaining the response body.
completion_status() {
    local url="$1"
    local request="$2"
    local output="$3"
    curl -sS -m 45 -o "${output}" -w '%{http_code}' \
        -H 'Content-Type: application/json' -d "${request}" "${url}"
}

# Rebuild the protected service and verify a genuine completion before exiting.
# This must be idempotent because it is invoked by the EXIT trap after success,
# failure, interrupt, or a failed candidate startup.
recover_normal_service() {
    FREETOKEN_GDN_NUM_WARPS=1 "${LAUNCHER}" stop "${ARTIFACT_DIR}/candidate" 2>/dev/null || true
    "${NORMAL_START}" >"${ARTIFACT_DIR}/recovery-start.txt" 2>&1 || true
    for attempt in $(seq 1 600); do
        code="$(completion_status http://127.0.0.1:1919/v1/chat/completions "${NORMAL_REQUEST}" "${ARTIFACT_DIR}/recovery-probe.json" || true)"
        if [[ "${code}" == "200" ]]; then
            printf 'normal_api_ready=1 attempts=%s\n' "${attempt}" >"${ARTIFACT_DIR}/cleanup.txt"
            return 0
        fi
        sleep 1
    done
    printf 'normal_api_ready=0 attempts=600\n' >"${ARTIFACT_DIR}/cleanup.txt"
    return 1
}

# Fail closed before the normal service is touched if any expected immutable
# source or safety helper is absent.
for required in "${LAUNCHER}" "${NORMAL_STOP}" "${NORMAL_START}" \
    "${SOURCE_DIR}/scripts/gmk-evo-x2/verify_qwen_aime_quality.py" \
    "${SOURCE_DIR}/scripts/gmk-evo-x2/run_qwen_scheduler_baseline.sh"; do
    [[ -f "${required}" ]] || { echo "missing required file: ${required}" >&2; exit 2; }
done

# Restore normal service even if any candidate quality, measurement, or startup
# gate fails after the protected service has been stopped.
trap recover_normal_service EXIT

# Refuse to interrupt an unavailable normal service since recovery would not
# prove that the candidate controller preserved its prior working state.
preflight_code="$(completion_status http://127.0.0.1:1919/v1/chat/completions "${NORMAL_REQUEST}" "${ARTIFACT_DIR}/preflight.json" || true)"
[[ "${preflight_code}" == "200" ]] || { echo "normal API unavailable before candidate: ${preflight_code}" >&2; exit 1; }

# Release the GPU only after all static guards and the normal preflight pass.
"${NORMAL_STOP}" >"${ARTIFACT_DIR}/normal-stop.txt" 2>&1

# Start the candidate with the experimental two-wave GDN launch setting and a
# candidate-specific extension cache, leaving the default launch configuration
# and the normal service cache untouched.
FREETOKEN_Q4_EXTENSION_CACHE_DIR="${ROOT_DIR}/cache/torch_extensions-gdn-${GDN_NUM_WARPS}-f1baf13" \
FREETOKEN_GDN_NUM_WARPS="${GDN_NUM_WARPS}" \
bash "${LAUNCHER}" start "${ARTIFACT_DIR}/candidate" 0.25 "${CUDA_GRAPH_MAX_BS}"

# Wait for an actual candidate completion.  A model-list response is explicitly
# insufficient because it can succeed before the model worker finishes loading.
for attempt in $(seq 1 600); do
    code="$(completion_status http://127.0.0.1:1922/v1/chat/completions "${CANDIDATE_REQUEST}" "${ARTIFACT_DIR}/candidate/ready.json" || true)"
    if [[ "${code}" == "200" ]]; then
        printf 'candidate_api_ready=1 attempts=%s\n' "${attempt}" >"${ARTIFACT_DIR}/candidate/ready.txt"
        break
    fi
    sleep 1
done
[[ -f "${ARTIFACT_DIR}/candidate/ready.txt" ]] || { echo 'candidate API never became ready' >&2; exit 1; }

# Require deterministic quality before accepting any throughput increase.
set +e
PYTHONPATH="${SOURCE_DIR}/python" "${ROOT_DIR}/.venv/bin/python" \
    "${SOURCE_DIR}/scripts/gmk-evo-x2/verify_qwen_aime_quality.py" \
    --base-url http://127.0.0.1:1922 --model "${CANDIDATE_MODEL}" \
    --artifact "${ARTIFACT_DIR}/quality-aime.json" >"${ARTIFACT_DIR}/quality-aime.log" 2>&1
quality_exit="$?"
set -e

# Prefer the original absolute-quality gate when no same-source control hash
# was provided.  When a reference is supplied, require the candidate's entire
# captured output hash to match that control exactly, then persist both values
# for an auditable quality-parity decision.
if [[ -z "${QUALITY_REFERENCE_SHA1}" ]]; then
    [[ "${quality_exit}" == "0" ]] || { echo 'absolute quality gate failed' >&2; exit 1; }
else
    observed_sha1="$("${ROOT_DIR}/.venv/bin/python" -c 'import json,sys; print(json.load(open(sys.argv[1]))["output_sha1"])' "${ARTIFACT_DIR}/quality-aime.json")"
    printf 'quality_reference_sha1=%s\nquality_observed_sha1=%s\n' \
        "${QUALITY_REFERENCE_SHA1}" "${observed_sha1}" >"${ARTIFACT_DIR}/quality-parity.txt"
    [[ "${observed_sha1}" == "${QUALITY_REFERENCE_SHA1}" ]] || {
        echo 'same-source quality parity gate failed' >&2
        exit 1
    }
fi

# Measure warm client-visible prefill and decode TPS using three scored samples
# and the same fixed scheduler workload as the qualified Q4 baseline.
GMK_EVO_X2_QWEN_BENCHMARK_SOURCE_DIR="${SOURCE_DIR}" \
GMK_EVO_X2_QWEN_TOKENIZER_DIR="${ROOT_DIR}/models/Qwen3.6-35B-A3B-NVFP4" \
GMK_EVO_X2_QWEN_MODEL_NAME="${CANDIDATE_MODEL}" \
GMK_EVO_X2_QWEN_BASE_URL=http://127.0.0.1:1922/v1 \
bash "${SOURCE_DIR}/scripts/gmk-evo-x2/run_qwen_scheduler_baseline.sh" \
    "${ARTIFACT_DIR}/scheduler-tps" >"${ARTIFACT_DIR}/scheduler.log" 2>&1

# Mark success only after readiness, quality, and both TPS paths complete.
printf 'candidate_quality_and_scheduler=passed\n' >"${ARTIFACT_DIR}/result.txt"
