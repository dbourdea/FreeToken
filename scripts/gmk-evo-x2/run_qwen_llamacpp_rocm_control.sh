#!/usr/bin/env bash
# Run the isolated ROCm 10 llama.cpp Qwen3.6-35B-A3B control on GMKtec EVO-X2.
#
# This script intentionally starts a short-lived loopback-only llama.cpp server
# on port 1921. It never contacts llama-swap, modifies its configuration, stops
# the FreeToken service on port 1919, or uses another LAN host. The server is
# terminated by the EXIT trap after evidence capture, including on a failure.

set -euo pipefail

# Keep the precise source revision, model revision, local model path, and API
# identity visible in the command itself so the comparison can be reproduced
# without guessing which llama.cpp build or Qwen quantization was selected.
readonly ROOT_DIR="/home/david/freetoken-amd"
# Permit the protected controller to use the same current isolated source for
# this server and its benchmark harness, while retaining the old checkout as
# the compatibility default for existing direct invocations.
readonly SOURCE_DIR="${FREETOKEN_LLAMA_CONTROL_SOURCE_DIR:-${ROOT_DIR}/source-qwen-harness-d6ee8ce}"
readonly LLAMA_SERVER="${ROOT_DIR}/llama.cpp-rocm10-b10141/build-rocm10-clang/bin/llama-server"
readonly MODEL_DIR="${ROOT_DIR}/models/controls/qwen36-35b-a3b-unsloth-a483e9e6"
readonly MODEL_FILE="${MODEL_DIR}/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
readonly TOKENIZER_DIR="${ROOT_DIR}/models/Qwen3.6-35B-A3B-NVFP4"
readonly MODEL_NAME="qwen3.6-35b-a3b-q4km-llamacpp-rocm10"
readonly BASE_URL="http://127.0.0.1:1921/v1"
readonly ARTIFACT_ROOT="${1:-${ROOT_DIR}/artifacts/qwen35b-llamacpp-rocm10-$(date -u +%Y%m%dT%H%M%SZ)}"
readonly BENCHMARK_DIR="${ARTIFACT_ROOT}/benchmark"
readonly SERVER_LOG="${ARTIFACT_ROOT}/llama-server.log"
readonly SERVER_PID_FILE="${ARTIFACT_ROOT}/llama-server.pid"
# Keep concurrent measurement opt-in so the existing single-client control is
# unchanged unless a protected time-share controller explicitly requests C4.
readonly CONCURRENT_CLIENTS="${GMK_EVO_X2_QWEN_CONCURRENT_CLIENTS:-0}"
# Keep the historical one-slot server as the direct-control default. A protected
# C4 comparison explicitly selects four slots so llama.cpp does not serialize
# four arriving clients while FreeToken admits four live requests.
readonly PARALLEL_SLOTS="${GMK_EVO_X2_LLAMA_PARALLEL_SLOTS:-1}"

# Refuse ambiguous or partial input before allocating GPU memory. The matching
# FreeToken tokenizer counts generated text consistently across both endpoints.
if [[ ! -x "${LLAMA_SERVER}" ]]; then
    echo "error: ROCm llama-server is missing or not executable: ${LLAMA_SERVER}" >&2
    exit 2
fi
if [[ ! -f "${MODEL_FILE}" ]]; then
    echo "error: matching Qwen GGUF is missing: ${MODEL_FILE}" >&2
    exit 2
fi
if [[ ! -d "${TOKENIZER_DIR}" ]]; then
    echo "error: FreeToken Qwen tokenizer directory is missing: ${TOKENIZER_DIR}" >&2
    exit 2
fi
if [[ -e "${ARTIFACT_ROOT}" ]]; then
    echo "error: artifact root already exists: ${ARTIFACT_ROOT}" >&2
    exit 2
fi
if [[ "${CONCURRENT_CLIENTS}" != "0" && "${CONCURRENT_CLIENTS}" != "4" ]]; then
    echo "error: GMK_EVO_X2_QWEN_CONCURRENT_CLIENTS must be 0 or 4" >&2
    exit 2
fi
if [[ "${PARALLEL_SLOTS}" != "1" && "${PARALLEL_SLOTS}" != "4" ]]; then
    echo "error: GMK_EVO_X2_LLAMA_PARALLEL_SLOTS must be 1 or 4" >&2
    exit 2
fi

mkdir -p "${ARTIFACT_ROOT}"

# ROCm 10's llama.cpp build dynamically links LLVM's libclang runtime. Extend
# only this script's process environment so global shell and service settings
# remain unchanged. Keep any pre-existing library path entries available too.
export LD_LIBRARY_PATH="/opt/rocm-10.0/llvm/lib:/opt/rocm-10.0/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"

# Stop only the temporary child recorded by this script. The guard prevents a
# malformed PID file from targeting another process, and wait reaps the child
# before leaving its raw server log and benchmark evidence on disk.
cleanup_server() {
    if [[ -f "${SERVER_PID_FILE}" ]]; then
        local server_pid
        server_pid="$(<"${SERVER_PID_FILE}")"
        if [[ "${server_pid}" =~ ^[0-9]+$ ]] && kill -0 "${server_pid}" 2>/dev/null; then
            kill "${server_pid}" 2>/dev/null || true
            wait "${server_pid}" 2>/dev/null || true
        fi
    fi
}
trap cleanup_server EXIT

# Start the exact ROCm 10 b10141 control on an otherwise unused loopback port.
# One slot, 8,192 context tokens, full GPU offload, Flash Attention, and Q8 KV
# cache retain the previously documented GMKtec EVO-X2 ROCm control conventions.
"${LLAMA_SERVER}" \
    -m "${MODEL_FILE}" \
    --alias "${MODEL_NAME}" \
    -ngl all \
    -c 8192 \
    -np "${PARALLEL_SLOTS}" \
    -b 2048 \
    -ub 512 \
    -ctk q8_0 \
    -ctv q8_0 \
    -fa on \
    --jinja \
    --reasoning-format deepseek \
    --no-context-shift \
    --no-warmup \
    --metrics \
    --slots \
    --host 127.0.0.1 \
    --port 1921 >"${SERVER_LOG}" 2>&1 &
echo "$!" >"${SERVER_PID_FILE}"

# Wait for a definite local health response, reporting the preserved server log
# if initialization fails rather than silently benchmarking a different server.
for _ in $(seq 1 180); do
    if curl -fsS "${BASE_URL%/v1}/health" >"${ARTIFACT_ROOT}/health-ready.json"; then
        break
    fi
    if ! kill -0 "$(<"${SERVER_PID_FILE}")" 2>/dev/null; then
        echo "error: temporary llama.cpp server exited during initialization" >&2
        tail -n 120 "${SERVER_LOG}" >&2 || true
        exit 1
    fi
    sleep 1
done
if [[ ! -s "${ARTIFACT_ROOT}/health-ready.json" ]]; then
    echo "error: temporary llama.cpp server was not healthy within 180 seconds" >&2
    exit 1
fi

# Delegate the unchanged fixed workload to the existing harness while overriding
# only endpoint identity and tokenizer location for this temporary control.
GMK_EVO_X2_QWEN_BASE_URL="${BASE_URL}" \
GMK_EVO_X2_QWEN_MODEL_NAME="${MODEL_NAME}" \
GMK_EVO_X2_QWEN_TOKENIZER_DIR="${TOKENIZER_DIR}" \
GMK_EVO_X2_QWEN_BENCHMARK_SOURCE_DIR="${SOURCE_DIR}" \
    bash "${SOURCE_DIR}/scripts/gmk-evo-x2/run_qwen_scheduler_baseline.sh" "${BENCHMARK_DIR}"

# Use the same synchronized four-client client harness as the FreeToken Q4
# control when explicitly requested. The JSON retains API usage, aggregate
# prompt-prefill TPS, aggregate decode TPS, TTFT, and token-gap evidence.
if [[ "${CONCURRENT_CLIENTS}" == "4" ]]; then
    PYTHONPATH="${SOURCE_DIR}/python" "${ROOT_DIR}/.venv/bin/python" \
        "${SOURCE_DIR}/benchmarks/gmk_evo_x2/run_concurrent_api_control.py" \
        --base-url "${BASE_URL}" --model "${MODEL_NAME}" \
        --tokenizer "${TOKENIZER_DIR}" --artifact "${ARTIFACT_ROOT}/concurrent-c4.json" \
        --concurrency 4 --rounds 3 >"${ARTIFACT_ROOT}/concurrent-c4.log" 2>&1
fi

if [[ "${GMK_EVO_X2_QWEN_QUALITY_SUITE:-}" == "1" ]]; then
    # The optional suite uses only deterministic visible-output controls.  Keep
    # it opt-in so the normal throughput control remains unchanged, while a
    # paired quality campaign can run against this exact temporary ROCm server.
    PYTHONPATH="${SOURCE_DIR}/python" "${ROOT_DIR}/.venv/bin/python" \
        "${SOURCE_DIR}/benchmarks/gmk_evo_x2/run_quality_suite.py" \
        --base-url "${BASE_URL}" \
        --model "${MODEL_NAME}" \
        --expected-host "david-Gmktec-x2-2" \
        --max-tokens 64 \
        --artifact "${ARTIFACT_ROOT}/quality.json" \
        >"${ARTIFACT_ROOT}/quality.log" 2>&1
fi

if [[ "${GMK_EVO_X2_QWEN_COLD_PREFILL_CONTROL:-}" == "1" ]]; then
    # A unique early nonce forces every long prompt to miss the full prefix
    # cache.  This separates genuine prompt-processing work from the cache-hit
    # rounds that can otherwise inflate a repeated-prompt API benchmark.
    PYTHONPATH="${SOURCE_DIR}/python" "${ROOT_DIR}/.venv/bin/python" \
        "${SOURCE_DIR}/benchmarks/gmk_evo_x2/run_long_context_control.py" \
        --base-url "${BASE_URL}" --model "${MODEL_NAME}" \
        --expected-host "david-Gmktec-x2-2" --filler-repetitions 48 \
        --sample-variation prefix_nonce --samples 3 --max-tokens 16 \
        --artifact "${ARTIFACT_ROOT}/cold-prefill.json" \
        >"${ARTIFACT_ROOT}/cold-prefill.log" 2>&1
fi

# Capture final endpoint health before the EXIT trap terminates the control.
curl -fsS "${BASE_URL%/v1}/health" >"${ARTIFACT_ROOT}/health-before-cleanup.json"
