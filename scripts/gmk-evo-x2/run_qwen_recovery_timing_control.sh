#!/usr/bin/env bash
# Measure protected Qwen restart-to-completion time on GMKtec EVO-X2.
#
# This controller intentionally measures a real OpenAI-compatible completion.
# A listener, a health response, or a model list can appear while serial expert
# loading is still in progress, so none of those states proves usable recovery.

set -euo pipefail

# The caller supplies a new immutable artifact directory. Refusing preexisting
# paths prevents accidental merging of two restart measurements.
readonly ARTIFACT_DIR="${1:?usage: run_qwen_recovery_timing_control.sh ARTIFACT_DIR}"
readonly ROOT_DIR="/home/david/freetoken-amd"
readonly RECOVERY_SOURCE="${ROOT_DIR}/source-qwen-recovery-d6ee8cef479c"
readonly START_SCRIPT="${RECOVERY_SOURCE}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh"
readonly STOP_SCRIPT="${RECOVERY_SOURCE}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh"
readonly COMPLETION_URL="http://127.0.0.1:1919/v1/chat/completions"
readonly HEALTH_URL="http://127.0.0.1:1919/health"
readonly REQUEST='{"model":"qwen3.6-35b-a3b-nvfp4-amd","messages":[{"role":"user","content":"Reply with exactly READY."}],"max_tokens":4,"temperature":0,"stream":false}'

[[ ! -e "${ARTIFACT_DIR}" ]] || { echo "artifact directory already exists: ${ARTIFACT_DIR}" >&2; exit 2; }
[[ -x "${START_SCRIPT}" && -x "${STOP_SCRIPT}" ]] || { echo "maintained recovery scripts are unavailable" >&2; exit 2; }
mkdir -p "${ARTIFACT_DIR}"

# Emit a monotonically comparable wall-clock marker. Python formats the value
# portably and avoids shell-specific fractional-second behavior.
timestamp() {
    python3 -c 'import time; print(f"{time.time():.6f}")'
}

# Write a real completion response and return its HTTP status. Keeping the body
# makes a later audit distinguish loading errors from valid generated output.
completion_status() {
    curl -sS -m 45 -o "${ARTIFACT_DIR}/completion-probe.json" -w '%{http_code}' \
        -H 'Content-Type: application/json' -d "${REQUEST}" "${COMPLETION_URL}"
}

# If any command after the stop fails, invoke the same maintained launcher and
# leave a completion probe record. This protects the normal service while the
# measurement controller is the temporary owner of its restart lifecycle.
recover_if_needed() {
    local code
    code="$(completion_status || true)"
    [[ "${code}" == "200" ]] && return 0
    "${START_SCRIPT}" >"${ARTIFACT_DIR}/trap-recovery-start.txt" 2>&1 || true
    for _ in $(seq 1 600); do
        code="$(completion_status || true)"
        [[ "${code}" == "200" ]] && return 0
        sleep 1
    done
    return 1
}
trap recover_if_needed EXIT

# Do not deliberately restart an unhealthy service. The preflight itself is a
# real completion and is retained as an artifact.
preflight_code="$(completion_status || true)"
[[ "${preflight_code}" == "200" ]] || { echo "protected Qwen preflight completion failed: ${preflight_code}" >&2; exit 1; }
printf 'preflight_completion=200\n' >"${ARTIFACT_DIR}/preflight.txt"

"${STOP_SCRIPT}" >"${ARTIFACT_DIR}/stop.log" 2>&1
for _ in $(seq 1 30); do
    ! curl -fsS -m 2 "${HEALTH_URL}" >/dev/null 2>&1 && break
    sleep 1
done

start_epoch="$(timestamp)"
"${START_SCRIPT}" >"${ARTIFACT_DIR}/start.log" 2>&1
printf 'start_epoch_seconds=%s\n' "${start_epoch}" >"${ARTIFACT_DIR}/timing.txt"

health_epoch=""
completion_epoch=""
for attempt in $(seq 1 600); do
    if [[ -z "${health_epoch}" ]] && curl -fsS -m 3 "${HEALTH_URL}" >"${ARTIFACT_DIR}/health-probe.json" 2>/dev/null; then
        health_epoch="$(timestamp)"
        printf 'health_epoch_seconds=%s attempts=%s\n' "${health_epoch}" "${attempt}" >>"${ARTIFACT_DIR}/timing.txt"
    fi
    code="$(completion_status || true)"
    if [[ "${code}" == "200" ]]; then
        completion_epoch="$(timestamp)"
        printf 'completion_epoch_seconds=%s attempts=%s\n' "${completion_epoch}" "${attempt}" >>"${ARTIFACT_DIR}/timing.txt"
        break
    fi
    sleep 1
done
[[ -n "${completion_epoch}" ]] || { echo "restart did not reach completion readiness" >&2; exit 1; }

# Calculate elapsed intervals once and record them with the raw markers.
python3 - "${start_epoch}" "${health_epoch:-0}" "${completion_epoch}" >>"${ARTIFACT_DIR}/timing.txt" <<'PY'
import sys
start, health, complete = map(float, sys.argv[1:])
if health:
    print(f"health_ready_seconds={health - start:.6f}")
print(f"completion_ready_seconds={complete - start:.6f}")
PY
printf 'qwen_restart_request_timing=passed\n' >"${ARTIFACT_DIR}/result.txt"
