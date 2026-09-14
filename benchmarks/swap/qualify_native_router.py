"""Opt-in native freetoken-swap routing benchmark for an approved Linux window.

It keeps raw requests, responses, daemon logs, catalog paths, and host details
inside a newly created private artifact directory.  It never changes protected
service enablement or configuration, and always attempts restoration after a
maintenance stop.  This is evidence collection, not a production launcher.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request


def request_json(url: str, body: dict | None = None, *, timeout: float = 30) -> tuple[bytes, dict]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return raw, json.loads(raw)


def request_bytes(url: str, *, timeout: float = 30) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
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
        headers={"Content-Type": "application/json"},
    )
    raw = bytearray()
    content: list[str] = []
    started = time.monotonic()
    first_byte_s: float | None = None
    completion_tokens: int | None = None
    with urllib.request.urlopen(request, timeout=660) as response:
        for chunk in response:
            if first_byte_s is None:
                first_byte_s = time.monotonic() - started
            raw.extend(chunk)
            if len(raw) > 8 * 1024 * 1024:
                raise RuntimeError("canary response exceeded private capture bound")
            if chunk.startswith(b"data: ") and chunk.strip() != b"data: [DONE]":
                event = json.loads(chunk[6:])
                usage = event.get("usage")
                if isinstance(usage, dict) and isinstance(usage.get("completion_tokens"), int):
                    completion_tokens = usage["completion_tokens"]
                for choice in event.get("choices", []):
                    content.append(choice.get("delta", {}).get("content") or "")
    duration_s = time.monotonic() - started
    answer = "".join(content).strip()
    if b"data: [DONE]" not in raw:
        raise RuntimeError("SSE completion marker missing")
    if answer != "4":
        raise RuntimeError("deterministic quality gate failed")
    if not isinstance(completion_tokens, int) or completion_tokens <= 0:
        raise RuntimeError("streamed completion usage missing")
    if first_byte_s is None or duration_s <= first_byte_s:
        raise RuntimeError("stream timing did not permit token-throughput measurement")
    decode_s = duration_s - first_byte_s
    completion_tokens_per_second = completion_tokens / decode_s
    return bytes(raw), {
        "route": "direct" if direct else "native_router",
        "model": model,
        "firstByteSeconds": first_byte_s,
        "durationSeconds": duration_s,
        "decodeSeconds": decode_s,
        "completionTokens": completion_tokens,
        "completionTokensPerSecond": completion_tokens_per_second,
        "responseBytes": len(raw),
        "passed": True,
    }


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
        headers={"Content-Type": "application/json", "X-FT-Request-ID": request_id},
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
    (artifacts / f"{label}.hardware.json").write_bytes(raw)
    return hardware


def require_listener_closed(port: int) -> None:
    """Fail the qualification if a temporary engine listener survived cleanup."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(1)
        if connection.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError("temporary engine listener remains reachable after cleanup")


def reload_conflict_canary(base: str, catalog_path: Path, model_a: str, model_b: str) -> dict:
    """Prove an active profile's scheduler policy cannot change under its engine."""
    catalog_path.write_text(native_catalog_text(model_a, model_b, model_a_priority=1), encoding="utf-8")
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


def ttl_eviction_canary(
    base: str, catalog_path: Path, model_a: str, model_b: str, *, seconds: float = 45
) -> dict:
    """Exercise idle-TTL ownership cleanup against the temporary catalog only."""
    _, before = request_json(base + "/router/status")
    prior_evictions = before.get("evictions")
    if not isinstance(prior_evictions, int):
        raise RuntimeError("router status lacks eviction counter")
    _, unloaded = request_json(base + "/router/unload", {}, timeout=45)
    if unloaded.get("unloaded") is not True:
        raise RuntimeError("could not unload the prior resident before TTL qualification")
    catalog_path.write_text(native_catalog_text(model_a, model_b, ttl_s=2), encoding="utf-8")
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
    invalid_model: str | None = None,
) -> str:
    """Return the allowlisted, dynamic-port catalog used by the private run."""
    common_args = [
        "--host", "127.0.0.1", "--served-model-name", "${MODEL_ID}",
        "--max-seq-len-override", "4096", "--num-tokens", "4096", "--max-prefill-length", "512",
        "--max-running-requests", "1", "--graph", "1", "--memory-ratio", "0.75",
        "--attention-backend", "triton", "--moe-backend", "fused", "--disable-pynccl",
    ]
    catalog = ["[router]", "upstream_timeout_s = 660", ""]
    for alias, model in (("model-a", model_a), ("model-b", model_b)):
        catalog.extend((
            f"[models.{alias}]", f"model = {json.dumps(model)}", "port = 0", "ready_timeout_s = 600",
            f"ttl_s = {ttl_s}", f"priority = {model_a_priority if alias == 'model-a' else 0}",
            "args = " + json.dumps(common_args).replace("${MODEL_ID}", alias), "",
        ))
    if invalid_model is not None:
        catalog.extend((
            "[models.model-invalid]", f"model = {json.dumps(invalid_model)}", "port = 0",
            "ready_timeout_s = 15", "ttl_s = 0",
            "args = " + json.dumps(common_args).replace("${MODEL_ID}", "model-invalid"), "",
        ))
    return "\n".join(catalog)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "source", "python", "model-a", "model-b", "artifacts", "protected-service", "protected-url",
    ):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--allow-maintenance", action="store_true", required=True)
    parser.add_argument("--daemon-port", type=int, default=1964)
    args = parser.parse_args()
    if not sys.platform.startswith("linux"):
        raise SystemExit("native maintenance qualification requires Linux process-group semantics")

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
    catalog_path.write_text(
        native_catalog_text(args.model_a, args.model_b, invalid_model=invalid_model), encoding="utf-8"
    )
    with (artifacts / "kernel-preflight.log").open("wb") as log:
        subprocess.run(
            [args.python, "-c", "from freetoken.kernel.gguf import _module; _module(); print('NATIVE_KERNEL_READY')"],
            cwd=args.source, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600,
        )

    daemon: subprocess.Popen[bytes] | None = None
    maintenance = False
    final_engine_port: int | None = None
    base = f"http://127.0.0.1:{args.daemon_port}"
    try:
        with (artifacts / "daemon.log").open("wb") as log:
            daemon = subprocess.Popen(
                [args.python, "-m", "freetoken.cli", "daemon", "--host", "127.0.0.1",
                 "--port", str(args.daemon_port), "--state-dir", str(artifacts / "daemon-state"),
                 "--catalog", str(catalog_path), "--catalog-watch-interval", "0", "--no-oom",
                 "--stop-serve-on-exit"],
                cwd=args.source, env=env, stdout=log, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, start_new_session=True,
            )
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
            result["reloadConflict"] = reload_conflict_canary(base, catalog_path, args.model_a, args.model_b)
            result["ttl"] = ttl_eviction_canary(base, catalog_path, args.model_a, args.model_b)
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
