#!/usr/bin/env bash
# Run one isolated Qwen3.8 dense-GGUF load and deterministic API gate.
#
# This controller is intentionally a load gate, not a throughput benchmark. It
# takes the GPU only after checking the protected Qwen endpoint, uses a separate
# loopback port and source tree, and restores the protected service before exit.

set -euo pipefail

readonly ROOT_DIR="/home/david/freetoken-amd"
readonly SOURCE_DIR="${QWEN35_DENSE_SOURCE_DIR:-/tmp/qwen35-dense-port}"
readonly MODEL_PATH="/home/david/models/qwen38-27b-ggml-org-0669b986/Qwen3.8-27B-Q4_K_M.gguf"
readonly RECOVERY_SOURCE="${ROOT_DIR}/source-qwen-recovery-d6ee8cef479c"
readonly VENV_PYTHON="${ROOT_DIR}/.venv/bin/python"
readonly CANDIDATE_PORT="1922"
readonly NORMAL_PORT="1919"
readonly CANDIDATE_MODEL="qwen3.8-27b-q4km-dense-amd"
readonly ARTIFACT_DIR="${ROOT_DIR}/artifacts/qwen35-dense-load-$(date -u +%Y%m%dT%H%M%SZ)"
readonly CANDIDATE_LOG="${ARTIFACT_DIR}/candidate.log"
readonly CANDIDATE_PID_FILE="${ARTIFACT_DIR}/candidate.pid"

mkdir -p "${ARTIFACT_DIR}"
test -d "${SOURCE_DIR}/python/freetoken"
test -f "${MODEL_PATH}"
test -x "${VENV_PYTHON}"

normal_health() { curl -fsS --max-time 5 "http://127.0.0.1:${NORMAL_PORT}/health"; }
candidate_health() { curl -fsS --max-time 5 "http://127.0.0.1:${CANDIDATE_PORT}/health"; }
candidate_process() {
    local pid="$1" cmdline
    [[ "${pid}" =~ ^[0-9]+$ ]] || return 1
    [[ -r "/proc/${pid}/cmdline" ]] || return 1
    cmdline="$(tr '\0' ' ' < /proc/${pid}/cmdline)"
    [[ "${cmdline}" == *"freetoken.cli serve"* ]] || return 1
    [[ "${cmdline}" == *"${MODEL_PATH}"* ]] || return 1
    [[ "${cmdline}" == *"--port ${CANDIDATE_PORT}"* ]] || return 1
}

normal_health >"${ARTIFACT_DIR}/normal-preflight.json"
pgrep -af "freetoken.cli serve.*--port ${NORMAL_PORT}" >"${ARTIFACT_DIR}/normal-preflight-process.txt"
"${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh" \
    >"${ARTIFACT_DIR}/normal-stop.log" 2>&1

cleanup() {
    set +e
    if [[ -f "${CANDIDATE_PID_FILE}" ]]; then
        local pid pgid
        pid="$(cat "${CANDIDATE_PID_FILE}")"
        if candidate_process "${pid}" && kill -0 "${pid}" 2>/dev/null; then
            pgid="$(ps -o pgid= -p "${pid}" | tr -d ' ')
            if [[ "${pgid}" == "${pid}" ]]; then
                kill -TERM -- "-${pgid}" 2>/dev/null || true
                for _ in $(seq 1 30); do
                    kill -0 "${pid}" 2>/dev/null || break
                    sleep 1
                done
                kill -KILL -- "-${pgid}" 2>/dev/null || true
            fi
        fi
    fi
    if ! normal_health >"${ARTIFACT_DIR}/normal-recovery-health.json" 2>/dev/null; then
        "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh" \
            >"${ARTIFACT_DIR}/normal-recovery.log" 2>&1 || true
        for _ in $(seq 1 600); do
            if normal_health >"${ARTIFACT_DIR}/normal-recovery-health.json" 2>/dev/null; then
                break
            fi
            sleep 1
        done
    fi
    if normal_health >"${ARTIFACT_DIR}/normal-final-health.json" 2>/dev/null; then
        printf '%s\n' recovery_health=passed >>"${ARTIFACT_DIR}/result.txt"
    else
        printf '%s\n' recovery_health=failed >>"${ARTIFACT_DIR}/result.txt"
    fi
}
trap cleanup EXIT

setsid nohup env \
    PYTHONPATH="${SOURCE_DIR}/python" \
    TORCH_EXTENSIONS_DIR="${ROOT_DIR}/cache/torch_extensions-qwen35-dense" \
    ROCM_HOME=/opt/rocm-10.0 ROCM_PATH=/opt/rocm-10.0 HIP_PATH=/opt/rocm-10.0 \
    "${VENV_PYTHON}" -m freetoken.cli serve \
    --model-path "${MODEL_PATH}" \
    --served-model-name "${CANDIDATE_MODEL}" \
    --host 127.0.0.1 --port "${CANDIDATE_PORT}" \
    --attention-backend triton --moe-backend fused \
    --max-seq-len-override 8192 --kv-reserve-tokens 8192 \
    --cuda-graph-max-bs 0 --disable-pynccl \
    >"${CANDIDATE_LOG}" 2>&1 < /dev/null &
echo "$!" >"${CANDIDATE_PID_FILE}"

for _ in $(seq 1 600); do
    if candidate_health >"${ARTIFACT_DIR}/candidate-health.json" 2>/dev/null; then
        break
    fi
    sleep 1
done
candidate_health >"${ARTIFACT_DIR}/candidate-final-health.json"
request_body="$(printf '{\"model\":\"%s\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly 4.\"}],\"max_tokens\":4,\"temperature\":0,\"stream\":false}' "${CANDIDATE_MODEL}")"
curl -fsS --max-time 120 "http://127.0.0.1:${CANDIDATE_PORT}/v1/chat/completions" \
    -H 'content-type: application/json' \
    -d "${request_body}" \
    >"${ARTIFACT_DIR}/completion.json"
printf '%s\n' load_and_completion=passed >"${ARTIFACT_DIR}/result.txt"
