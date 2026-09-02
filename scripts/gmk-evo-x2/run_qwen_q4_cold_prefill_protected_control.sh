#!/usr/bin/env bash
# Measure cache-neutral Qwen Q4 prefill on an isolated FreeToken server safely.
#
# The corresponding ROCm llama.cpp control uses the same Q4_K_M GGUF, tokenizer,
# long-prompt generator, greedy decoding, and per-sample early nonce.  The nonce
# is before the expensive filler, so a prefix cache cannot turn later samples
# into cheap suffix-only extensions.  This controller owns the short GPU window
# and proves the normal OpenAI-compatible service can complete a real request
# after the isolated server has stopped.

set -euo pipefail

readonly ARTIFACT_DIR="${1:?usage: run_qwen_q4_cold_prefill_protected_control.sh ARTIFACT_DIR}"
readonly ROOT_DIR="/home/david/freetoken-amd"
readonly SOURCE_DIR="${FREETOKEN_Q4_SOURCE_DIR:-${ROOT_DIR}/source-qwen-gdn-isolated-f1}"
readonly RECOVERY_SOURCE="${ROOT_DIR}/source-qwen-recovery-d6ee8cef479c"
readonly LAUNCHER="${SOURCE_DIR}/scripts/gmk-evo-x2/launch_qwen_gguf_qualified.sh"
readonly HARNESS="${SOURCE_DIR}/benchmarks/gmk_evo_x2/run_long_context_control.py"
readonly QUALITY_SUITE="${SOURCE_DIR}/benchmarks/gmk_evo_x2/run_quality_suite.py"
readonly MODEL="qwen36-35b-a3b-q4km-gguf-amd"
# Row-sharing candidates are opt-in for the isolated process only. They never
# change the recovery server or the default Q4 launch profile.
readonly MOE_K_TWO_ROWS="${FREETOKEN_Q4_MOE_K_TWO_ROWS:-0}"
readonly MOE_K_THREE_ROWS="${FREETOKEN_Q4_MOE_K_THREE_ROWS:-0}"
# Grouped prefill is a separate, opt-in candidate.  Keep its threshold and
# scope explicit so an inherited shell setting cannot make an artifact
# ambiguous or affect the protected recovery launch.
readonly GROUPED_PREFILL_MIN_TOKENS="${FREETOKEN_Q4_GROUPED_PREFILL_MIN_TOKENS:-0}"
readonly GROUPED_PREFILL_MODE="${FREETOKEN_Q4_GROUPED_PREFILL_MODE:-both}"
readonly NORMAL_REQUEST='{"model":"qwen3.6-35b-a3b-nvfp4-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":4,"temperature":0,"stream":false}'

[[ ! -e "${ARTIFACT_DIR}" ]] || { echo "artifact directory already exists: ${ARTIFACT_DIR}" >&2; exit 2; }
[[ "${MOE_K_TWO_ROWS}" == "0" || "${MOE_K_TWO_ROWS}" == "1" ]] || {
    echo "FREETOKEN_Q4_MOE_K_TWO_ROWS must be 0 or 1" >&2
    exit 2
}
[[ "${MOE_K_THREE_ROWS}" == "0" || "${MOE_K_THREE_ROWS}" == "1" ]] || {
    echo "FREETOKEN_Q4_MOE_K_THREE_ROWS must be 0 or 1" >&2
    exit 2
}
[[ ! ( "${MOE_K_TWO_ROWS}" == "1" && "${MOE_K_THREE_ROWS}" == "1" ) ]] || {
    echo "select at most one Q4 row-sharing candidate" >&2
    exit 2
}
[[ "${GROUPED_PREFILL_MIN_TOKENS}" =~ ^[0-9]+$ ]] || {
    echo "FREETOKEN_Q4_GROUPED_PREFILL_MIN_TOKENS must be a non-negative integer" >&2
    exit 2
}
[[ "${GROUPED_PREFILL_MODE}" == "both" || "${GROUPED_PREFILL_MODE}" == "q4_gate_up" || "${GROUPED_PREFILL_MODE}" == "q5_down" ]] || {
    echo "FREETOKEN_Q4_GROUPED_PREFILL_MODE must be both, q4_gate_up, or q5_down" >&2
    exit 2
}
for required in "${LAUNCHER}" "${HARNESS}" "${QUALITY_SUITE}" "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh" "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh"; do
    [[ -f "${required}" ]] || { echo "missing required file: ${required}" >&2; exit 2; }
done
mkdir -p "${ARTIFACT_DIR}"

normal_status() {
    curl -sS -m 45 -o "$1" -w '%{http_code}' -H 'Content-Type: application/json' \
        -d "${NORMAL_REQUEST}" http://127.0.0.1:1919/v1/chat/completions
}

candidate_status() {
    # Uvicorn's health route becomes available before the Q4 model worker has
    # loaded its weights.  A real completion is the readiness condition, just
    # as it is for protected-service recovery, so the harness never records a
    # misleading HTTP-503 "benchmark" during asynchronous model startup.
    curl -sS -m 45 -o "$1" -w '%{http_code}' -H 'Content-Type: application/json' \
        -d '{"model":"qwen36-35b-a3b-q4km-gguf-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":4,"temperature":0,"stream":false}' \
        http://127.0.0.1:1922/v1/chat/completions
}

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

stop_candidate() {
    "${LAUNCHER}" stop "${ARTIFACT_DIR}/q4-server" >"${ARTIFACT_DIR}/q4-stop.txt" 2>&1 || true
}

trap 'stop_candidate; recover_normal_service' EXIT
preflight_code="$(normal_status "${ARTIFACT_DIR}/preflight.json" || true)"
[[ "${preflight_code}" == "200" ]] || { echo "normal API unavailable before Q4 cold-prefill control: ${preflight_code}" >&2; exit 1; }
"${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh" >"${ARTIFACT_DIR}/normal-stop.txt" 2>&1

# Preserve the accepted 30 percent Q4 profile: one GDN wave, Q4/Q6 overlap,
# and four request admission.  Only the client prompts change their prefixes.
FREETOKEN_Q4_SOURCE_DIR="${SOURCE_DIR}" FREETOKEN_Q4_PREFILL_OVERLAP=1 \
FREETOKEN_GGUF_MOE_K_TWO_ROWS="${MOE_K_TWO_ROWS}" \
FREETOKEN_GGUF_MOE_K_THREE_ROWS="${MOE_K_THREE_ROWS}" \
FREETOKEN_Q4_GROUPED_PREFILL_MIN_TOKENS="${GROUPED_PREFILL_MIN_TOKENS}" \
FREETOKEN_Q4_GROUPED_PREFILL_MODE="${GROUPED_PREFILL_MODE}" \
    "${LAUNCHER}" start "${ARTIFACT_DIR}/q4-server" 0.30 0
for _ in $(seq 1 480); do
    code="$(candidate_status "${ARTIFACT_DIR}/q4-ready-probe.json" || true)"
    if [[ "${code}" == "200" ]]; then
        break
    fi
    printf 'status=%s\n' "${code}" >>"${ARTIFACT_DIR}/q4-ready-progress.txt"
    sleep 1
done
[[ -s "${ARTIFACT_DIR}/q4-ready-probe.json" ]] || { echo "Q4 server did not reach real completion readiness" >&2; exit 1; }

# Require the candidate to preserve deterministic arithmetic, JSON, and the
# streamed OpenAI response contract before collecting any TPS evidence.  This
# suite is distinct from the marker retrieval workload below, preventing a
# throughput-only result from being mistaken for a quality qualification.
PYTHONPATH="${SOURCE_DIR}/python" "${ROOT_DIR}/.venv/bin/python" "${QUALITY_SUITE}" \
    --base-url http://127.0.0.1:1922/v1 --model "${MODEL}" \
    --expected-host david-Gmktec-x2-2 --artifact "${ARTIFACT_DIR}/quality-suite.json" \
    >"${ARTIFACT_DIR}/quality-suite.log" 2>&1

PYTHONPATH="${SOURCE_DIR}/python" "${ROOT_DIR}/.venv/bin/python" "${HARNESS}" \
    --base-url http://127.0.0.1:1922/v1 --model "${MODEL}" \
    --expected-host david-Gmktec-x2-2 --filler-repetitions 48 --sample-variation prefix_nonce \
    --samples 3 --max-tokens 16 --artifact "${ARTIFACT_DIR}/cold-prefill.json" \
    >"${ARTIFACT_DIR}/cold-prefill.log" 2>&1
if [[ "${GMK_EVO_X2_QWEN_COLD_CONCURRENT:-0}" == "1" ]]; then
    # One synchronized C4 round retains a single cold-admission epoch. Each
    # client gets an early unique prefix so it cannot reuse a prior user prompt.
    PYTHONPATH="${SOURCE_DIR}/python" "${ROOT_DIR}/.venv/bin/python" \
        "${SOURCE_DIR}/benchmarks/gmk_evo_x2/run_concurrent_api_control.py" \
        --base-url http://127.0.0.1:1922/v1 --model "${MODEL}" \
        --tokenizer "${ROOT_DIR}/models/Qwen3.6-35B-A3B-NVFP4" \
        --expected-host david-Gmktec-x2-2 --concurrency 4 --rounds 1 \
        --sample-variation prefix_nonce --artifact "${ARTIFACT_DIR}/cold-concurrent-c4.json" \
        >"${ARTIFACT_DIR}/cold-concurrent-c4.log" 2>&1
fi
printf 'q4_quality_and_cold_prefill_control=passed moe_k_two_rows=%s moe_k_three_rows=%s grouped_prefill_min_tokens=%s grouped_prefill_mode=%s\n' \
    "${MOE_K_TWO_ROWS}" "${MOE_K_THREE_ROWS}" "${GROUPED_PREFILL_MIN_TOKENS}" "${GROUPED_PREFILL_MODE}" >"${ARTIFACT_DIR}/result.txt"
