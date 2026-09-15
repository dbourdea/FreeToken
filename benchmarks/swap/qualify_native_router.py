"""Opt-in native freetoken-swap routing benchmark for an approved Linux window.

It keeps raw requests, responses, daemon logs, catalog paths, and host details
inside a newly created private artifact directory.  It never changes protected
service enablement or configuration, and always attempts restoration after a
maintenance stop.  This is evidence collection, not a production launcher.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request


_NATIVE_AUTH_BASE: str | None = None
_NATIVE_API_KEY: str | None = None


def require_expected_hostname(expected: str, *, actual: str | None = None) -> str:
    """Require an exact operator-supplied host without disclosing either name."""
    actual = socket.gethostname() if actual is None else actual
    if not expected or "\x00" in expected or actual != expected:
        raise RuntimeError(
            "qualification host does not match the operator-supplied expected hostname"
        )
    return actual


def configure_native_auth(base: str, api_key: str) -> None:
    """Scope private router credentials to the exact temporary daemon origin."""
    global _NATIVE_AUTH_BASE, _NATIVE_API_KEY
    _NATIVE_AUTH_BASE = base.rstrip("/")
    _NATIVE_API_KEY = api_key


def _native_headers(url: str) -> dict[str, str]:
    if (
        _NATIVE_AUTH_BASE is not None
        and _NATIVE_API_KEY is not None
        and (url == _NATIVE_AUTH_BASE or url.startswith(_NATIVE_AUTH_BASE + "/"))
    ):
        return {"Authorization": f"Bearer {_NATIVE_API_KEY}"}
    return {}


def request_json(
    url: str,
    body: dict | None = None,
    *,
    timeout: float = 30,
    method: str | None = None,
) -> tuple[bytes, dict]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **_native_headers(url)},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return raw, json.loads(raw)


def request_bytes(url: str, *, timeout: float = 30) -> bytes:
    request = urllib.request.Request(url, headers=_native_headers(url))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def wait_json(url: str, *, seconds: float) -> dict:
    deadline = time.monotonic() + seconds
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return request_json(url, timeout=3)[1]
        except (OSError, ValueError, urllib.error.HTTPError) as exc:
            last = exc
            time.sleep(0.25)
    raise TimeoutError(f"endpoint did not become available: {last!r}")


def canary(url: str, model: str, *, direct: bool) -> tuple[bytes, dict]:
    """Make one deterministic request and retain raw bytes only in private artifacts."""
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "What is 2 + 2? Reply with only the single digit."}],
        "temperature": 0,
        "max_tokens": 32,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {"enable_thinking": False},
    }
    request = urllib.request.Request(
        url + "/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **_native_headers(url)},
    )
    raw = bytearray()
    content: list[str] = []
    started = time.monotonic()
    first_byte_s: float | None = None
    first_token_s: float | None = None
    completion_tokens: int | None = None
    with urllib.request.urlopen(request, timeout=660) as response:
        for chunk in response:
            observed_s: float | None = None
            if first_byte_s is None:
                observed_s = time.monotonic() - started
                first_byte_s = observed_s
            raw.extend(chunk)
            if len(raw) > 8 * 1024 * 1024:
                raise RuntimeError("canary response exceeded private capture bound")
            if chunk.startswith(b"data: ") and chunk.strip() != b"data: [DONE]":
                event = json.loads(chunk[6:])
                usage = event.get("usage")
                if isinstance(usage, dict) and isinstance(usage.get("completion_tokens"), int):
                    completion_tokens = usage["completion_tokens"]
                for choice in event.get("choices", []):
                    value = choice.get("delta", {}).get("content") or ""
                    if value and first_token_s is None:
                        if observed_s is None:
                            observed_s = time.monotonic() - started
                        first_token_s = observed_s
                    content.append(value)
    duration_s = time.monotonic() - started
    answer = "".join(content).strip()
    if b"data: [DONE]" not in raw:
        raise RuntimeError("SSE completion marker missing")
    if answer != "4":
        raise RuntimeError("deterministic quality gate failed")
    if not isinstance(completion_tokens, int) or completion_tokens <= 0:
        raise RuntimeError("streamed completion usage missing")
    if first_byte_s is None or first_token_s is None or duration_s <= first_token_s:
        raise RuntimeError("stream timing did not permit token-throughput measurement")
    decode_s = duration_s - first_token_s
    completion_tokens_per_second = completion_tokens / decode_s
    return bytes(raw), {
        "route": "direct" if direct else "native_router",
        "model": model,
        "firstByteSeconds": first_byte_s,
        "firstTokenSeconds": first_token_s,
        "durationSeconds": duration_s,
        "decodeSeconds": decode_s,
        "completionTokens": completion_tokens,
        "completionTokensPerSecond": completion_tokens_per_second,
        "responseBytes": len(raw),
        "passed": True,
    }


def validate_loading_feedback(raw: bytes, *, expected: bool) -> dict:
    """Require the private SSE capture to match the expected router loading state."""
    reasoning: list[str] = []
    for line in raw.splitlines():
        if not line.startswith(b"data: ") or line == b"data: [DONE]":
            continue
        try:
            event = json.loads(line[6:])
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        for choice in event.get("choices", []):
            delta = choice.get("delta", {}) if isinstance(choice, dict) else {}
            value = delta.get("reasoning_content") if isinstance(delta, dict) else None
            if isinstance(value, str):
                reasoning.append(value)
    combined = "".join(reasoning)
    observed = "freetoken-swap loading model:" in combined
    if observed != expected:
        state = "missing" if expected else "unexpected"
        raise RuntimeError(f"router loading feedback was {state} for this qualification trial")
    return {"expected": expected, "observed": observed, "passed": True}


def concurrent_canaries(base: str, model: str, *, seconds: float = 180) -> tuple[list[tuple[bytes, dict]], dict]:
    """Run two same-profile streams and prove they did not trigger a model swap."""
    _, before = request_json(base + "/router/status")
    prior_activations = before.get("activations")
    if before.get("activeProfile") != model or not isinstance(prior_activations, int):
        raise RuntimeError("same-model concurrency requires an already active profile")
    results: list[tuple[bytes, dict]] = []
    errors: list[BaseException] = []
    lock = threading.Lock()
    gate = threading.Barrier(3)

    def run_one() -> None:
        try:
            gate.wait(timeout=seconds)
            value = canary(base, model, direct=False)
            with lock:
                results.append(value)
        except BaseException as exc:
            with lock:
                errors.append(exc)

    workers = [threading.Thread(target=run_one, name=f"native-router-concurrent-{index}", daemon=True)
               for index in range(2)]
    for worker in workers:
        worker.start()
    gate.wait(timeout=seconds)
    for worker in workers:
        worker.join(seconds)
    if any(worker.is_alive() for worker in workers):
        raise TimeoutError("same-model concurrent streams did not finish")
    if errors:
        raise RuntimeError("same-model concurrent stream failed") from errors[0]
    _, after = request_json(base + "/router/status")
    if (
        len(results) != 2
        or not all(row.get("passed") is True for _, row in results)
        or after.get("activeRequests") != 0
        or after.get("activeProfile") != model
        or after.get("activations") != prior_activations
    ):
        raise RuntimeError("same-model concurrency changed native routing residency")
    return results, {
        "route": "native_router",
        "model": model,
        "requests": 2,
        "activationDelta": 0,
        "activeRequestsAfter": 0,
        "passed": True,
    }


def cancellation_canary(base: str, model: str, *, seconds: float = 90) -> tuple[bytes, dict]:
    """Prove native router cancellation reaches idle without a normal completion credit.

    The raw partial SSE remains a private artifact.  The returned observation is
    deliberately limited to lifecycle counters and timing-safe booleans.
    """
    request_id = "native-qualification-cancel"
    _, before = request_json(base + "/router/status")
    prior_cancellations = before.get("cancellations")
    prior_terminal = before.get("terminalStreams")
    if not isinstance(prior_cancellations, int) or not isinstance(prior_terminal, int):
        raise RuntimeError("router status lacks cancellation counters")
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "Count upward slowly and do not stop."}],
        "temperature": 0,
        "max_tokens": 2048,
        "stream": True,
    }
    request = urllib.request.Request(
        base + "/v1/chat/completions", data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json", "X-FT-Request-ID": request_id,
            **_native_headers(base),
        },
    )
    raw = bytearray()
    first_chunk = threading.Event()
    finished = threading.Event()
    errors: list[BaseException] = []

    def consume() -> None:
        try:
            with urllib.request.urlopen(request, timeout=seconds) as response:
                for chunk in response:
                    raw.extend(chunk)
                    first_chunk.set()
        except Exception as exc:  # cancellation may close a blocking HTTP read
            errors.append(exc)
        finally:
            finished.set()

    worker = threading.Thread(target=consume, name="native-router-cancel", daemon=True)
    started = time.monotonic()
    worker.start()
    if not first_chunk.wait(seconds):
        raise TimeoutError("cancellation stream produced no first chunk")
    _, cancelled = request_json(base + f"/router/requests/{request_id}/cancel", {}, timeout=30)
    if cancelled != {"cancelled": True, "id": request_id}:
        raise RuntimeError("router did not acknowledge the active cancellation request")
    if not finished.wait(seconds):
        raise TimeoutError("cancelled stream did not close")
    deadline = time.monotonic() + seconds
    status: dict | None = None
    while time.monotonic() < deadline:
        status = request_json(base + "/router/status", timeout=3)[1]
        if status.get("activeRequests") == 0:
            break
        time.sleep(0.1)
    if status is None or status.get("activeRequests") != 0:
        raise TimeoutError("router did not return to idle after cancellation")
    if status.get("cancellations") != prior_cancellations + 1:
        raise RuntimeError("router cancellation counter did not increment")
    if status.get("terminalStreams") != prior_terminal:
        raise RuntimeError("cancelled stream was credited as a normal completion")
    if b"data: [DONE]" in raw:
        raise RuntimeError("cancelled stream reached a normal terminal event")
    return bytes(raw), {
        "route": "native_router",
        "model": model,
        "requestId": request_id,
        "durationSeconds": time.monotonic() - started,
        "responseBytes": len(raw),
        "cancellationIncremented": True,
        "normalCompletionCredited": False,
        "streamReadError": repr(errors[0]) if errors else None,
        "passed": True,
    }


def conflicting_request_canary(
    base: str, active_model: str, waiting_model: str, *, seconds: float = 180
) -> tuple[bytes, bytes, bytes, dict]:
    """Hold A, prove B queues, cancel A, then complete B and restore A."""
    request_id = "native-qualification-conflict"
    _, before = request_json(base + "/router/status")
    prior_activations = before.get("activations")
    if before.get("activeProfile") != active_model or not isinstance(prior_activations, int):
        raise RuntimeError("conflicting-request qualification requires active model A")
    body = {
        "model": active_model,
        "messages": [{"role": "user", "content": "Count upward slowly and do not stop."}],
        "temperature": 0, "max_tokens": 2048, "stream": True,
    }
    request = urllib.request.Request(
        base + "/v1/chat/completions", data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json", "X-FT-Request-ID": request_id,
            **_native_headers(base),
        },
    )
    active_raw = bytearray()
    first_chunk = threading.Event()
    active_finished = threading.Event()
    waiting_result: list[tuple[bytes, dict]] = []
    active_errors: list[BaseException] = []
    waiting_errors: list[BaseException] = []

    def consume_active() -> None:
        try:
            with urllib.request.urlopen(request, timeout=seconds) as response:
                for chunk in response:
                    active_raw.extend(chunk)
                    first_chunk.set()
        except Exception as exc:
            active_errors.append(exc)
        finally:
            active_finished.set()

    def consume_waiting() -> None:
        try:
            waiting_result.append(canary(base, waiting_model, direct=False))
        except BaseException as exc:
            waiting_errors.append(exc)

    active_worker = threading.Thread(target=consume_active, daemon=True)
    active_worker.start()
    if not first_chunk.wait(seconds):
        raise TimeoutError("active conflicting stream produced no first chunk")
    waiting_worker = threading.Thread(target=consume_waiting, daemon=True)
    waiting_worker.start()
    deadline = time.monotonic() + seconds
    queued: dict | None = None
    while time.monotonic() < deadline:
        queued = request_json(base + "/router/status", timeout=3)[1]
        if queued.get("queuedRequests") == 1:
            break
        time.sleep(0.1)
    if (
        queued is None or queued.get("queuedRequests") != 1
        or queued.get("activeProfile") != active_model
        or queued.get("activeRequests") != 1
        or queued.get("activeIdentityMatchesEngine") is not True
    ):
        raise RuntimeError("waiting model did not queue behind the active stream")
    if request_json(base + f"/router/requests/{request_id}/cancel", {}, timeout=30)[1] != {
        "cancelled": True, "id": request_id,
    }:
        raise RuntimeError("active conflicting stream cancellation was not acknowledged")
    if not active_finished.wait(seconds):
        raise TimeoutError("active conflicting stream did not close")
    waiting_worker.join(seconds)
    if waiting_worker.is_alive() or waiting_errors or len(waiting_result) != 1:
        raise RuntimeError("waiting model did not complete after active-stream cancellation")
    waiting_raw, waiting_row = waiting_result[0]
    _, after_waiting = request_json(base + "/router/status")
    if (
        waiting_row.get("passed") is not True
        or after_waiting.get("activeProfile") != waiting_model
        or after_waiting.get("activeRequests") != 0
        or after_waiting.get("activations") != prior_activations + 1
    ):
        raise RuntimeError("waiting model did not receive exactly one post-drain activation")
    restored_raw, restored_row = canary(base, active_model, direct=False)
    _, restored = request_json(base + "/router/status")
    if restored_row.get("passed") is not True or restored.get("activations") != prior_activations + 2:
        raise RuntimeError("conflicting-request qualification did not restore model A")
    if b"data: [DONE]" in active_raw:
        raise RuntimeError("active conflicting stream completed normally instead of being cancelled")
    return bytes(active_raw), waiting_raw, restored_raw, {
        "activeProfile": active_model, "waitingProfile": waiting_model,
        "queuedBehindActive": True, "activeIdentityPreservedWhileQueued": True,
        "activationDelta": 2, "restoredProfile": active_model, "passed": True,
    }


def stop_process_group(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    os.killpg(proc.pid, signal.SIGTERM)
    try:
        proc.wait(timeout=45)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=10)


def validate_routed_trial(router: dict, *, alias: str, prior_activations: int, expected_delta: int) -> int:
    """Prove that a labeled routed benchmark actually used its intended state.

    Timings alone cannot distinguish a warm request from an accidental reload.
    The bounded router state makes each performance label auditable without
    retaining a prompt or model path in the public summary.
    """
    activations = router.get("activations")
    if router.get("activeProfile") != alias or router.get("activeRequests") != 0:
        raise RuntimeError("routed trial did not settle on the expected idle profile")
    if not isinstance(activations, int) or activations != prior_activations + expected_delta:
        raise RuntimeError("routed trial activation count did not match its scenario")
    return activations


def control_plane_canary(base: str, artifacts: Path) -> dict:
    """Qualify authenticated management, metrics, and bounded router-log access."""
    unauthorized: dict[str, int] = {}
    for path in ("/router/status", "/v1/models", "/models"):
        request = urllib.request.Request(base + path)
        try:
            with urllib.request.urlopen(request, timeout=10):
                pass
        except urllib.error.HTTPError as exc:
            unauthorized[path] = exc.code
            exc.close()
        else:
            raise RuntimeError(f"unauthenticated request unexpectedly succeeded: {path}")
    if set(unauthorized.values()) != {401}:
        raise RuntimeError("native router did not reject unauthenticated control and inference")

    if _NATIVE_AUTH_BASE != base.rstrip("/") or _NATIVE_API_KEY is None:
        raise RuntimeError("native router credentials are not scoped to the qualification origin")
    basic = base64.b64encode(f"operator:{_NATIVE_API_KEY}".encode()).decode()
    alternate_auth_raw: dict[str, bytes] = {}
    for name, headers in (
        ("basic", {"Authorization": f"Basic {basic}"}),
        ("x-api-key", {"X-Api-Key": _NATIVE_API_KEY}),
    ):
        request = urllib.request.Request(base + "/router/status", headers=headers)
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read()
        status = json.loads(raw)
        if status.get("activeProfile") != "model-a":
            raise RuntimeError(f"{name} authentication did not expose exact model-a residency")
        alternate_auth_raw[name] = raw

    models_raw, models = request_json(base + "/v1/models", timeout=10)
    _, models_alias = request_json(base + "/models", timeout=10)
    _, namespaced_stats = request_json(
        base + "/upstream/compat/model-a/v1/stats", timeout=10
    )
    routed_raw, routed = request_json(base + "/router/models", timeout=10)
    profiles_raw, profiles = request_json(base + "/router/profiles", timeout=10)
    metrics_raw = request_bytes(base + "/metrics", timeout=10)
    model_rows = models.get("data")
    alias_rows = models_alias.get("data")
    routed_rows = routed.get("data")
    profile_rows = profiles.get("data")
    routing_profiles = profiles.get("routingProfiles")
    if not all(
        isinstance(rows, list) and all(isinstance(item, dict) for item in rows)
        for rows in (model_rows, alias_rows, routed_rows, profile_rows)
    ):
        raise RuntimeError("authenticated native control-plane responses have invalid shapes")
    # The pinned alias invokes the same handler independently, so request-time
    # `created` values may differ by one second. Everything else must match.
    normalized_models = [{k: v for k, v in item.items() if k != "created"} for item in model_rows]
    normalized_alias = [{k: v for k, v in item.items() if k != "created"} for item in alias_rows]
    model_envelope = {k: v for k, v in models.items() if k != "data"}
    alias_envelope = {k: v for k, v in models_alias.items() if k != "data"}
    if model_envelope != alias_envelope or normalized_models != normalized_alias:
        raise RuntimeError("/models is not equivalent to the /v1/models compatibility listing")
    aliases = sorted(item["id"] for item in model_rows if isinstance(item.get("id"), str))
    routed_names = sorted(
        item["name"] for item in routed_rows if isinstance(item.get("name"), str)
    )
    profile_names = sorted(
        item["name"] for item in profile_rows if isinstance(item.get("name"), str)
    )
    coding_profile = next(
        (
            item for item in routing_profiles
            if isinstance(item, dict) and item.get("name") == "coding"
        ),
        None,
    ) if isinstance(routing_profiles, list) else None
    resident = [item.get("name") for item in routed_rows if item.get("resident")]
    routed_a = next((item for item in routed_rows if item.get("name") == "model-a"), None)
    if (
        not {"model-a", "model-b", "compat/model-a", "preferred-model"}.issubset(aliases)
        or routed_names != profile_names
        or not {"model-a", "model-b"}.issubset(routed_names)
        or resident != ["model-a"]
        or profiles.get("activeProfile") != "model-a"
        or profiles.get("activeRoutingProfile") is not None
        or not isinstance(routing_profiles, list)
        or not isinstance(coding_profile, dict)
        or coding_profile.get("pins") != {
            "disabled-model": None, "profile-model": "preferred-model",
        }
        or not isinstance(routed_a, dict)
        or routed_a.get("checkEndpoint") != "/ready"
        or not isinstance(namespaced_stats, dict)
        or b"freetoken_swap_admissions_total" not in metrics_raw
    ):
        raise RuntimeError("authenticated native control-plane responses are inconsistent")

    log_request = urllib.request.Request(
        base + "/router/logs?since=0", headers=_native_headers(base)
    )
    log_frame = bytearray()
    with urllib.request.urlopen(log_request, timeout=10) as response:
        if response.headers.get_content_type() != "text/event-stream":
            raise RuntimeError("router log endpoint did not return SSE")
        while len(log_frame) <= 64 * 1024:
            line = response.readline()
            if not line:
                break
            log_frame.extend(line)
            if b"management_loaded" in log_frame:
                break
    if len(log_frame) > 64 * 1024 or b"management_loaded" not in log_frame:
        raise RuntimeError("router log stream lacked the bounded management event")

    (artifacts / "control-v1-models.json").write_bytes(models_raw)
    (artifacts / "control-router-models.json").write_bytes(routed_raw)
    (artifacts / "control-router-profiles.json").write_bytes(profiles_raw)
    (artifacts / "control-metrics.prom").write_bytes(metrics_raw)
    (artifacts / "control-router-log.sse").write_bytes(log_frame)
    for name, raw in alternate_auth_raw.items():
        (artifacts / f"control-auth-{name}.json").write_bytes(raw)
    return {
        "unauthenticatedControlRejected": True,
        "unauthenticatedInferenceRejected": True,
        "aliasCount": len(aliases),
        "selectorListed": "preferred-model" in aliases,
        "profileCount": len(profile_names),
        "routingProfileListed": True,
        "configuredReadinessTargetVerified": True,
        "residentProfile": "model-a",
        "modelListAliasVerified": True,
        "namespacedUpstreamVerified": True,
        "apiKeyFormsVerified": ["bearer", "basic", "x-api-key"],
        "metricsAvailable": True,
        "routerLogSseAvailable": True,
        "passed": True,
    }


def selector_canary(base: str, artifacts: Path) -> dict:
    """Prove a warm virtual ID reuses the resident target without a swap."""
    _, before = request_json(base + "/router/status")
    prior_activations = before.get("activations")
    if before.get("activeProfile") != "model-a" or not isinstance(prior_activations, int):
        raise RuntimeError("warm selector canary requires resident model-a")
    raw, completion = canary(base, "preferred-model", direct=False)
    _, after = request_json(base + "/router/status")
    if (
        completion.get("passed") is not True
        or after.get("activeProfile") != "model-a"
        or after.get("activeRequests") != 0
        or after.get("activations") != prior_activations
    ):
        raise RuntimeError("warm selector did not reuse the resident target")
    (artifacts / "warm-selector.sse").write_bytes(raw)
    return {
        "strategy": "warm",
        "resolvedProfile": "model-a",
        "activationDelta": 0,
        "passed": True,
    }


def routing_profile_canary(base: str, artifacts: Path) -> dict:
    """Prove an active profile pin composes through a warm selector, then clear it."""
    _, before = request_json(base + "/router/status")
    prior_activations = before.get("activations")
    if before.get("activeProfile") != "model-a" or not isinstance(prior_activations, int):
        raise RuntimeError("routing profile canary requires resident model-a")
    raw = b""
    listed_raw = b""
    try:
        _, activated = request_json(
            base + "/router/profiles/active", {"name": "coding"}, method="PUT"
        )
        if activated != {"active": "coding"}:
            raise RuntimeError("routing profile activation was not acknowledged")
        listed_raw, listed = request_json(base + "/v1/models", timeout=10)
        listed_ids = {
            item.get("id") for item in listed.get("data", []) if isinstance(item, dict)
        }
        if "profile-model" not in listed_ids or "disabled-model" in listed_ids:
            raise RuntimeError("active routing profile model listing is inconsistent")
        raw, completion = canary(base, "profile-model", direct=False)
        _, after = request_json(base + "/router/status")
        if (
            completion.get("passed") is not True
            or after.get("activeRoutingProfile") != "coding"
            or after.get("activeProfile") != "model-a"
            or after.get("activeRequests") != 0
            or after.get("activations") != prior_activations
        ):
            raise RuntimeError("routing profile pin did not reuse the resident selector target")
    finally:
        _, cleared = request_json(
            base + "/router/profiles/active", {"name": None}, method="PUT"
        )
        if cleared != {"active": None}:
            raise RuntimeError("routing profile was not cleared after its canary")
    (artifacts / "routing-profile.sse").write_bytes(raw)
    (artifacts / "routing-profile-models.json").write_bytes(listed_raw)
    return {
        "profileActivated": True,
        "profileCleared": True,
        "selectorComposed": True,
        "resolvedProfile": "model-a",
        "activationDelta": 0,
        "passed": True,
    }


def capture_hardware(base: str, artifacts: Path, label: str) -> dict:
    """Keep per-trial process and memory observations in the private artifact set."""
    raw, hardware = request_json(base + "/router/hardware")
    engine = hardware.get("engine")
    memory = hardware.get("memory")
    if not isinstance(engine, dict) or not isinstance(memory, dict):
        raise RuntimeError("router hardware observation has an invalid shape")
    if (
        not engine.get("running")
        or not isinstance(engine.get("pid"), int)
        or engine["pid"] <= 0
        or not isinstance(engine.get("port"), int)
        or not 1 <= engine["port"] <= 65535
    ):
        raise RuntimeError("router hardware observation does not identify a running engine")
    if not all(isinstance(memory.get(key), int) for key in ("ramBytes", "vramBytes")):
        raise RuntimeError("router hardware observation lacks byte measurements")
    if memory.get("ramAvailable") is not True or memory.get("vramAvailable") is not True:
        raise RuntimeError("router hardware observation contains unavailable memory measurements")
    if memory["ramBytes"] <= 0 or memory["vramBytes"] <= 0:
        raise RuntimeError("router hardware observation contains non-positive memory measurements")
    if not all(isinstance(memory.get(key), str) and memory[key] for key in ("ramSource", "vramSource")):
        raise RuntimeError("router hardware observation lacks memory measurement sources")
    (artifacts / f"{label}.hardware.json").write_bytes(raw)
    return hardware


def validate_re_adoption(before: dict, after: dict, router: dict) -> dict:
    """Validate that a replacement daemon bound, rather than replaced, one engine."""
    old_pid, old_port = before.get("pid"), before.get("port")
    if (
        not before.get("running")
        or not isinstance(old_pid, int) or old_pid <= 0
        or not isinstance(old_port, int) or not 1 <= old_port <= 65535
    ):
        raise RuntimeError("pre-restart engine identity is invalid")
    if (
        after.get("pid") != old_pid
        or after.get("port") != old_port
        or after.get("adopted") is not True
        or router.get("activeProfile") != "model-a"
        or router.get("activeIdentityMatchesEngine") is not True
        or router.get("activations") != 0
    ):
        raise RuntimeError("replacement daemon did not bind the exact adopted residency")
    return {
        "profile": "model-a", "samePid": True, "samePort": True,
        "managerAdopted": True, "activationDelta": 0,
    }


def require_listener_closed(port: int) -> None:
    """Fail the qualification if a temporary engine listener survived cleanup."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(1)
        if connection.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError("temporary engine listener remains reachable after cleanup")


def require_listener_open(port: int) -> None:
    """Require a detached test-owned engine to remain reachable for re-adoption."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(1)
        if connection.connect_ex(("127.0.0.1", port)) != 0:
            raise RuntimeError("detached engine listener did not survive daemon restart")


def stop_detached_engine(pid: int, port: int) -> None:
    """Best-effort cleanup for the exact test-owned engine during a restart gap."""
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            require_listener_closed(port)
            return
        except RuntimeError:
            time.sleep(0.1)
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            require_listener_closed(port)
            return
        except RuntimeError:
            time.sleep(0.1)
    raise RuntimeError("detached test-owned engine survived cleanup")


def reload_conflict_canary(
    base: str, catalog_path: Path, model_a: str, model_b: str, *, api_key: str | None = None
) -> dict:
    """Prove an active profile's scheduler policy cannot change under its engine."""
    catalog_path.write_text(
        native_catalog_text(model_a, model_b, model_a_priority=1, api_key=api_key),
        encoding="utf-8",
    )
    try:
        request_json(base + "/router/reload", {}, timeout=30)
    except urllib.error.HTTPError as exc:
        if exc.code != 409:
            raise RuntimeError("active catalog conflict returned the wrong status") from exc
    else:
        raise RuntimeError("active catalog scheduler redefinition was accepted")
    _, status = request_json(base + "/router/status", timeout=30)
    if status.get("activeProfile") != "model-a" or status.get("activeIdentityMatchesEngine") is not True:
        raise RuntimeError("rejected catalog replacement changed active engine identity")
    return {
        "activeProfile": "model-a",
        "rejectedStatus": 409,
        "activeIdentityPreserved": True,
        "passed": True,
    }


def failed_switch_canary(base: str, model: str, restored_model: str) -> tuple[bytes, bytes, dict]:
    """Require a failed disposable load to restore the prior resident engine."""
    _, before = request_json(base + "/router/status")
    _, pending_before = request_json(base + "/accounting/pending")
    receipts_before = pending_before.get("receipts")
    if not isinstance(receipts_before, list):
        raise RuntimeError("accounting outbox response has an invalid shape")
    before_ids = {
        receipt.get("receiptId") for receipt in receipts_before
        if isinstance(receipt, dict) and isinstance(receipt.get("receiptId"), str)
    }
    prior_failures = before.get("activationFailures")
    if (
        before.get("activeProfile") != restored_model
        or before.get("activeIdentityMatchesEngine") is not True
        or not isinstance(prior_failures, int)
    ):
        raise RuntimeError("failed-switch qualification requires an exact healthy resident")
    failure_raw = b""
    try:
        request_json(base + "/router/load", {"name": model}, timeout=90)
    except urllib.error.HTTPError as exc:
        failure_raw = exc.read(1024 * 1024 + 1)
        if exc.code != 503 or len(failure_raw) > 1024 * 1024:
            raise RuntimeError("failed replacement returned an invalid bounded response") from exc
    else:
        raise RuntimeError("disposable invalid model unexpectedly activated")
    try:
        failure = json.loads(failure_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("failed replacement response was not JSON") from exc
    error = failure.get("error") if isinstance(failure, dict) else None
    recovery = failure.get("recovery") if isinstance(failure, dict) else None
    if not isinstance(error, dict) or error.get("type") not in {"engine_not_ready", "switch_launch_failed"}:
        raise RuntimeError("failed replacement did not report a lifecycle failure")
    if not isinstance(recovery, dict) or recovery.get("launched") is not True:
        raise RuntimeError("failed replacement did not report successful rollback launch")
    _, after = request_json(base + "/router/status", timeout=30)
    if (
        after.get("activeProfile") != restored_model
        or after.get("activeIdentityMatchesEngine") is not True
        or after.get("activeRequests") != 0
        or after.get("activationFailures") != prior_failures + 1
    ):
        raise RuntimeError("failed replacement did not restore exact idle residency")
    _, pending_after = request_json(base + "/accounting/pending")
    receipts_after = pending_after.get("receipts")
    if not isinstance(receipts_after, list):
        raise RuntimeError("post-failure accounting outbox response has an invalid shape")
    after_ids = {
        receipt.get("receiptId") for receipt in receipts_after
        if isinstance(receipt, dict) and isinstance(receipt.get("receiptId"), str)
    }
    new_receipts = after_ids - before_ids
    if not new_receipts:
        raise RuntimeError("failed switch produced no new durable accounting receipt")
    restored_raw, restored = canary(base, restored_model, direct=False)
    return failure_raw, restored_raw, {
        "failedProfile": model,
        "restoredProfile": restored_model,
        "failureType": error["type"],
        "rollbackLaunched": True,
        "activationFailureIncremented": True,
        "newAccountingReceiptCount": len(new_receipts),
        "restoredCompletionPassed": restored.get("passed") is True,
        "passed": restored.get("passed") is True,
    }


def persistent_capacity_canary(
    base: str, catalog_path: Path, model_a: str, model_b: str, *, api_key: str | None = None
) -> tuple[bytes, dict]:
    """Prove a singleton persistent group reserves the sole resident slot."""
    if request_json(base + "/router/unload", {}, timeout=45)[1].get("unloaded") is not True:
        raise RuntimeError("could not unload before persistent capacity qualification")
    catalog_path.write_text(
        native_catalog_text(model_a, model_b, persistent_a=True, api_key=api_key),
        encoding="utf-8",
    )
    if request_json(base + "/router/reload", {}, timeout=30)[1].get("reloaded") is not True:
        raise RuntimeError("persistent catalog reload was not acknowledged")
    _, loaded_a = request_json(base + "/router/load", {"name": "model-a"}, timeout=660)
    router_a, pid_a = loaded_a.get("router"), loaded_a.get("pid")
    if (
        loaded_a.get("profile") != "model-a" or not isinstance(pid_a, int) or pid_a <= 0
        or not isinstance(router_a, dict) or router_a.get("persistent") is not True
        or router_a.get("activeIdentityMatchesEngine") is not True
    ):
        raise RuntimeError("model-a did not occupy the persistent resident slot")
    rejection_raw = b""
    try:
        request_json(base + "/router/load", {"name": "model-b"}, timeout=30)
    except urllib.error.HTTPError as exc:
        rejection_raw = exc.read(1024 * 1024 + 1)
        if exc.code != 409 or len(rejection_raw) > 1024 * 1024:
            raise RuntimeError("persistent capacity conflict returned an invalid response") from exc
    else:
        raise RuntimeError("persistent resident allowed a conflicting activation")
    try:
        rejection = json.loads(rejection_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("persistent capacity response was not JSON") from exc
    if rejection.get("error", {}).get("type") != "capacity_unavailable":
        raise RuntimeError("persistent capacity conflict returned the wrong error type")
    _, still_a = request_json(base + "/router/status")
    if (
        still_a.get("activeProfile") != "model-a"
        or still_a.get("activeIdentityMatchesEngine") is not True
        or still_a.get("persistent") is not True
        or request_json(base + "/engine/status")[1].get("pid") != pid_a
    ):
        raise RuntimeError("persistent capacity rejection disturbed the resident engine")
    if request_json(base + "/router/unload", {"name": "model-a"}, timeout=45)[1].get("unloaded") is not True:
        raise RuntimeError("explicit persistent unload failed")
    _, loaded_b = request_json(base + "/router/load", {"name": "model-b"}, timeout=660)
    if loaded_b.get("profile") != "model-b" or loaded_b.get("router", {}).get("activeIdentityMatchesEngine") is not True:
        raise RuntimeError("released persistent capacity did not admit model-b")
    return rejection_raw, {
        "persistentProfile": "model-a", "conflictingProfile": "model-b",
        "rejectedStatus": 409, "residentPidPreserved": True,
        "explicitUnloadReleasedCapacity": True, "passed": True,
    }


def ttl_eviction_canary(
    base: str, catalog_path: Path, model_a: str, model_b: str, *, seconds: float = 45,
    api_key: str | None = None,
) -> dict:
    """Exercise idle-TTL ownership cleanup against the temporary catalog only."""
    _, before = request_json(base + "/router/status")
    prior_evictions = before.get("evictions")
    if not isinstance(prior_evictions, int):
        raise RuntimeError("router status lacks eviction counter")
    _, unloaded = request_json(base + "/router/unload", {}, timeout=45)
    if unloaded.get("unloaded") is not True:
        raise RuntimeError("could not unload the prior resident before TTL qualification")
    catalog_path.write_text(
        native_catalog_text(model_a, model_b, ttl_s=2, api_key=api_key), encoding="utf-8"
    )
    _, reloaded = request_json(base + "/router/reload", {}, timeout=30)
    if reloaded.get("reloaded") is not True:
        raise RuntimeError("temporary TTL catalog reload was not acknowledged")
    _, loaded = request_json(base + "/router/load", {"name": "model-a"}, timeout=660)
    port = loaded.get("port")
    if loaded.get("profile") != "model-a" or not isinstance(port, int) or not 1 <= port <= 65535:
        raise RuntimeError("TTL qualification did not activate a concrete model-a engine")
    deadline = time.monotonic() + seconds
    status: dict | None = None
    while time.monotonic() < deadline:
        status = request_json(base + "/router/status", timeout=3)[1]
        if status.get("activeProfile") is None and status.get("evictions") == prior_evictions + 1:
            break
        time.sleep(0.1)
    if status is None or status.get("activeProfile") is not None or status.get("evictions") != prior_evictions + 1:
        raise TimeoutError("idle TTL did not evict the temporary resident engine")
    require_listener_closed(port)
    return {
        "profile": "model-a",
        "ttlSeconds": 2,
        "port": port,
        "evictionIncremented": True,
        "listenerClosed": True,
        "passed": True,
    }


def native_catalog_text(
    model_a: str, model_b: str, *, ttl_s: int = 0, model_a_priority: int = 0,
    invalid_model: str | None = None, persistent_a: bool = False,
    api_key: str | None = None,
) -> str:
    """Return the allowlisted, dynamic-port catalog used by the private run."""
    common_args = [
        "--host", "127.0.0.1", "--served-model-name", "${MODEL_ID}",
        "--max-seq-len-override", "4096", "--num-tokens", "4096", "--max-prefill-length", "512",
        "--max-running-requests", "1", "--graph", "1", "--memory-ratio", "0.75",
        "--attention-backend", "triton", "--moe-backend", "fused", "--disable-pynccl",
    ]
    catalog = [
        "[router]", "upstream_timeout_s = 660", "include_aliases_in_list = true",
        "send_loading_state = true", "",
    ]
    if api_key is not None:
        catalog[2:2] = [f"api_keys = [{json.dumps(api_key)}]"]
    catalog.extend((
        "[selectors.preferred-model]", 'strategy = "warm"',
        'targets = ["model-b", "model-a"]', 'name = "Preferred local model"',
        'description = "Reuses a ready target before the ordered cold fallback"', "",
        "[profiles.coding]", 'description = "Qualification routing profile"',
        "[profiles.coding.pins]", 'profile-model = "preferred-model"',
        'disabled-model = ""', "",
    ))
    if persistent_a:
        catalog.extend((
            "[router.groups.resident]", 'members = ["model-a"]', "swap = false",
            "exclusive = true", "persistent = true", "",
        ))
    for alias, model in (("model-a", model_a), ("model-b", model_b)):
        profile_lines = [
            f"[models.{alias}]", f"model = {json.dumps(model)}", "port = 0", "ready_timeout_s = 600",
            'check_endpoint = "/ready"', 'proxy = "http://127.0.0.1:${PORT}"',
            f"ttl_s = {ttl_s}", f"priority = {model_a_priority if alias == 'model-a' else 0}",
        ]
        if persistent_a and alias == "model-a":
            profile_lines.append('group = "resident"')
        if alias == "model-a":
            profile_lines.append('aliases = ["compat/model-a"]')
        profile_lines.extend((
            "args = " + json.dumps(common_args).replace("${MODEL_ID}", alias), ""
        ))
        catalog.extend(profile_lines)
    if invalid_model is not None:
        catalog.extend((
            "[models.model-invalid]", f"model = {json.dumps(invalid_model)}", "port = 0",
            "ready_timeout_s = 15", 'check_endpoint = "/ready"',
            'proxy = "http://127.0.0.1:${PORT}"', "ttl_s = 0",
            "args = " + json.dumps(common_args).replace("${MODEL_ID}", "model-invalid"), "",
        ))
    return "\n".join(catalog)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "source", "python", "model-a", "model-b", "artifacts", "protected-service", "protected-url",
        "expected-hostname",
    ):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--allow-maintenance", action="store_true", required=True)
    parser.add_argument("--daemon-port", type=int, default=1964)
    args = parser.parse_args()
    if not sys.platform.startswith("linux"):
        raise SystemExit("native maintenance qualification requires Linux process-group semantics")
    require_expected_hostname(args.expected_hostname)

    artifacts = Path(args.artifacts)
    artifacts.mkdir(parents=True, exist_ok=False)
    result: dict = {"trials": [], "restored": False}

    def save() -> None:
        (artifacts / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    service = ["sudo", "-n", "systemctl"]
    subprocess.run(service + ["is-active", "--quiet", args.protected_service], check=True)
    baseline_raw, baseline = request_json(args.protected_url + "/health", timeout=10)
    (artifacts / "protected-baseline-health.json").write_bytes(baseline_raw)
    if baseline.get("status") != "ok":
        raise RuntimeError("protected service health baseline failed; no maintenance performed")
    _, listing = request_json(args.protected_url + "/v1/models", timeout=10)
    protected_model = listing["data"][0]["id"]
    protected_raw, _ = canary(args.protected_url, protected_model, direct=True)
    (artifacts / "protected-baseline-response.sse").write_bytes(protected_raw)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(args.source) / "python")
    env["TORCH_EXTENSIONS_DIR"] = str(artifacts / "torch-extensions")
    env["MAX_JOBS"] = "2"
    catalog_path = artifacts / "models.toml"
    invalid_model = str(artifacts / "intentionally-missing-model.gguf")
    native_api_key = secrets.token_urlsafe(32)
    catalog_path.write_text(
        native_catalog_text(
            args.model_a, args.model_b, invalid_model=invalid_model, api_key=native_api_key
        ),
        encoding="utf-8",
    )
    with (artifacts / "kernel-preflight.log").open("wb") as log:
        subprocess.run(
            [args.python, "-c", "from freetoken.kernel.gguf import _module; _module(); print('NATIVE_KERNEL_READY')"],
            cwd=args.source, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600,
        )

    daemon: subprocess.Popen[bytes] | None = None
    detached_engine: tuple[int, int] | None = None
    maintenance = False
    final_engine_port: int | None = None
    base = f"http://127.0.0.1:{args.daemon_port}"
    configure_native_auth(base, native_api_key)

    def launch_daemon(log, *, stop_serve_on_exit: bool) -> subprocess.Popen[bytes]:
        command = [
            args.python, "-m", "freetoken.cli", "daemon", "--host", "127.0.0.1",
            "--port", str(args.daemon_port), "--state-dir", str(artifacts / "daemon-state"),
            "--catalog", str(catalog_path), "--catalog-watch-interval", "0", "--no-oom",
        ]
        if stop_serve_on_exit:
            command.append("--stop-serve-on-exit")
        return subprocess.Popen(
            command, cwd=args.source, env=env, stdout=log, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, start_new_session=True,
        )

    try:
        with (artifacts / "daemon.log").open("wb") as log:
            daemon = launch_daemon(log, stop_serve_on_exit=False)
            wait_json(base + "/router/status", seconds=30)
            maintenance = True
            subprocess.run(service + ["stop", args.protected_service], check=True, timeout=90)

            # Direct is intentionally measured against the native engine port after a router-owned load.
            loaded_raw, loaded = request_json(base + "/router/load", {"name": "model-a"}, timeout=660)
            if loaded.get("profile") != "model-a" or not isinstance(loaded.get("port"), int):
                raise RuntimeError("native management load did not return a concrete model-a target")
            activation_count = validate_routed_trial(
                loaded["router"], alias="model-a", prior_activations=0, expected_delta=1
            )
            result["controlPlane"] = control_plane_canary(base, artifacts)
            result["selector"] = selector_canary(base, artifacts)
            result["routingProfile"] = routing_profile_canary(base, artifacts)
            direct_raw, direct_row = canary(f"http://127.0.0.1:{loaded['port']}", "model-a", direct=True)
            (artifacts / "direct-a.sse").write_bytes(direct_raw)
            (artifacts / "direct-a.load.json").write_bytes(loaded_raw)
            direct_row["router"] = loaded["router"]
            direct_row["expectedActivationDelta"] = 1
            direct_row["hardware"] = capture_hardware(base, artifacts, "direct-a")
            final_engine_port = direct_row["hardware"]["engine"]["port"]
            result["trials"].append(direct_row)

            cancel_raw, cancellation = cancellation_canary(base, "model-a")
            (artifacts / "cancel-a.partial.sse").write_bytes(cancel_raw)
            result["cancellation"] = cancellation

            concurrent_rows, concurrency = concurrent_canaries(base, "model-a")
            for index, (concurrent_raw, _) in enumerate(concurrent_rows):
                (artifacts / f"concurrent-a-{index}.sse").write_bytes(concurrent_raw)
            result["concurrency"] = concurrency
            save()

            for label, alias, expected_delta in (
                ("warm-a", "model-a", 0),
                ("cold-b", "model-b", 1),
                ("alternating-a", "model-a", 1),
            ):
                raw, row = canary(base, alias, direct=False)
                row["scenario"] = label
                row["loadingFeedback"] = validate_loading_feedback(
                    raw, expected=expected_delta == 1
                )
                row["router"] = request_json(base + "/router/status")[1]
                activation_count = validate_routed_trial(
                    row["router"], alias=alias, prior_activations=activation_count,
                    expected_delta=expected_delta,
                )
                row["expectedActivationDelta"] = expected_delta
                (artifacts / f"{label}.sse").write_bytes(raw)
                (artifacts / f"{label}.metrics").write_bytes(request_bytes(base + "/metrics"))
                row["hardware"] = capture_hardware(base, artifacts, label)
                final_engine_port = row["hardware"]["engine"]["port"]
                result["trials"].append(row)
                save()
            failure_raw, restored_raw, failed_switch = failed_switch_canary(
                base, "model-invalid", "model-a"
            )
            (artifacts / "failed-switch-response.json").write_bytes(failure_raw)
            (artifacts / "failed-switch-restored-a.sse").write_bytes(restored_raw)
            result["failedSwitch"] = failed_switch

            before_restart_raw, before_restart = request_json(base + "/engine/status")
            old_pid, old_port = before_restart.get("pid"), before_restart.get("port")
            if (
                not before_restart.get("running")
                or not isinstance(old_pid, int) or old_pid <= 0
                or not isinstance(old_port, int) or not 1 <= old_port <= 65535
            ):
                raise RuntimeError("pre-restart engine identity is invalid")
            (artifacts / "re-adoption-before-engine.json").write_bytes(before_restart_raw)
            detached_engine = (old_pid, old_port)
            stop_process_group(daemon)
            daemon = None
            require_listener_open(old_port)
            daemon = launch_daemon(log, stop_serve_on_exit=True)
            adopted_router = wait_json(base + "/router/status", seconds=30)
            adopted_raw, adopted_engine = request_json(base + "/engine/status")
            (artifacts / "re-adoption-after-engine.json").write_bytes(adopted_raw)
            identity = validate_re_adoption(before_restart, adopted_engine, adopted_router)
            readopted_raw, readopted_completion = canary(base, "model-a", direct=False)
            (artifacts / "re-adoption-restored-a.sse").write_bytes(readopted_raw)
            if request_json(base + "/router/status")[1].get("activations") != 0:
                raise RuntimeError("routed request replaced the re-adopted engine")
            result["reAdoption"] = {
                **identity,
                "completionPassed": readopted_completion.get("passed") is True,
                "passed": readopted_completion.get("passed") is True,
            }
            detached_engine = None
            conflict_a_raw, conflict_b_raw, conflict_restored_raw, conflict = conflicting_request_canary(
                base, "model-a", "model-b"
            )
            (artifacts / "conflict-active-a.partial.sse").write_bytes(conflict_a_raw)
            (artifacts / "conflict-waiting-b.sse").write_bytes(conflict_b_raw)
            (artifacts / "conflict-restored-a.sse").write_bytes(conflict_restored_raw)
            result["conflictingRequest"] = conflict
            result["reloadConflict"] = reload_conflict_canary(
                base, catalog_path, args.model_a, args.model_b, api_key=native_api_key
            )
            persistent_raw, persistent = persistent_capacity_canary(
                base, catalog_path, args.model_a, args.model_b, api_key=native_api_key
            )
            (artifacts / "persistent-capacity-rejection.json").write_bytes(persistent_raw)
            result["persistentCapacity"] = persistent
            result["ttl"] = ttl_eviction_canary(
                base, catalog_path, args.model_a, args.model_b, api_key=native_api_key
            )
            final_engine_port = result["ttl"]["port"]
            save()
            result["passed"] = (
                len(result["trials"]) == 4
                and all(x["passed"] for x in result["trials"])
                and result.get("cancellation", {}).get("passed") is True
                and result.get("concurrency", {}).get("passed") is True
                and result.get("ttl", {}).get("passed") is True
                and result.get("reloadConflict", {}).get("passed") is True
                and result.get("failedSwitch", {}).get("passed") is True
                and result.get("reAdoption", {}).get("passed") is True
                and result.get("persistentCapacity", {}).get("passed") is True
                and result.get("conflictingRequest", {}).get("passed") is True
                and result.get("controlPlane", {}).get("passed") is True
                and result.get("selector", {}).get("passed") is True
                and result.get("routingProfile", {}).get("passed") is True
            )
    except BaseException as exc:
        result["error"] = repr(exc)
    finally:
        if daemon is not None:
            try:
                request_json(base + "/shutdown", {}, timeout=45)
            except (OSError, ValueError, urllib.error.HTTPError):
                pass
            try:
                stop_process_group(daemon)
                if daemon.poll() is None:
                    raise RuntimeError("temporary daemon process did not exit")
                if final_engine_port is not None:
                    require_listener_closed(final_engine_port)
            except (OSError, subprocess.TimeoutExpired) as exc:
                result["cleanupError"] = repr(exc)
            except RuntimeError as exc:
                if detached_engine is None:
                    result["cleanupError"] = repr(exc)
                else:
                    try:
                        stop_detached_engine(*detached_engine)
                        detached_engine = None
                    except (OSError, RuntimeError) as detached_exc:
                        result["cleanupError"] = repr(detached_exc)
        elif detached_engine is not None:
            try:
                stop_detached_engine(*detached_engine)
            except (OSError, RuntimeError) as exc:
                result["cleanupError"] = repr(exc)
        if maintenance:
            try:
                subprocess.run(service + ["start", args.protected_service], check=True, timeout=180)
                wait_json(args.protected_url + "/health", seconds=300)
                restored_raw, _ = canary(args.protected_url, protected_model, direct=True)
                (artifacts / "protected-restored-response.sse").write_bytes(restored_raw)
                result["restored"] = True
            except BaseException as exc:
                result["restoreError"] = repr(exc)
        save()
    return 0 if result.get("passed") and result["restored"] and "cleanupError" not in result else 1


if __name__ == "__main__":
    raise SystemExit(main())
