"""Opt-in real-model daemon recovery test. Raw artifacts must remain private."""
# What: document opt in real model daemon recovery test raw in the qualify_native_recovery docstring; why: introspection and maintainers read this exact docstring fragment to understand qualify native recovery behavior without executing it.

# What: import argparse for main using argparse; why: main uses argparse argument parser, making that imported dependency available to its named operation.
import argparse
# What: import from concurrent futures import ThreadPoolExecutor; why: this module calls or annotates these symbols in the branch-created operations below.
from concurrent.futures import ThreadPoolExecutor
# What: import json for main using json; why: main uses json dumps, making that imported dependency available to its named operation.
import json
# What: import os for main using os; why: main uses os environ copy, making that imported dependency available to its named operation.
import os
# What: import path for main using pathlib and path; why: main uses path, making that imported dependency available to its named operation.
from pathlib import Path
# What: import signal for main using signal; why: main uses signal signal, making that imported dependency available to its named operation.
import signal
# What: import subprocess for main using subprocess; why: main uses subprocess run, making that imported dependency available to its named operation.
import subprocess
# What: import sys for module initialization using sys; why: module initialization uses sys exit, making that imported dependency available to its named operation.
import sys

# What: import canary and http and require expected hostname and wait health for main using qualify and canary and http and require expected hostname and wait health; why: main uses canary and http and require expected hostname and wait health, making that imported dependency available to its named operation.
from qualify import canary, http, require_expected_hostname, wait_health


# What: define main around the current object state; why: its direct callers call main for main and rely on this exact input and result contract.
def main():
    # What: compute parser from argument parser and argparse and doc; why: parser add argument name required later reads parser, so main must retain the computed value under that name.
    parser = argparse.ArgumentParser(description=__doc__)
    # What: iterate across the computed value to perform add argument and parser and name; why: main repeats the body only while or for the loop header admits an iteration.
    for name in ("source", "daemon-source", "python", "model", "extensions-dir",
                 # What: apply the protected service protected url artifacts expected hostname portion of the enclosing predicate; why: this clause remains in main\'s enclosing expression so its grouping and evaluation order stay intact.
                 "protected-service", "protected-url", "artifacts", "expected-hostname"):
        # What: register the parser add argument name required True command-line option; why: main validates this operator input before starting the qualification sequence.
        parser.add_argument("--" + name, required=True)
    # What: register the parser add argument allow maintenance action store true required True command-line option; why: main validates this operator input before starting the qualification sequence.
    parser.add_argument("--allow-maintenance", action="store_true", required=True)
    # What: register the parser add argument port type int default 1963 command-line option; why: main validates this operator input before starting the qualification sequence.
    parser.add_argument("--port", type=int, default=1963)
    # What: compute args from parse args and parser; why: require expected hostname args expected hostname later reads args, so main must retain the computed value under that name.
    args = parser.parse_args()
    # What: call require_expected_hostname with expected hostname and args; why: main invokes require_expected_hostname while performing sys path insert str path args daemon source python; the call advances that operation through its result or side effect.
    require_expected_hostname(args.expected_hostname)
    # What: preserve the exact sys path insert str path args daemon source python literal fragment; why: main passes this fragment verbatim through sys.path.insert(0, str(Path(args.daemon_source) / "python")), because changing it would alter a protocol payload, serialized fixture, or public message.
    sys.path.insert(0, str(Path(args.daemon_source) / "python"))
    # What: import test client for main using fastapi and testclient and test client; why: main uses test client, making that imported dependency available to its named operation.
    from fastapi.testclient import TestClient
    # What: import build app for main using freetoken and daemon and app and build app; why: main uses build app, making that imported dependency available to its named operation.
    from freetoken.daemon.app import build_app
    # What: import model catalog for main using freetoken and daemon and catalog and model catalog; why: main uses model catalog load, making that imported dependency available to its named operation.
    from freetoken.daemon.catalog import ModelCatalog
    # What: import log ring for main using freetoken and daemon and logring and log ring; why: main uses log ring, making that imported dependency available to its named operation.
    from freetoken.daemon.logring import LogRing
    # What: import serve state store for main using freetoken and daemon and pidfile and serve state store; why: main uses serve state store, making that imported dependency available to its named operation.
    from freetoken.daemon.pidfile import ServeStateStore
    # What: import serve probe for main using freetoken and daemon and proxy and serve probe; why: main uses serve probe, making that imported dependency available to its named operation.
    from freetoken.daemon.proxy import ServeProbe
    # What: import popen child and serve manager for spawn and main using freetoken and daemon and serve manager and popen child and serve manager; why: spawn and main uses popen child and serve manager, making that imported dependency available to its named operation.
    from freetoken.daemon.serve_manager import PopenChild, ServeManager

    # What: compute artifacts from path and artifacts and args; why: artifacts mkdir parents exist ok later reads artifacts, so main must retain the computed value under that name.
    artifacts = Path(args.artifacts)
    # What: supply parents to artifacts.mkdir; why: main binds this true value to artifacts.mkdir's parents input.
    artifacts.mkdir(parents=True, exist_ok=False)
    # What: map the passed field as false; why: main carries passed through status into status baseline health wait health args protected url health 10.
    status = {"passed": False, "restored": False}
    # What: compute service from sudo and n and systemctl; why: subprocess run service is active quiet args protected service check later reads service, so main must retain the computed value under that name.
    service = ["sudo", "-n", "systemctl"]
    # What: execute subprocess run service is active quiet args protected service check True; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
    subprocess.run(service + ["is-active", "--quiet", args.protected_service], check=True)
    # What: compute status entry from wait health and protected url and args and 10 and health; why: status initial response json later reads status entry, so main must retain the computed value under that name.
    status["baselineHealth"] = wait_health(args.protected_url + "/health", 10)
    # What: compute protected model from loads and json and http and protected url; why: raw content canary args protected url protected model later reads protected model, so main must retain the computed value under that name.
    protected_model = json.loads(http(args.protected_url + "/v1/models"))["data"][0]["id"]
    # What: evaluate and capture raw content canary args protected url protected model; why: the enclosing qualifier uses the captured result in its next validation or artifact step.
    raw, content = canary(args.protected_url, protected_model)
    # What: execute artifacts baseline json write bytes raw; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
    (artifacts / "baseline.json").write_bytes(raw)
    # What: assert that content equals 4; why:  main requires content equals 4 to be true, so a false result stops the invalid state.
    assert content == "4", "baseline failed; no maintenance performed"
    # What: compute env from copy and environ and os; why: env pythonpath str path args source python later reads env, so main must retain the computed value under that name.
    env = os.environ.copy()
    # What: compute env entry from str and path and source and args and python; why: env torch extensions dir args extensions dir later reads env entry, so main must retain the computed value under that name.
    env["PYTHONPATH"] = str(Path(args.source) / "python")
    # What: compute env entry from extensions dir and args; why: env max jobs later reads env entry, so main must retain the computed value under that name.
    env["TORCH_EXTENSIONS_DIR"] = args.extensions_dir
    # What: compute env entry from 2; why: cwd args source env env stdout log later reads env entry, so main must retain the computed value under that name.
    env["MAX_JOBS"] = "2"
    # What: open the with artifacts kernel preflight log open wb as log resource scope; why: the qualification operation releases this resource when the guarded block exits.
    with (artifacts / "kernel-preflight.log").open("wb") as log:
        # What: execute subprocess run args python c from freetoken kernel gguf import  module  module; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
        subprocess.run([args.python, "-c", "from freetoken.kernel.gguf import _module; _module()"],
                       # What: supply cwd to subprocess.run; why: main binds this source and args value to subprocess.run's cwd input.
                       cwd=args.source, env=env, stdout=log, stderr=subprocess.STDOUT,
                       # What: supply check to subprocess.run; why: main binds this true value to subprocess.run's check input.
                       check=True, timeout=600)
    # Deliberately corrupt test artifact, never an existing model file.
    # What: compute bad model from artifacts and invalid test model and gguf; why: bad model write bytes b invalid gguf test fixture later reads bad model, so main must retain the computed value under that name.
    bad_model = artifacts / "invalid-test-model.gguf"
    # What: call bad_model.write_bytes with the named fixture input; why: main invokes bad_model.write_bytes while performing common host served model name native recovery; the call advances that operation through its result or side effect.
    bad_model.write_bytes(b"INVALID_GGUF_TEST_FIXTURE")
    # What: compute common from host and 127 0 0 1 and served model name and native recovery and max seq len override; why: f ready timeout s nargs json dumps common n later reads common, so main must retain the computed value under that name.
    common = ["--host", "127.0.0.1", "--served-model-name", "native-recovery",
              # What: apply the max seq len override num tokens portion of common; why: main uses this clause to evaluate common as one grouped value.
              "--max-seq-len-override", "4096", "--num-tokens", "4096",
              # What: apply the max prefill length max running requests portion of common; why: main uses this clause to evaluate common as one grouped value.
              "--max-prefill-length", "512", "--max-running-requests", "1",
              # What: apply the graph memory ratio attention backend triton portion of common; why: main uses this clause to evaluate common as one grouped value.
              "--graph", "1", "--memory-ratio", "0.75", "--attention-backend", "triton",
              # What: apply the moe backend fused disable pynccl portion of common; why: main uses this clause to evaluate common as one grouped value.
              "--moe-backend", "fused", "--disable-pynccl"]
    # What: compute catalog path from artifacts and models and toml; why: catalog path write text n join later reads catalog path, so main must retain the computed value under that name.
    catalog_path = artifacts / "models.toml"
    # What: preserve the exact catalog path write text n join literal fragment; why: main passes this fragment verbatim through catalog_path.write_text("\n".join(, because changing it would alter a protocol payload, serialized fixture, or public message.
    catalog_path.write_text("\n".join(
        # What: preserve the exact f models name nmodel json dumps str literal fragment; why: main passes this fragment verbatim through f"[models.{name}]\nmodel = {json.dumps(str(model))}\nport = {args.port}\, because changing it would alter a protocol payload, serialized fixture, or public message.
        # What: preserve the exact f ready timeout s nargs json dumps common n literal fragment; why: main passes this fragment verbatim through f"[models.{name}]\nmodel = {json.dumps(str(model))}\nport = {args.port}\, because changing it would alter a protocol payload, serialized fixture, or public message.
        f"[models.{name}]\nmodel = {json.dumps(str(model))}\nport = {args.port}\n"
        f"ready_timeout_s = 600\nargs = {json.dumps(common)}\n"
        # What: preserve the exact for name model in good args model literal fragment; why: main passes this fragment verbatim through for name, model in (("good", args.model), ("bad", bad_model))), encoding, because changing it would alter a protocol payload, serialized fixture, or public message.
        for name, model in (("good", args.model), ("bad", bad_model))), encoding="utf-8")
    # What: initialize children as an empty runtime accumulator; why: main appends or maps entries into it during log path artifacts f engine len children log before consuming the aggregate.
    children = []

    # What: define spawn around model and port and launch args; why: its direct callers call spawn for spawn and rely on this exact input and result contract.
    def spawn(model, port, launch_args):
        # What: compute log path from artifacts and len and children and engine and log; why: with log path open wb as log later reads log path, so spawn must retain the computed value under that name.
        log_path = artifacts / f"engine-{len(children)}.log"
        # What: enter the log_path.open managed context before proc subprocess popen args python m freetoken cli serve; why: spawn releases this resource or lock after proc subprocess popen args python m freetoken cli serve on both success and failure paths.
        with log_path.open("wb") as log:
            # What: compute proc from popen and subprocess and python and model; why: child popen child proc str log path later reads proc, so spawn must retain the computed value under that name.
            proc = subprocess.Popen([args.python, "-m", "freetoken.cli", "serve",
                                     # What: call str with port; why: spawn invokes str while performing cwd args source env env stdout log; the call advances that operation through its result or side effect.
                                     "--model", model, "--port", str(port), *launch_args],
                                    # What: supply cwd to subprocess.Popen; why: spawn binds this source and args value to subprocess.Popen's cwd input.
                                    cwd=args.source, env=env, stdout=log, stderr=subprocess.STDOUT,
                                    # What: supply stdin to subprocess.Popen; why: spawn binds this devnull and subprocess value to subprocess.Popen's stdin input.
                                    stdin=subprocess.DEVNULL, start_new_session=True)
        # What: compute child from popen child and proc and str and log path; why: children append child later reads child, so spawn must retain the computed value under that name.
        child = PopenChild(proc, str(log_path))
        # What: call children.append with child; why: spawn invokes children.append while performing return child; the call advances that operation through its result or side effect.
        children.append(child)
        # What: return child from spawn; why: spawn exposes child so its caller can continue with the function\'s computed outcome.
        return child

    # What: compute probe from serve probe; why: prepare stop probe prepare stop read stats probe fresh stats later reads probe, so main must retain the computed value under that name.
    probe = ServeProbe()
    # What: compute ring from log ring; why: manager serve manager ring store spawn fn spawn later reads ring, so main must retain the computed value under that name.
    ring = LogRing()
    # What: compute store from serve state store and str and artifacts and serve and json; why: manager serve manager ring store spawn fn spawn later reads store, so main must retain the computed value under that name.
    store = ServeStateStore(str(artifacts / "serve.json"))
    # What: compute manager from serve manager and ring and store and spawn; why: app build app manager manager ring ring later reads manager, so main must retain the computed value under that name.
    manager = ServeManager(ring, store, spawn_fn=spawn, apply_oom=False,
                           # What: supply prepare stop to ServeManager; why: main binds this prepare stop and probe value to ServeManager's prepare stop input.
                           prepare_stop=probe.prepare_stop, read_stats=probe.fresh_stats,
                           # What: supply grace s to ServeManager; why: main binds this 30 value to ServeManager's grace s input.
                           grace_s=30, reap_wait_s=15)
    # What: compute maintenance from false; why: maintenance later reads maintenance, so main must retain the computed value under that name.
    maintenance = False

    # What: define interrupt around the current object state; why: its direct callers call interrupt for interrupt and rely on this exact input and result contract.
    def interrupt(*_):
        # What: propagate the active failure to the caller; why: interrupt stops this rejected path before it can mutate state, dispatch work, or report success.
        raise KeyboardInterrupt

    # What: call signal.signal with sigterm and signal and interrupt; why: main invokes signal.signal while performing signal signal signal sighup interrupt; the call advances that operation through its result or side effect.
    signal.signal(signal.SIGTERM, interrupt)
    # What: call signal.signal with sighup and signal and interrupt; why: main invokes signal.signal while performing try; the call advances that operation through its result or side effect.
    signal.signal(signal.SIGHUP, interrupt)
    # What: establish the handler boundary for the protected operation; why: main routes failures to base exception while preserving cleanup and success flow.
    try:
        # What: compute maintenance from true; why: if maintenance later reads maintenance, so main must retain the computed value under that name.
        maintenance = True
        # What: execute subprocess run service stop args protected service check True timeout 90; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
        subprocess.run(service + ["stop", args.protected_service], check=True, timeout=90)
        # What: preserve the exact print native maintenance started flush literal fragment; why: main passes this fragment verbatim through print("NATIVE_MAINTENANCE_STARTED", flush=True), because changing it would alter a protocol payload, serialized fixture, or public message.
        print("NATIVE_MAINTENANCE_STARTED", flush=True)
        # What: enter the ThreadPoolExecutor and ThreadPoolExecutor managed context before app build app manager manager ring ring; why: main releases this resource or lock after app build app manager manager ring ring on both success and failure paths.
        with ThreadPoolExecutor(2) as lifecycle, ThreadPoolExecutor(2) as proxy:
            # What: declare the pid input for main; why: main consumes pid during signature binding, so callers must bind it with the other signature inputs.
            app = build_app(manager=manager, ring=ring, probe=probe, footprint_fn=lambda pid: {},
                            # What: supply lifecycle pool to build_app; why: main binds this lifecycle value to build_app's lifecycle pool input.
                            lifecycle_pool=lifecycle, proxy_pool=proxy,
                            # What: supply catalog to ModelCatalog.load; why: main binds this load and model catalog and str and catalog path value to ModelCatalog.load's catalog input.
                            catalog=ModelCatalog.load(str(catalog_path)))
            # What: enter the TestClient managed context before response client post engine start profile json name; why: main releases this resource or lock after response client post engine start profile json name on both success and failure paths.
            with TestClient(app) as client:
                # What: map the name field as good; why: main carries name through response into status initial response json.
                response = client.post("/engine/start-profile", json={"name": "good"})
                # What: compute status entry from json and response; why: status failed switch response json later reads status entry, so main must retain the computed value under that name.
                status["initial"] = response.json()
                # What: assert that response status code equals 200 and response json readiness ready; why: main requires response status code equals 200 and response json readiness ready to be true, so a false result stops the invalid state.
                assert response.status_code == 200 and response.json()["readiness"]["ready"]
                # What: compute raw and content from canary and port and args and native recovery and http; why: artifacts before failure json write bytes raw later reads raw and content, so main must retain the computed value under that name.
                raw, content = canary(f"http://127.0.0.1:{args.port}", "native-recovery")
                # What: preserve the exact artifacts before failure json write bytes raw literal fragment; why: main passes this fragment verbatim through (artifacts / "before-failure.json").write_bytes(raw), because changing it would alter a protocol payload, serialized fixture, or public message.
                (artifacts / "before-failure.json").write_bytes(raw)
                # What: assert that content equals 4; why:  main requires content equals 4 to be true, so a false result stops the invalid state.
                assert content == "4"
                # What: preserve the exact print native baseline ok flush literal fragment; why: main passes this fragment verbatim through print("NATIVE_BASELINE_OK", flush=True), because changing it would alter a protocol payload, serialized fixture, or public message.
                print("NATIVE_BASELINE_OK", flush=True)
                # What: map the name field as bad; why: main carries name through response into status failed switch response json.
                response = client.post("/engine/switch-profile", json={"name": "bad"})
                # What: compute status entry from json and response; why: status accounting manager pending accounting later reads status entry, so main must retain the computed value under that name.
                status["failedSwitch"] = response.json()
                # What: assert that response status code equals 503; why: main requires response status code equals 503 to be true, so a false result stops the invalid state.
                assert response.status_code == 503, "failed model must not report success"
                # What: compute rollback from json and response and rollback; why: assert rollback launched and rollback readiness later reads rollback, so main must retain the computed value under that name.
                rollback = response.json()["rollback"]
                # What: assert that rollback launched and rollback readiness ready; why: main requires rollback launched and rollback readiness ready to be true, so a false result stops the invalid state.
                assert rollback["launched"] and rollback["readiness"]["ready"]
                # What: assert that len children equals 3 and children 1 proc poll not in; why: main requires len children equals 3 and children 1 proc poll not in to be true, so a false result stops the invalid state.
                assert len(children) == 3 and children[1].proc.poll() not in (None, 0)
                # What: require GGUF magic invalid in artifacts engine 1 log read text errors replace; why: the qualifier stops immediately when this protected invariant is false.
                # What: require GGUF magic invalid in artifacts engine 1 log read text errors replace; why: the qualifier stops immediately when this protected invariant is false.
                assert "GGUF magic invalid" in (artifacts / "engine-1.log").read_text(errors="replace"), \
                    "replacement must fail for the intended invalid-GGUF reason"
                # What: assert that store load model equals args model; why: main requires store load model equals args model to be true, so a false result stops the invalid state.
                assert store.load().model == args.model
                # What: compute raw and content from canary and port and args and native recovery and true; why: artifacts after recovery sse write bytes raw later reads raw and content, so main must retain the computed value under that name.
                raw, content = canary(f"http://127.0.0.1:{args.port}", "native-recovery", True)
                # What: preserve the exact artifacts after recovery sse write bytes raw literal fragment; why: main passes this fragment verbatim through (artifacts / "after-recovery.sse").write_bytes(raw), because changing it would alter a protocol payload, serialized fixture, or public message.
                (artifacts / "after-recovery.sse").write_bytes(raw)
                # What: assert that content equals 4; why:  main requires content equals 4 to be true, so a false result stops the invalid state.
                assert content == "4", "restored model failed generation"
                # What: compute status entry from pending accounting and manager; why: for row in status accounting previous later reads status entry, so main must retain the computed value under that name.
                status["accounting"] = manager.pending_accounting()
                # What: require any row get drainComplete and not row get degraded; why: the qualifier stops immediately when this protected invariant is false.
                assert any(row.get("drainComplete") and not row.get("degraded")
                           # What: execute for row in status accounting previous engine receipt must be sealed; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
                           for row in status["accounting"]), "previous engine receipt must be sealed"
                # What: require any row get reason == engine crashed and row get degraded; why: the qualifier stops immediately when this protected invariant is false.
                assert any(row.get("reason") == "engine-crashed" and row.get("degraded")
                           # What: execute for row in status accounting loader failure must retain explicit crash accounting; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
                           for row in status["accounting"]), "loader failure must retain explicit crash accounting"
                # What: compute status entry from true; why: status error repr exc later reads status entry, so main must retain the computed value under that name.
                status["passed"] = True
                # What: preserve the exact print native model recovery ok flush literal fragment; why: main passes this fragment verbatim through print("NATIVE_MODEL_RECOVERY_OK", flush=True), because changing it would alter a protocol payload, serialized fixture, or public message.
                print("NATIVE_MODEL_RECOVERY_OK", flush=True)
    # What: handle base exception by status error repr exc; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
    except BaseException as exc:
        # What: compute status entry from repr and exc; why: status cleanup error repr exc later reads status entry, so  main must retain the computed value under that name.
        status["error"] = repr(exc)
        # What: preserve the exact print native recovery failed repr exc flush literal fragment; why: main passes this fragment verbatim through print("NATIVE_RECOVERY_FAILED " + repr(exc), flush=True), because changing it would alter a protocol payload, serialized fixture, or public message.
        print("NATIVE_RECOVERY_FAILED " + repr(exc), flush=True)
    # What: run try on every exit path; why: main performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
    finally:
        # What: establish the handler boundary for the protected operation; why: main routes failures to exception while preserving cleanup and success flow.
        try:
            # What: supply force to manager.stop; why: main binds this true value to manager.stop's force input.
            manager.stop(force=True)
        # What: handle exception by status cleanup error repr exc; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
        except Exception as exc:
            # What: compute status entry from repr and exc; why: status cleanup error repr exc later reads status entry, so  main must retain the computed value under that name.
            status["cleanupError"] = repr(exc)
        # What: iterate across children to perform process lookup error and oserror and timeout expired and killpg and pid; why: main repeats the body only while or for the loop header admits an iteration.
        for child in children:
            # What: establish the handler boundary for the protected operation; why: main routes failures to oserror and timeout expired and subprocess while preserving cleanup and success flow.
            try:
                # What: establish the handler boundary for the protected operation; why: main routes failures to process lookup error while preserving cleanup and success flow.
                try:
                    # What: call os.killpg with pid and child and sigkill and signal; why: main invokes os.killpg while performing except process lookup error; the call advances that operation through its result or side effect.
                    os.killpg(child.pid, signal.SIGKILL)
                # What: handle process lookup error by pass; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
                except ProcessLookupError:
                    # What: ignore the anticipated exception handled by this branch; why: interrupt continues its retry or cleanup path instead of re-raising that transient failure.
                    pass
                # What: gate on poll and proc and child before wait and proc and child; why: main admits wait and proc and child only for this predicate and excludes the opposite state.
                if child.proc.poll() is None:
                    # What: supply timeout to child.proc.wait; why: main binds this 15 value to child.proc.wait's timeout input.
                    child.proc.wait(timeout=15)
            # What: handle oserror and timeout expired and subprocess by status cleanup error repr exc; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
            except (OSError, subprocess.TimeoutExpired) as exc:
                # What: compute status entry from repr and exc; why: status restored health wait health args protected url health later reads status entry, so main must retain the computed value under that name.
                status["cleanupError"] = repr(exc)
        # What: gate on maintenance before exception and run and status and wait health and raw; why: main admits exception and run and status and wait health and raw only for this predicate and excludes the opposite state.
        if maintenance:
            # What: establish the handler boundary for the protected operation; why: main routes failures to exception while preserving cleanup and success flow.
            try:
                # What: execute subprocess run service start args protected service check True timeout 180; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
                subprocess.run(service + ["start", args.protected_service], check=True, timeout=180)
                # What: execute status restoredHealth wait health args protected url health 300; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
                status["restoredHealth"] = wait_health(args.protected_url + "/health", 300)
                # What: evaluate and capture raw content canary args protected url protected model; why: the enclosing qualifier uses the captured result in its next validation or artifact step.
                raw, content = canary(args.protected_url, protected_model)
                # What: execute artifacts restored json write bytes raw; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
                (artifacts / "restored.json").write_bytes(raw)
                # What: compute status entry from content and 4; why: print restored str status restored flush later reads status entry, so main must retain the computed value under that name.
                status["restored"] = content == "4"
                # What: execute print RESTORED str status restored flush True; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
                print("RESTORED " + str(status["restored"]), flush=True)
            # What: handle exception by status restore error repr exc; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
            except Exception as exc:
                # What: compute status entry from repr and exc; why: artifacts result json write text json dumps status indent later reads status entry, so main must retain the computed value under that name.
                status["restoreError"] = repr(exc)
        # What: preserve the exact artifacts result json write text json dumps status indent literal fragment; why: main passes this fragment verbatim through (artifacts / "result.json").write_text(json.dumps(status, indent=2), enc, because changing it would alter a protocol payload, serialized fixture, or public mess.
        (artifacts / "result.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    # What: return status and 0 and 1 and passed and restored from main; why: main exposes status and 0 and 1 and passed and restored so its caller can continue with the function\'s computed outcome.
    return 0 if status["passed"] and status["restored"] and "cleanupError" not in status else 1


# What: gate on name before exit and sys and main; why: qualify_native_recovery admits exit and sys and main only for this predicate and excludes the opposite state.
if __name__ == "__main__":
    # What: call sys.exit with main; why: qualify_native_recovery invokes sys.exit while performing the enclosing return; the call advances that operation through its result or side effect.
    sys.exit(main())
