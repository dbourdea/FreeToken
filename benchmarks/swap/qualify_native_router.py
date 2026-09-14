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
import subprocess
import sys
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
    with urllib.request.urlopen(request, timeout=660) as response:
        for chunk in response:
            if first_byte_s is None:
                first_byte_s = time.monotonic() - started
            raw.extend(chunk)
            if len(raw) > 8 * 1024 * 1024:
                raise RuntimeError("canary response exceeded private capture bound")
            if chunk.startswith(b"data: ") and chunk.strip() != b"data: [DONE]":
                event = json.loads(chunk[6:])
                for choice in event.get("choices", []):
                    content.append(choice.get("delta", {}).get("content") or "")
    duration_s = time.monotonic() - started
    answer = "".join(content).strip()
    if b"data: [DONE]" not in raw:
        raise RuntimeError("SSE completion marker missing")
    if answer != "4":
        raise RuntimeError("deterministic quality gate failed")
    return bytes(raw), {
        "route": "direct" if direct else "native_router",
        "model": model,
        "firstByteSeconds": first_byte_s,
        "durationSeconds": duration_s,
        "responseBytes": len(raw),
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
    common_args = [
        "--host", "127.0.0.1", "--served-model-name", "${MODEL_ID}",
        "--max-seq-len-override", "4096", "--num-tokens", "4096", "--max-prefill-length", "512",
        "--max-running-requests", "1", "--graph", "1", "--memory-ratio", "0.75",
        "--attention-backend", "triton", "--moe-backend", "fused", "--disable-pynccl",
    ]
    catalog = ["[router]", "upstream_timeout_s = 660", ""]
    for alias, model in (("model-a", args.model_a), ("model-b", args.model_b)):
        catalog.extend((
            f"[models.{alias}]", f"model = {json.dumps(model)}", "port = 0", "ready_timeout_s = 600",
            "unload_ttl_s = 0", "args = " + json.dumps(common_args).replace("${MODEL_ID}", alias), "",
        ))
    catalog_path = artifacts / "models.toml"
    catalog_path.write_text("\n".join(catalog), encoding="utf-8")
    with (artifacts / "kernel-preflight.log").open("wb") as log:
        subprocess.run(
            [args.python, "-c", "from freetoken.kernel.gguf import _module; _module(); print('NATIVE_KERNEL_READY')"],
            cwd=args.source, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600,
        )

    daemon: subprocess.Popen[bytes] | None = None
    maintenance = False
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
            _, loaded = request_json(base + "/router/load", {"name": "model-a"}, timeout=660)
            direct_raw, direct_row = canary(f"http://127.0.0.1:{loaded['port']}", "model-a", direct=True)
            (artifacts / "direct-a.sse").write_bytes(direct_raw)
            result["trials"].append(direct_row)

            for label, alias in (("warm-a", "model-a"), ("cold-b", "model-b"), ("alternating-a", "model-a")):
                raw, row = canary(base, alias, direct=False)
                row["scenario"] = label
                row["router"] = request_json(base + "/router/status")[1]
                (artifacts / f"{label}.sse").write_bytes(raw)
                (artifacts / f"{label}.metrics").write_bytes(request_bytes(base + "/metrics"))
                result["trials"].append(row)
                save()
            result["passed"] = len(result["trials"]) == 4 and all(x["passed"] for x in result["trials"])
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
            except (OSError, subprocess.TimeoutExpired) as exc:
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
