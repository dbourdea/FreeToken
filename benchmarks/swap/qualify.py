"""Opt-in Linux maintenance-window qualification against a real llama-swap binary.

Artifacts contain local operational paths and raw model output. Keep them private.
This script never changes the protected service's configuration or enablement.
"""

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
from concurrent.futures import ThreadPoolExecutor


def http(url, body=None, timeout=30):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def wait_health(url, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            doc = json.loads(http(url, timeout=3))
            if doc.get("status") == "ok":
                return doc
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise TimeoutError("health did not become ready")


def canary(url, model, stream=False):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "What is 2 + 2? Reply with only the single digit."}],
        "temperature": 0, "max_tokens": 32, "stream": stream,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if stream:
        body["stream_options"] = {"include_usage": True}
    raw = http(url + "/v1/chat/completions", body, timeout=660)
    if stream:
        parts = []
        assert b"data: [DONE]" in raw, "SSE completion marker missing"
        for line in raw.decode().splitlines():
            if line.startswith("data: ") and line != "data: [DONE]":
                doc = json.loads(line[6:])
                for choice in doc.get("choices", []):
                    parts.append(choice.get("delta", {}).get("content") or "")
        content = "".join(parts)
    else:
        doc = json.loads(raw)
        content = doc["choices"][0]["message"].get("content") or ""
    return raw, content.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "python", "llama-swap", "model-a", "model-b", "artifacts", "protected-service", "protected-url"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--allow-maintenance", action="store_true", required=True)
    parser.add_argument("--port", type=int, default=1960)
    parser.add_argument("--start-port", type=int, default=1961)
    parser.add_argument("--extended", action="store_true", help="Also test concurrent requests and idle eviction")
    args = parser.parse_args()
    artifacts = Path(args.artifacts)
    artifacts.mkdir(parents=True, exist_ok=False)
    status = {"trials": [], "restored": False}

    def save():
        (artifacts / "result.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

    service = ["sudo", "-n", "systemctl"]
    subprocess.run(service + ["is-active", "--quiet", args.protected_service], check=True)
    status["baselineHealth"] = wait_health(args.protected_url + "/health", 10)
    baseline_models = json.loads(http(args.protected_url + "/v1/models"))
    protected_model = baseline_models["data"][0]["id"]
    raw, content = canary(args.protected_url, protected_model)
    (artifacts / "baseline.json").write_bytes(raw)
    if content != "4":
        raise RuntimeError("protected-service baseline canary did not return 4; no maintenance performed")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(args.source) / "python")
    env["PATH"] = str(Path.home() / ".local/bin") + os.pathsep + env.get("PATH", "")
    # Avoid sharing extension binaries or abandoned build locks across revisions.
    env["TORCH_EXTENSIONS_DIR"] = str(artifacts / "torch-extensions")
    env["MAX_JOBS"] = "2"
    config = ["healthCheckTimeout: 600", "globalTTL: 0", "unloadTimeout: 45", "logToStdout: both", f"startPort: {args.start_port}", "models:"]
    import shlex

    for alias, model in (("model-a", args.model_a), ("model-b", args.model_b)):
        command = shlex.join([
            args.python, "-m", "freetoken.cli", "serve", "--model", model,
            "--host", "127.0.0.1", "--port", "${PORT}", "--served-model-name", "${MODEL_ID}",
            "--max-seq-len-override", "4096", "--num-tokens", "4096", "--max-prefill-length", "512",
            "--max-running-requests", "1", "--graph", "1", "--memory-ratio", "0.75",
            "--attention-backend", "triton", "--moe-backend", "fused", "--disable-pynccl",
        ])
        config += [f"  {alias}:", "    cmd: " + json.dumps(command), "    checkEndpoint: /ready", "    proxy: http://127.0.0.1:${PORT}"]
        if args.extended:
            config.append("    ttl: 5")
    config_path = artifacts / "models.yaml"
    config_path.write_text("\n".join(config) + "\n", encoding="utf-8")
    subprocess.run([args.llama_swap, "-config", str(config_path), "-validate"], env=env, check=True)
    print("NATIVE_KERNEL_PREFLIGHT_STARTED", flush=True)
    with (artifacts / "kernel-build.log").open("wb") as build_log:
        subprocess.run([args.python, "-c", "from freetoken.kernel.gguf import _module; _module(); print('NATIVE_KERNEL_READY')"],
                       env=env, cwd=args.source, stdout=build_log, stderr=subprocess.STDOUT, check=True, timeout=600)
    proc = None
    maintenance = False

    def interrupted(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGHUP, interrupted)
    try:
        # Set the restore obligation before the stop, including partial failures.
        maintenance = True
        subprocess.run(service + ["stop", args.protected_service], check=True, timeout=90)
        print("MAINTENANCE_STARTED", flush=True)
        with (artifacts / "swap.log").open("wb") as log:
            proc = subprocess.Popen([args.llama_swap, "-config", str(config_path), "-listen", f"127.0.0.1:{args.port}"],
                                    env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            base = f"http://127.0.0.1:{args.port}"
            deadline = time.monotonic() + 20
            while True:
                try:
                    listing = json.loads(http(base + "/v1/models", timeout=2))
                    assert {item["id"] for item in listing["data"]} == {"model-a", "model-b"}
                    break
                except (OSError, ValueError):
                    if time.monotonic() >= deadline or proc.poll() is not None:
                        raise
                    time.sleep(0.5)
            for index, (alias, streaming) in enumerate((("model-a", False), ("model-b", True), ("model-a", True))):
                started = time.monotonic()
                print(f"TRIAL_STARTED {index} {alias}", flush=True)
                raw, content = canary(base, alias, streaming)
                (artifacts / f"trial-{index}.response").write_bytes(raw)
                row = {"model": alias, "stream": streaming, "seconds": time.monotonic() - started, "content": content, "passed": content == "4"}
                status["trials"].append(row)
                save()
                print("TRIAL_RESULT " + json.dumps(row), flush=True)
                if not row["passed"]:
                    raise RuntimeError("deterministic quality gate failed")
            if args.extended:
                for names in (("model-a", "model-a"), ("model-a", "model-b")):
                    with ThreadPoolExecutor(2) as clients:
                        futures = [clients.submit(canary, base, name, True) for name in names]
                        for index, future in enumerate(futures):
                            raw, content = future.result()
                            (artifacts / f"concurrent-{'-'.join(names)}-{index}.sse").write_bytes(raw)
                            assert content == "4", "concurrent quality gate failed"
                            assert b'"usage"' in raw, "streamed usage block missing"
                    print("CONCURRENT_OK " + ",".join(names), flush=True)
                status["concurrentPassed"] = True
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    running = json.loads(http(base + "/running"))
                    if running.get("running") == []:
                        status["idleEvictionPassed"] = True
                        break
                    time.sleep(1)
                assert status.get("idleEvictionPassed"), "idle TTL did not unload the models"
                print("IDLE_EVICTION_OK", flush=True)
    except BaseException as exc:
        status["error"] = repr(exc)
        print("QUALIFICATION_FAILED " + repr(exc), flush=True)
    finally:
        if proc is not None:
            try:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(timeout=60)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait(timeout=10)
            except (OSError, subprocess.TimeoutExpired) as exc:
                status["cleanupError"] = repr(exc)
        if maintenance:
            try:
                subprocess.run(service + ["start", args.protected_service], check=True, timeout=180)
                status["restoredHealth"] = wait_health(args.protected_url + "/health", 300)
                raw, content = canary(args.protected_url, protected_model)
                (artifacts / "restored.json").write_bytes(raw)
                status["restored"] = content == "4"
                print("RESTORED " + str(status["restored"]), flush=True)
            except Exception as exc:
                status["restoreError"] = repr(exc)
                print("RESTORE_FAILED " + repr(exc), flush=True)
        save()
    passed = (status["restored"] and "error" not in status and "cleanupError" not in status
              and len(status["trials"]) == 3 and all(x["passed"] for x in status["trials"]))
    if args.extended:
        passed = passed and status.get("concurrentPassed") and status.get("idleEvictionPassed")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
