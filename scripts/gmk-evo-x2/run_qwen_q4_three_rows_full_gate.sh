#!/usr/bin/env bash
# Qualify an opt-in Q4_K/Q5_K HIP candidate through complete API gates.
#
# This controller time-shares the GPU only after a real protected-service
# completion. It runs the canonical deterministic fingerprint, three warm
# scheduler samples, and three synchronized four-client rounds against a
# loopback-only candidate. The EXIT trap always restores and proves the normal
# OpenAI-compatible Qwen service before the controller exits.

set -euo pipefail

# Require a fresh immutable evidence directory from the caller.
readonly ARTIFACT_DIR="${1:?usage: run_qwen_q4_three_rows_full_gate.sh ARTIFACT_DIR}"
# Keep the candidate source explicit, so benchmark code and loaded extension are auditable.
readonly SOURCE_DIR="${FREETOKEN_Q4_SOURCE_DIR:-/home/david/freetoken-amd/source-qwen-gdn-isolated-f1}"
# Keep all host-owned paths adjacent to make service scope reviewable.
readonly ROOT_DIR="/home/david/freetoken-amd"
readonly RECOVERY_SOURCE="${ROOT_DIR}/source-qwen-recovery-d6ee8cef479c"
readonly LAUNCHER="${SOURCE_DIR}/scripts/gmk-evo-x2/launch_qwen_gguf_qualified.sh"
readonly QUALITY="${SOURCE_DIR}/scripts/gmk-evo-x2/verify_qwen_aime_quality.py"
readonly SCHEDULER="${SOURCE_DIR}/scripts/gmk-evo-x2/run_qwen_scheduler_baseline.sh"
readonly CONCURRENT="${SOURCE_DIR}/benchmarks/gmk_evo_x2/run_concurrent_api_control.py"
readonly VENV_PYTHON="${ROOT_DIR}/.venv/bin/python"
readonly TOKENIZER="${ROOT_DIR}/models/Qwen3.6-35B-A3B-NVFP4"
readonly CANDIDATE_MODEL="qwen36-35b-a3b-q4km-gguf-amd"
# The AIME helper appends `/v1` itself, while scheduler and concurrency helpers
# accept an OpenAI API base that already ends in `/v1`. Keep both boundaries
# explicit so a controller cannot accidentally request `/v1/v1/models`.
readonly CANDIDATE_ROOT="http://127.0.0.1:1922"
readonly CANDIDATE_URL="http://127.0.0.1:1922/v1"
# Each candidate selector is explicit and recorded below.  The values are passed
# only to the isolated launcher, never to the protected recovery service.
readonly MOE_K_TWO_ROWS="${FREETOKEN_Q4_MOE_K_TWO_ROWS:-0}"
readonly MOE_K_THREE_ROWS="${FREETOKEN_Q4_MOE_K_THREE_ROWS:-0}"
readonly GROUPED_PREFILL_MIN_TOKENS="${FREETOKEN_Q4_GROUPED_PREFILL_MIN_TOKENS:-0}"
readonly GROUPED_PREFILL_MODE="${FREETOKEN_Q4_GROUPED_PREFILL_MODE:-both}"
readonly NORMAL_REQUEST='{"model":"qwen3.6-35b-a3b-nvfp4-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":4,"temperature":0,"stream":false}'

[[ ! -e "${ARTIFACT_DIR}" ]] || { echo "artifact directory already exists: ${ARTIFACT_DIR}" >&2; exit 2; }
[[ "${MOE_K_TWO_ROWS}" == "0" || "${MOE_K_TWO_ROWS}" == "1" ]] || { echo "FREETOKEN_Q4_MOE_K_TWO_ROWS must be 0 or 1" >&2; exit 2; }
[[ "${MOE_K_THREE_ROWS}" == "0" || "${MOE_K_THREE_ROWS}" == "1" ]] || { echo "FREETOKEN_Q4_MOE_K_THREE_ROWS must be 0 or 1" >&2; exit 2; }
[[ ! ( "${MOE_K_TWO_ROWS}" == "1" && "${MOE_K_THREE_ROWS}" == "1" ) ]] || { echo "select at most one Q4 row-sharing candidate" >&2; exit 2; }
[[ "${GROUPED_PREFILL_MIN_TOKENS}" =~ ^[0-9]+$ ]] || { echo "FREETOKEN_Q4_GROUPED_PREFILL_MIN_TOKENS must be a non-negative integer" >&2; exit 2; }
[[ "${GROUPED_PREFILL_MODE}" == "both" || "${GROUPED_PREFILL_MODE}" == "gate_up" || "${GROUPED_PREFILL_MODE}" == "down" ]] || { echo "FREETOKEN_Q4_GROUPED_PREFILL_MODE must be both, gate_up, or down" >&2; exit 2; }
for required in "${LAUNCHER}" "${QUALITY}" "${SCHEDULER}" "${CONCURRENT}" "${TOKENIZER}" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh"; do
    [[ -e "${required}" ]] || { echo "missing prerequisite: ${required}" >&2; exit 2; }
done
mkdir -p "${ARTIFACT_DIR}"

# Capture a real completion status and retain its response without trusting a models list.
normal_status() {
    curl -sS -m 45 -o "$1" -w '%{http_code}' -H 'Content-Type: application/json' \
        -d "${NORMAL_REQUEST}" http://127.0.0.1:1919/v1/chat/completions
}

# Candidate readiness uses a real short completion because the frontend becomes
# reachable before the asynchronous model worker is ready.
candidate_status() {
    curl -sS -m 45 -o "$1" -w '%{http_code}' -H 'Content-Type: application/json' \
        -d '{"model":"qwen36-35b-a3b-q4km-gguf-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":4,"temperature":0,"stream":false}' \
        http://127.0.0.1:1922/v1/chat/completions
}

# Return the protected API only after the candidate is gone, keeping recovery
# separate from every test result and preserving a count of actual completions.
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

# Stop only the launcher-associated candidate before invoking the protected recovery source.
stop_candidate() {
    "${LAUNCHER}" stop "${ARTIFACT_DIR}/q4-server" >"${ARTIFACT_DIR}/q4-stop.txt" 2>&1 || true
}

trap 'stop_candidate; recover_normal_service' EXIT
preflight_code="$(normal_status "${ARTIFACT_DIR}/preflight.json" || true)"
[[ "${preflight_code}" == "200" ]] || { echo "normal API unavailable before Q4 full gate: ${preflight_code}" >&2; exit 1; }
"${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh" >"${ARTIFACT_DIR}/normal-stop.txt" 2>&1

# Only this child inherits experimental selectors. The established 30 percent,
# four-request, overlap-enabled Q4 profile is otherwise unchanged.
FREETOKEN_Q4_SOURCE_DIR="${SOURCE_DIR}" FREETOKEN_Q4_PREFILL_OVERLAP=1 \
FREETOKEN_GGUF_MOE_K_TWO_ROWS="${MOE_K_TWO_ROWS}" \
FREETOKEN_GGUF_MOE_K_THREE_ROWS="${MOE_K_THREE_ROWS}" \
FREETOKEN_Q4_GROUPED_PREFILL_MIN_TOKENS="${GROUPED_PREFILL_MIN_TOKENS}" \
FREETOKEN_Q4_GROUPED_PREFILL_MODE="${GROUPED_PREFILL_MODE}" \
    "${LAUNCHER}" start "${ARTIFACT_DIR}/q4-server" 0.30 0
candidate_ready=0
for _ in $(seq 1 480); do
    code="$(candidate_status "${ARTIFACT_DIR}/ready.json" || true)"
    if [[ "${code}" == "200" ]]; then
        candidate_ready=1
        break
    fi
    printf 'status=%s\n' "${code}" >>"${ARTIFACT_DIR}/ready-progress.txt"
    sleep 1
done
[[ "${candidate_ready}" == "1" ]] || { echo "Q4 candidate did not reach real completion readiness" >&2; exit 1; }

# The deterministic fingerprint is an admission gate, never a post-hoc report.
PYTHONPATH="${SOURCE_DIR}/python" "${VENV_PYTHON}" "${QUALITY}" \
    --base-url "${CANDIDATE_ROOT}" --model "${CANDIDATE_MODEL}" \
    --artifact "${ARTIFACT_DIR}/quality-aime.json" \
    --expected-output-sha1 3302eda43396 >"${ARTIFACT_DIR}/quality-aime.log" 2>&1

# Reuse the qualified scheduler workload with its fixed prompt, warmup, length,
# SSE timestamps, and three scored samples while targeting only the loopback candidate.
GMK_EVO_X2_QWEN_BENCHMARK_SOURCE_DIR="${SOURCE_DIR}" \
GMK_EVO_X2_QWEN_BASE_URL="${CANDIDATE_URL}" \
GMK_EVO_X2_QWEN_MODEL_NAME="${CANDIDATE_MODEL}" \
GMK_EVO_X2_QWEN_TOKENIZER_DIR="${TOKENIZER}" \
    bash "${SCHEDULER}" "${ARTIFACT_DIR}/scheduler" >"${ARTIFACT_DIR}/scheduler.log" 2>&1

# Release three four-client rounds simultaneously using the same tokenizer and
# fixed scheduler prompt. The raw event streams remain in the JSON artifact.
PYTHONPATH="${SOURCE_DIR}/python" "${VENV_PYTHON}" "${CONCURRENT}" \
    --base-url "${CANDIDATE_URL}" --model "${CANDIDATE_MODEL}" --tokenizer "${TOKENIZER}" \
    --expected-host david-Gmktec-x2-2 --concurrency 4 --rounds 3 --max-tokens 256 \
    --artifact "${ARTIFACT_DIR}/concurrent-c4.json" >"${ARTIFACT_DIR}/concurrent-c4.log" 2>&1

printf 'q4_candidate_quality_scheduler_and_c4=passed moe_k_two_rows=%s moe_k_three_rows=%s grouped_prefill_min_tokens=%s grouped_prefill_mode=%s\n' \
    "${MOE_K_TWO_ROWS}" "${MOE_K_THREE_ROWS}" "${GROUPED_PREFILL_MIN_TOKENS}" "${GROUPED_PREFILL_MODE}" >"${ARTIFACT_DIR}/result.txt"
