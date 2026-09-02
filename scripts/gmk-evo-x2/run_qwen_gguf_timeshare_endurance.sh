#!/usr/bin/env bash
# Run a long isolated Q4 endurance battery and restore GMKtec EVO-X2's NVFP4 service.
#
# This controller owns one deliberate GPU time-share window. It does not touch
# llama-swap or any LAN endpoint. It stops the verified dedicated loopback
# recovery session, starts the isolated Q4 test session, runs the existing
# process-scoped battery, and restores the normal service even when the battery
# fails or the controller receives a termination signal.

set -euo pipefail

# Require a caller-owned immutable root, then permit the full 24-hour default
# while also allowing a shorter explicitly labelled diagnostic duration.
readonly ARTIFACT_ROOT="${1:?usage: run_qwen_gguf_timeshare_endurance.sh ARTIFACT_ROOT [SESSION_COUNT] [INTERVAL_SECONDS]}"
readonly SESSION_COUNT="${2:-1440}"
readonly INTERVAL_SECONDS="${3:-60}"
# Keep the exact HIP row-selector state explicit. Endurance lasts long enough
# that an inherited environment would make the resulting evidence ambiguous.
# These controls match the isolated full API gate and default to the qualified
# generic vector route, so normal invocations do not change behavior.
readonly Q4_K_FOUR_ROWS="${FREETOKEN_Q4_Q4_K_FOUR_ROWS:-0}"
readonly Q5_K_FOUR_ROWS="${FREETOKEN_Q4_Q5_K_FOUR_ROWS:-0}"
# Match the C139 full API configuration by default. Both values remain
# caller-visible and are written into the artifact so an endurance result can
# never be mistaken for a different allocation or overlap profile.
readonly MEMORY_RATIO="${FREETOKEN_Q4_MEMORY_RATIO:-0.30}"
readonly PREFILL_OVERLAP="${FREETOKEN_Q4_PREFILL_OVERLAP:-1}"
# A swap drain is an opt-in residency repair. It is never enabled implicitly:
# when selected, the controller disables all configured swap only after it has
# stopped the normal service, then restores swap before normal recovery.
readonly DRAIN_SWAP="${FREETOKEN_Q4_DRAIN_SWAP:-0}"

# Keep every host-specific path explicit so an invocation cannot silently
# operate on another machine's service or an arbitrary source checkout.
readonly ROOT_DIR="/home/david/freetoken-amd"
readonly Q4_SOURCE_DIR="${FREETOKEN_Q4_SOURCE_DIR:?set FREETOKEN_Q4_SOURCE_DIR to an isolated Q4 worktree}"
readonly RECOVERY_SOURCE_DIR="${FREETOKEN_RECOVERY_SOURCE_DIR:?set FREETOKEN_RECOVERY_SOURCE_DIR to the recovery-launcher worktree}"
readonly Q4_LAUNCHER="${Q4_SOURCE_DIR}/scripts/gmk-evo-x2/launch_qwen_gguf_qualified.sh"
readonly Q4_BATTERY="${Q4_SOURCE_DIR}/scripts/gmk-evo-x2/run_qwen_gguf_endurance_battery.sh"
readonly RECOVERY_STOPPER="${RECOVERY_SOURCE_DIR}/scripts/gmk-evo-x2/stop_qwen_recovery_server.sh"
readonly RECOVERY_STARTER="${RECOVERY_SOURCE_DIR}/scripts/gmk-evo-x2/start_qwen_recovery_server.sh"
readonly Q4_ARTIFACT_DIR="${ARTIFACT_ROOT}/q4-server"
readonly BATTERY_ARTIFACT_DIR="${ARTIFACT_ROOT}/battery"
readonly RECOVERY_ARTIFACT="${ARTIFACT_ROOT}/recovery-health.json"

# Reject unsafe input before stopping the protected model service or creating
# any artifact. The source guards mirror the candidate launcher safeguards.
case "${SESSION_COUNT}" in ''|*[!0-9]*) echo "session count must be positive" >&2; exit 2;; esac
case "${INTERVAL_SECONDS}" in ''|*[!0-9]*) echo "interval must be non-negative" >&2; exit 2;; esac
(( SESSION_COUNT > 0 )) || { echo "session count must be positive" >&2; exit 2; }
[[ "${Q4_K_FOUR_ROWS}" == "0" || "${Q4_K_FOUR_ROWS}" == "1" ]] || { echo "FREETOKEN_Q4_Q4_K_FOUR_ROWS must be 0 or 1" >&2; exit 2; }
[[ "${Q5_K_FOUR_ROWS}" == "0" || "${Q5_K_FOUR_ROWS}" == "1" ]] || { echo "FREETOKEN_Q4_Q5_K_FOUR_ROWS must be 0 or 1" >&2; exit 2; }
[[ "${MEMORY_RATIO}" =~ ^0\.[0-9]+$|^1\.0+$ ]] || { echo "FREETOKEN_Q4_MEMORY_RATIO is invalid" >&2; exit 2; }
[[ "${PREFILL_OVERLAP}" == "0" || "${PREFILL_OVERLAP}" == "1" ]] || { echo "FREETOKEN_Q4_PREFILL_OVERLAP must be 0 or 1" >&2; exit 2; }
[[ "${DRAIN_SWAP}" == "0" || "${DRAIN_SWAP}" == "1" ]] || { echo "FREETOKEN_Q4_DRAIN_SWAP must be 0 or 1" >&2; exit 2; }
[[ ! -e "${ARTIFACT_ROOT}" ]] || { echo "artifact root already exists: ${ARTIFACT_ROOT}" >&2; exit 2; }
[[ "${Q4_SOURCE_DIR}" == "${ROOT_DIR}/source-qwen-"* ]] || { echo "Q4 source must be under ${ROOT_DIR}" >&2; exit 2; }
[[ "${RECOVERY_SOURCE_DIR}" == "${ROOT_DIR}/source-qwen-"* ]] || { echo "recovery source must be under ${ROOT_DIR}" >&2; exit 2; }
[[ -f "${Q4_LAUNCHER}" && -f "${Q4_BATTERY}" && -f "${RECOVERY_STOPPER}" && -f "${RECOVERY_STARTER}" ]] || {
    echo "missing time-share dependency" >&2
    exit 2
}

# Poll the documented health state instead of treating a bound port or model
# listing as proof that a cold server has loaded all expert banks.
wait_for_serving() {
    local port="$1" destination="$2" status maintenance missing_listener=0
    for _ in $(seq 1 900); do
        # A launch may need a few seconds to bind the port, but a missing
        # listener for a sustained interval means the candidate exited and the
        # controller must enter recovery instead of waiting the full timeout.
        if ss -ltn "( sport = :${port} )" | grep -q ":${port}"; then
            missing_listener=0
        else
            missing_listener=$((missing_listener + 1))
            if (( missing_listener >= 30 )); then
                echo "server on port ${port} exited before readiness" >&2
                return 1
            fi
        fi
        curl -fsS --max-time 5 "http://127.0.0.1:${port}/health" >"${destination}" 2>/dev/null || true
        status="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status", ""))' "${destination}" 2>/dev/null || true)"
        maintenance="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("maintenance", ""))' "${destination}" 2>/dev/null || true)"
        [[ "${status}" == "ok" && "${maintenance}" == "serving" ]] && return 0
        sleep 1
    done
    echo "server on port ${port} did not reach serving state" >&2
    return 1
}

# Restore in every exit path. The Q4 launcher verifies its own exact process
# group before signalling it, and the recovery launcher creates the dedicated
# group needed by future time-share windows.
restore_normal_service() {
    local status=0
    if [[ -f "${Q4_ARTIFACT_DIR}/server.pid" ]]; then
        FREETOKEN_Q4_SOURCE_DIR="${Q4_SOURCE_DIR}" bash "${Q4_LAUNCHER}" stop "${Q4_ARTIFACT_DIR}" || status=1
    fi
    # Re-enable every configured swap device before restarting the normal model.
    # The boolean is set only after swapoff succeeds, avoiding an unrelated
    # swapon attempt if privilege or capacity preflight fails.
    if [[ "${swap_disabled}" == "1" ]]; then
        sudo -n swapon -a || status=1
        free -h >"${ARTIFACT_ROOT}/memory-after-swapon.txt" || true
    fi
    if ! curl -fsS --max-time 5 http://127.0.0.1:1919/health >"${RECOVERY_ARTIFACT}" 2>/dev/null; then
        bash "${RECOVERY_STARTER}" >"${ARTIFACT_ROOT}/recovery-start.log" 2>&1 || status=1
    fi
    wait_for_serving 1919 "${RECOVERY_ARTIFACT}" || status=1
    return "${status}"
}

mkdir -p "${ARTIFACT_ROOT}"
printf 'started_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"${ARTIFACT_ROOT}/controller.txt"
printf 'session_count=%s\ninterval_seconds=%s\nq4_k_four_rows=%s\nq5_k_four_rows=%s\nmemory_ratio=%s\nprefill_overlap=%s\ndrain_swap=%s\n' \
    "${SESSION_COUNT}" "${INTERVAL_SECONDS}" "${Q4_K_FOUR_ROWS}" "${Q5_K_FOUR_ROWS}" "${MEMORY_RATIO}" "${PREFILL_OVERLAP}" "${DRAIN_SWAP}" \
    >>"${ARTIFACT_ROOT}/controller.txt"
# Record the original state before any host-level action. This lets a later
# reviewer distinguish the host's existing swapped pages from the candidate's
# own process-scoped swap gate.
free -h >"${ARTIFACT_ROOT}/memory-before-swap-policy.txt"
swap_disabled=0
trap 'restore_normal_service' EXIT INT TERM

# Establish noninteractive swap authority before taking the protected service
# offline. A missing sudo grant now leaves both swap and normal serving intact.
if [[ "${DRAIN_SWAP}" == "1" ]]; then
    sudo -n true
fi

# The stopper refuses an unmanaged legacy tree. That fail-closed behavior
# prevents this controller from guessing at child ownership on a shared host.
bash "${RECOVERY_STOPPER}"
if [[ "${DRAIN_SWAP}" == "1" ]]; then
    # Empty swap only after normal Qwen has released its resident model pages.
    sudo -n swapoff -a
    swap_disabled=1
    free -h >"${ARTIFACT_ROOT}/memory-after-swapoff.txt"
fi
# Pass both selectors to the isolated launcher explicitly. This keeps the
# normal recovery service free of experimental settings and makes the long-run
# candidate precisely reproducible from controller.txt alone.
FREETOKEN_Q4_SOURCE_DIR="${Q4_SOURCE_DIR}" \
FREETOKEN_GGUF_Q4_K_FOUR_ROWS="${Q4_K_FOUR_ROWS}" \
FREETOKEN_GGUF_Q5_K_FOUR_ROWS="${Q5_K_FOUR_ROWS}" \
FREETOKEN_Q4_PREFILL_OVERLAP="${PREFILL_OVERLAP}" \
    bash "${Q4_LAUNCHER}" start "${Q4_ARTIFACT_DIR}" "${MEMORY_RATIO}"
wait_for_serving 1922 "${ARTIFACT_ROOT}/q4-health.json"
FREETOKEN_Q4_SOURCE_DIR="${Q4_SOURCE_DIR}" bash "${Q4_BATTERY}" "${BATTERY_ARTIFACT_DIR}" "${SESSION_COUNT}" "${INTERVAL_SECONDS}"
# Ask the summarizer to write its own explicit artifact.  Redirecting stdout
# here would not satisfy its required --output contract and would make an
# otherwise successful battery look like a controller failure after the work
# had already completed.
"${ROOT_DIR}/.venv/bin/python" "${Q4_SOURCE_DIR}/benchmarks/gmk_evo_x2/summarize_qwen_gguf_endurance.py" \
    "${BATTERY_ARTIFACT_DIR}" --expected-sessions "${SESSION_COUNT}" \
    --output "${ARTIFACT_ROOT}/summary.json"
printf 'completed_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"${ARTIFACT_ROOT}/controller.txt"
