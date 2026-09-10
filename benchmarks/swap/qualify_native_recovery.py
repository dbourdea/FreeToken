"""Opt-in real-model daemon recovery test. Raw artifacts must remain private."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from qualify import canary, http, wait_health


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "daemon-source", "python", "model", "extensions-dir",
                 "protected-service", "protected-url", "artifacts"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--allow-maintenance", action="store_true", required=True)
    parser.add_argument("--port", type=int, default=1963)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(args.daemon_source) / "python"))
    from fastapi.testclient import TestClient
    from freetoken.daemon.app import build_app
    from freetoken.daemon.catalog import ModelCatalog
    from freetoken.daemon.logring import LogRing
    from freetoken.daemon.pidfile import ServeStateStore
    from freetoken.daemon.proxy import ServeProbe
    from freetoken.daemon.serve_manager import PopenChild, ServeManager

    artifacts = Path(args.artifacts)
    artifacts.mkdir(parents=True, exist_ok=False)
    status = {"passed": False, "restored": False}
    service = ["sudo", "-n", "systemctl"]
    subprocess.run(service + ["is-active", "--quiet", args.protected_service], check=True)
    status["baselineHealth"] = wait_health(args.protected_url + "/health", 10)
    protected_model = json.loads(http(args.protected_url + "/v1/models"))["data"][0]["id"]
    raw, content = canary(args.protected_url, protected_model)
    (artifacts / "baseline.json").write_bytes(raw)
    assert content == "4", "baseline failed; no maintenance performed"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(args.source) / "python")
    env["TORCH_EXTENSIONS_DIR"] = args.extensions_dir
    env["MAX_JOBS"] = "2"
    with (artifacts / "kernel-preflight.log").open("wb") as log:
        subprocess.run([args.python, "-c", "from freetoken.kernel.gguf import _module; _module()"],
                       cwd=args.source, env=env, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=600)
    # Deliberately corrupt test artifact, never an existing model file.
    bad_model = artifacts / "invalid-test-model.gguf"
    bad_model.write_bytes(b"INVALID_GGUF_TEST_FIXTURE")
    common = ["--host", "127.0.0.1", "--served-model-name", "native-recovery",
              "--max-seq-len-override", "4096", "--num-tokens", "4096",
              "--max-prefill-length", "512", "--max-running-requests", "1",
              "--graph", "1", "--memory-ratio", "0.75", "--attention-backend", "triton",
              "--moe-backend", "fused", "--disable-pynccl"]
    catalog_path = artifacts / "models.toml"
    catalog_path.write_text("\n".join(
        f"[models.{name}]\nmodel = {json.dumps(str(model))}\nport = {args.port}\n"
        f"ready_timeout_s = 600\nargs = {json.dumps(common)}\n"
        for name, model in (("good", args.model), ("bad", bad_model))), encoding="utf-8")
    children = []

    def spawn(model, port, launch_args):
        log_path = artifacts / f"engine-{len(children)}.log"
        with log_path.open("wb") as log:
            proc = subprocess.Popen([args.python, "-m", "freetoken.cli", "serve",
                                     "--model", model, "--port", str(port), *launch_args],
                                    cwd=args.source, env=env, stdout=log, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, start_new_session=True)
        child = PopenChild(proc, str(log_path))
        children.append(child)
        return child

    probe = ServeProbe()
    ring = LogRing()
    store = ServeStateStore(str(artifacts / "serve.json"))
    manager = ServeManager(ring, store, spawn_fn=spawn, apply_oom=False,
                           prepare_stop=probe.prepare_stop, read_stats=probe.fresh_stats,
                           grace_s=30, reap_wait_s=15)
    maintenance = False

    def interrupt(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGHUP, interrupt)
    try:
        maintenance = True
        subprocess.run(service + ["stop", args.protected_service], check=True, timeout=90)
        print("NATIVE_MAINTENANCE_STARTED", flush=True)
        with ThreadPoolExecutor(2) as lifecycle, ThreadPoolExecutor(2) as proxy:
            app = build_app(manager=manager, ring=ring, probe=probe, footprint_fn=lambda pid: {},
                            lifecycle_pool=lifecycle, proxy_pool=proxy,
                            catalog=ModelCatalog.load(str(catalog_path)))
            with TestClient(app) as client:
                response = client.post("/engine/start-profile", json={"name": "good"})
                status["initial"] = response.json()
                assert response.status_code == 200 and response.json()["readiness"]["ready"]
                raw, content = canary(f"http://127.0.0.1:{args.port}", "native-recovery")
                (artifacts / "before-failure.json").write_bytes(raw)
                assert content == "4"
                print("NATIVE_BASELINE_OK", flush=True)
                response = client.post("/engine/switch-profile", json={"name": "bad"})
                status["failedSwitch"] = response.json()
                assert response.status_code == 503, "failed model must not report success"
                rollback = response.json()["rollback"]
                assert rollback["launched"] and rollback["readiness"]["ready"]
                assert len(children) == 3 and children[1].proc.poll() not in (None, 0)
                assert "GGUF magic invalid" in (artifacts / "engine-1.log").read_text(errors="replace"), \
                    "replacement must fail for the intended invalid-GGUF reason"
                assert store.load().model == args.model
                raw, content = canary(f"http://127.0.0.1:{args.port}", "native-recovery", True)
                (artifacts / "after-recovery.sse").write_bytes(raw)
                assert content == "4", "restored model failed generation"
                status["accounting"] = manager.pending_accounting()
                assert any(row.get("drainComplete") and not row.get("degraded")
                           for row in status["accounting"]), "previous engine receipt must be sealed"
                assert any(row.get("reason") == "engine-crashed" and row.get("degraded")
                           for row in status["accounting"]), "loader failure must retain explicit crash accounting"
                status["passed"] = True
                print("NATIVE_MODEL_RECOVERY_OK", flush=True)
    except BaseException as exc:
        status["error"] = repr(exc)
        print("NATIVE_RECOVERY_FAILED " + repr(exc), flush=True)
    finally:
        try:
            manager.stop(force=True)
        except Exception as exc:
            status["cleanupError"] = repr(exc)
        for child in children:
            try:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                if child.proc.poll() is None:
                    child.proc.wait(timeout=15)
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
        (artifacts / "result.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    return 0 if status["passed"] and status["restored"] and "cleanupError" not in status else 1


if __name__ == "__main__":
    sys.exit(main())
