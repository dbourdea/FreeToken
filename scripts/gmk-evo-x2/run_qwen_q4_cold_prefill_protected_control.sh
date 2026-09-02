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
readonly MODEL="qwen36-35b-a3b-q4km-gguf-amd"
readonly NORMAL_REQUEST='{"model":"qwen3.6-35b-a3b-nvfp4-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":4,"temperature":0,"stream":false}'

[[ ! -e "${ARTIFACT_DIR}" ]] || { echo "artifact directory already exists: ${ARTIFACT_DIR}" >&2; exit 2; }
for required in "${LAUNCHER}" "${HARNESS}" "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh" "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh"; do
    [[ -f "${required}" ]] || { echo "missing required file: ${required}" >&2; exit 2; }
done
mkdir -p "${ARTIFACT_DIR}"

normal_status() {
    curl -sS -m 45 -o "$1" -w '%{http_code}' -H 'Content-Type: application/json' \
        -d "${NORMAL_REQUEST}" http://127.0.0.1:1919/v1/chat/completions
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
    "${LAUNCHER}" start "${ARTIFACT_DIR}/q4-server" 0.30 0
for _ in $(seq 1 480); do
    if curl -fsS http://127.0.0.1:1922/health >"${ARTIFACT_DIR}/q4-health.json"; then
        break
    fi
    sleep 1
done
[[ -s "${ARTIFACT_DIR}/q4-health.json" ]] || { echo "Q4 server did not become healthy" >&2; exit 1; }

PYTHONPATH="${SOURCE_DIR}/python" "${ROOT_DIR}/.venv/bin/python" "${HARNESS}" \
    --base-url http://127.0.0.1:1922/v1 --model "${MODEL}" \
    --expected-host david-Gmktec-x2-2 --filler-repetitions 48 --sample-variation prefix_nonce \
    --samples 3 --max-tokens 16 --artifact "${ARTIFACT_DIR}/cold-prefill.json" \
    >"${ARTIFACT_DIR}/cold-prefill.log" 2>&1
printf 'q4_cold_prefill_control=passed\n' >"${ARTIFACT_DIR}/result.txt"
