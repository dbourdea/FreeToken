#!/usr/bin/env bash
# Gate an opt-in Q4_K/Q5_K long-prefill MoE candidate on GMKtec EVO-X2.
#
# This controller proves a real completion from the protected normal service,
# stops it only after that preflight, runs vector and candidate component screens
# on the original Qwen Q4_K_M expert bytes, and restores a completion-capable
# normal service on every exit path.  It is intentionally not an API-TPS claim:
# only a parity-passing component winner can advance to a protected API gate.

set -euo pipefail

# The caller must provide a new directory.  The controller creates it itself so
# an accidental pre-created directory cannot invalidate immutable evidence.
readonly ARTIFACT_DIR="${1:?usage: run_qwen_q4_grouped_prefill_gate.sh ARTIFACT_DIR}"
readonly SOURCE_DIR="${FREETOKEN_Q4_SOURCE_DIR:?set FREETOKEN_Q4_SOURCE_DIR}"
readonly ROOT_DIR="/home/david/freetoken-amd"
readonly RECOVERY_SOURCE="${ROOT_DIR}/source-qwen-recovery-d6ee8cef479c"
readonly MODEL_PATH="${ROOT_DIR}/models/controls/qwen36-35b-a3b-unsloth-a483e9e6/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf"
readonly BENCHMARK="${SOURCE_DIR}/benchmarks/gmk_evo_x2/bench_qwen_q4_grouped_prefill.py"
readonly EXTENSION_CACHE="${ROOT_DIR}/cache/torch_extensions-q4-grouped-prefill-f1baf13"
readonly TRITON_CACHE="${ROOT_DIR}/cache/triton-q4-grouped-prefill-f1baf13"
# Keep the original both-projection screen as the default.  A caller can select
# one grouped projection for a diagnostic component screen; API promotion still
# requires a separate exact-output gate.
readonly GROUPED_MODE="${FREETOKEN_Q4_GROUPED_MODE:-both}"
# Select the candidate family without changing the normal serving default.
# ``grouped`` retains the original route-sort experiment. ``two_rows`` selects
# the HIP one-wave/two-output-row vector experiment. Both remain component-only
# gates and neither changes the recovery server or production defaults.
readonly COMPONENT_CANDIDATE="${FREETOKEN_Q4_COMPONENT_CANDIDATE:-grouped}"
# Keep occupancy selection explicit in evidence. One is the qualified two-row
# compile target; two is a single bounded candidate, not a serving default.
readonly TWO_ROWS_MIN_BLOCKS="${FREETOKEN_Q4_TWO_ROWS_MIN_BLOCKS:-1}"
# Separate controls are needed only for a diagnostic that keeps Q4_K at its
# qualified one-block target while testing Q5_K's independent residency.
readonly Q4_TWO_ROWS_MIN_BLOCKS="${FREETOKEN_Q4_Q4_TWO_ROWS_MIN_BLOCKS:-${TWO_ROWS_MIN_BLOCKS}}"
readonly Q5_TWO_ROWS_MIN_BLOCKS="${FREETOKEN_Q4_Q5_TWO_ROWS_MIN_BLOCKS:-${TWO_ROWS_MIN_BLOCKS}}"
readonly NORMAL_REQUEST='{"model":"qwen3.6-35b-a3b-nvfp4-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":4,"temperature":0,"stream":false}'

[[ ! -e "${ARTIFACT_DIR}" ]] || { echo "artifact directory already exists: ${ARTIFACT_DIR}" >&2; exit 2; }
[[ "${GROUPED_MODE}" == "both" || "${GROUPED_MODE}" == "gate_up" || "${GROUPED_MODE}" == "down" ]] || {
    echo "FREETOKEN_Q4_GROUPED_MODE must be both, gate_up, or down" >&2
    exit 2
}
[[ "${COMPONENT_CANDIDATE}" == "grouped" || "${COMPONENT_CANDIDATE}" == "two_rows" ]] || {
    echo "FREETOKEN_Q4_COMPONENT_CANDIDATE must be grouped or two_rows" >&2
    exit 2
}
[[ "${TWO_ROWS_MIN_BLOCKS}" == "1" || "${TWO_ROWS_MIN_BLOCKS}" == "2" ]] || {
    echo "FREETOKEN_Q4_TWO_ROWS_MIN_BLOCKS must be 1 or 2" >&2
    exit 2
}
[[ "${Q4_TWO_ROWS_MIN_BLOCKS}" == "1" || "${Q4_TWO_ROWS_MIN_BLOCKS}" == "2" ]] || {
    echo "FREETOKEN_Q4_Q4_TWO_ROWS_MIN_BLOCKS must be 1 or 2" >&2
    exit 2
}
[[ "${Q5_TWO_ROWS_MIN_BLOCKS}" == "1" || "${Q5_TWO_ROWS_MIN_BLOCKS}" == "2" ]] || {
    echo "FREETOKEN_Q4_Q5_TWO_ROWS_MIN_BLOCKS must be 1 or 2" >&2
    exit 2
}
mkdir -p "${ARTIFACT_DIR}"

# Return an HTTP status only while retaining the full completion response for
# recovery evidence and human inspection.
normal_status() {
    local output="$1"
    curl -sS -m 45 -o "${output}" -w '%{http_code}' \
        -H 'Content-Type: application/json' -d "${NORMAL_REQUEST}" \
        http://127.0.0.1:1919/v1/chat/completions
}

# Restore the protected service even if an extension build, Triton compilation,
# parity assertion, or timing run fails.  A models-list probe is insufficient:
# recovery requires a real completion response.
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

# Validate every static prerequisite before taking ownership of service recovery.
for required in "${MODEL_PATH}" "${BENCHMARK}" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh" \
    "${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh"; do
    [[ -f "${required}" ]] || { echo "missing required file: ${required}" >&2; exit 2; }
done

trap recover_normal_service EXIT

# Do not interrupt an already unhealthy production service.
preflight_code="$(normal_status "${ARTIFACT_DIR}/preflight.json" || true)"
[[ "${preflight_code}" == "200" ]] || { echo "normal API unavailable before grouped gate: ${preflight_code}" >&2; exit 1; }
"${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh" \
    >"${ARTIFACT_DIR}/normal-stop.txt" 2>&1
mkdir -p "${EXTENSION_CACHE}" "${TRITON_CACHE}"

# The vector reference keeps grouped dispatch disabled.  It builds and warms
# the native extension before events begin, producing an output artifact for
# the candidate parity assertion.
PYTHONPATH="${SOURCE_DIR}/python" TORCH_EXTENSIONS_DIR="${EXTENSION_CACHE}" \
TRITON_CACHE_DIR="${TRITON_CACHE}" PYTORCH_ROCM_ARCH=gfx1151 \
FREETOKEN_Q4_GROUPED_PREFILL_MIN_TOKENS=0 \
"${ROOT_DIR}/.venv/bin/python" "${BENCHMARK}" \
    --model "${MODEL_PATH}" --mode vector --tokens 1024 --warmup 8 --repetitions 20 \
    --json "${ARTIFACT_DIR}/vector.json" --save-output "${ARTIFACT_DIR}/vector-output.pt" \
    >"${ARTIFACT_DIR}/vector.log" 2>&1

if [[ "${COMPONENT_CANDIDATE}" == "grouped" ]]; then
    # The grouped run compiles and warms route alignment before timing.  It
    # must match the saved vector output under explicit tolerances before it
    # can record a passed component result.
    PYTHONPATH="${SOURCE_DIR}/python" TORCH_EXTENSIONS_DIR="${EXTENSION_CACHE}" \
    TRITON_CACHE_DIR="${TRITON_CACHE}" PYTORCH_ROCM_ARCH=gfx1151 \
    FREETOKEN_Q4_GROUPED_PREFILL_MIN_TOKENS=1024 \
    FREETOKEN_Q4_GROUPED_PREFILL_MODE="${GROUPED_MODE}" \
    "${ROOT_DIR}/.venv/bin/python" "${BENCHMARK}" \
        --model "${MODEL_PATH}" --mode grouped --grouped-mode "${GROUPED_MODE}" \
        --tokens 1024 --warmup 8 --repetitions 20 \
        --json "${ARTIFACT_DIR}/grouped.json" --reference-output "${ARTIFACT_DIR}/vector-output.pt" \
        >"${ARTIFACT_DIR}/grouped.log" 2>&1
    printf 'candidate=grouped mode=%s\n' "${GROUPED_MODE}" >"${ARTIFACT_DIR}/candidate.txt"
else
    # This kernel candidate changes only how two adjacent real Q4_K/Q5_K rows
    # share one HIP wave.  The saved production-vector output is the strict
    # reference, so a timing result is retained only if numerical parity holds.
    PYTHONPATH="${SOURCE_DIR}/python" TORCH_EXTENSIONS_DIR="${EXTENSION_CACHE}" \
    TRITON_CACHE_DIR="${TRITON_CACHE}" PYTORCH_ROCM_ARCH=gfx1151 \
    FREETOKEN_Q4_GROUPED_PREFILL_MIN_TOKENS=0 FREETOKEN_GGUF_MOE_K_TWO_ROWS=1 \
    FREETOKEN_GGUF_MOE_K_TWO_ROWS_MIN_BLOCKS="${TWO_ROWS_MIN_BLOCKS}" \
    FREETOKEN_GGUF_Q4_K_TWO_ROWS_MIN_BLOCKS="${Q4_TWO_ROWS_MIN_BLOCKS}" \
    FREETOKEN_GGUF_Q5_K_TWO_ROWS_MIN_BLOCKS="${Q5_TWO_ROWS_MIN_BLOCKS}" \
    "${ROOT_DIR}/.venv/bin/python" "${BENCHMARK}" \
        --model "${MODEL_PATH}" --mode vector --vector-two-rows \
        --two-rows-min-blocks "${TWO_ROWS_MIN_BLOCKS}" \
        --q4-two-rows-min-blocks "${Q4_TWO_ROWS_MIN_BLOCKS}" \
        --q5-two-rows-min-blocks "${Q5_TWO_ROWS_MIN_BLOCKS}" \
        --tokens 1024 --warmup 8 --repetitions 20 \
        --json "${ARTIFACT_DIR}/two-rows.json" --reference-output "${ARTIFACT_DIR}/vector-output.pt" \
        >"${ARTIFACT_DIR}/two-rows.log" 2>&1
    printf 'candidate=two_rows min_blocks=%s q4_min_blocks=%s q5_min_blocks=%s\n' \
        "${TWO_ROWS_MIN_BLOCKS}" "${Q4_TWO_ROWS_MIN_BLOCKS}" "${Q5_TWO_ROWS_MIN_BLOCKS}" \
        >"${ARTIFACT_DIR}/candidate.txt"
fi

# A passed marker means both runs completed, grouped output matched the saved
# vector reference, and timing evidence exists.  It makes no API claim.
printf 'real_q4_component_candidate_parity_and_timing=passed\n' >"${ARTIFACT_DIR}/result.txt"
