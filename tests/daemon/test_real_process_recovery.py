"""Linux CPU integration: real process groups, HTTP probes, and durable recovery.

No model runtime or production endpoint is used. The subprocess below is a small
test HTTP server, not a substitute for the separate GPU qualification gates.
"""
# What: document linux cpu integration real process groups in the test_real_process_recovery docstring; why: introspection and maintainers read this exact docstring fragment to understand test real process recovery behavior without executing it.
# What: document no model runtime or production endpoint in the test_real_process_recovery docstring; why: introspection and maintainers read this exact docstring fragment to understand test real process recovery behavior without executing it.
# What: document test http server not a substitute in the test_real_process_recovery docstring; why: introspection and maintainers read this exact docstring fragment to understand test real process recovery behavior without executing it.
# What: preserve the paragraph boundary in the the test_real_process_recovery docstring; why: introspection and maintainers read this paragraph break to understand test real process recovery behavior without executing it.

# What: import json for json get using json; why: json_get uses json load, making that imported dependency available to its named operation.
import json
# What: import os for test real readiness rollback and process group cleanup using os; why: test_real_readiness_rollback_and_process_group_cleanup uses os killpg, making that imported dependency available to its named operation.
import os
# What: import socket for test real readiness rollback and process group cleanup using socket; why: test_real_readiness_rollback_and_process_group_cleanup uses socket socket, making that imported dependency available to its named operation.
import socket
# What: import subprocess for test native router binds and routes a real readopted child using subprocess; why: test_native_router_binds_and_routes_a_real_readopted_child uses subprocess popen, making that imported dependency available to its named operation.
import subprocess
# What: import sys for module initialization using sys; why: module initialization uses sys platform, making that imported dependency available to its named operation.
import sys
# What: import time for test native router binds and routes a real readopted child using time; why: test_native_router_binds_and_routes_a_real_readopted_child uses time monotonic, making that imported dependency available to its named operation.
import time
# What: import urllib request for json get using urllib and request; why: json_get uses urllib request urlopen, making that imported dependency available to its named operation.
import urllib.request
# What: import thread pool executor for test native router supervises a real child and relays sse using concurrent and futures and thread pool executor; why: test_native_router_supervises_a_real_child_and_relays_sse uses thread pool executor, making that imported dependency available to its named operation.
from concurrent.futures import ThreadPoolExecutor

# What: import pytest for module initialization using pytest; why: module initialization uses pytest mark skipif, making that imported dependency available to its named operation.
import pytest
# What: import test client for test native router uses fresh dynamic ports for real child reactivation using fastapi and testclient and test client; why: test_native_router_uses_fresh_dynamic_ports_for_real_child_reactivation uses test client, making that imported dependency available to its named operation.
from fastapi.testclient import TestClient

# What: import build app for test native router supervises a real child and relays sse using freetoken and daemon and app and build app; why: test_native_router_supervises_a_real_child_and_relays_sse uses build app, making that imported dependency available to its named operation.
from freetoken.daemon.app import build_app
# What: arrange from freetoken daemon catalog import ModelCatalog ModelProfile RouterSettings for the scenario; why: test real process recovery requires this concrete input or helper state before exercising the behavior under test.
from freetoken.daemon.catalog import ModelCatalog, ModelProfile, RouterSettings
# What: import log ring for test real readiness rollback and process group cleanup using freetoken and daemon and logring and log ring; why: test_real_readiness_rollback_and_process_group_cleanup uses log ring, making that imported dependency available to its named operation.
from freetoken.daemon.logring import LogRing
# What: arrange from freetoken daemon pidfile import ServeState ServeStateStore for the scenario; why: test real process recovery requires this concrete input or helper state before exercising the behavior under test.
from freetoken.daemon.pidfile import ServeState, ServeStateStore
# What: import serve probe for test real readiness rollback and process group cleanup using freetoken and daemon and proxy and serve probe; why: test_real_readiness_rollback_and_process_group_cleanup uses serve probe, making that imported dependency available to its named operation.
from freetoken.daemon.proxy import ServeProbe
# What: import wait for ready for test real readiness rollback and process group cleanup using freetoken and daemon and readiness and wait for ready; why: test_real_readiness_rollback_and_process_group_cleanup uses wait for ready, making that imported dependency available to its named operation.
from freetoken.daemon.readiness import wait_for_ready
# What: arrange from freetoken daemon router import RoutingCoordinator for the scenario; why: test real process recovery requires this concrete input or helper state before exercising the behavior under test.
from freetoken.daemon.router import RoutingCoordinator
# What: arrange from freetoken daemon serve manager import AdoptedChild PopenChild ServeManager for the scenario; why: test real process recovery requires this concrete input or helper state before exercising the behavior under test.
from freetoken.daemon.serve_manager import AdoptedChild, PopenChild, ServeManager


# What: act by calling pytest.mark.skipif and capture pytestmark; why: the real process recovery test asserts the response, state, or failure produced by this call.
pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux process-group integration")

# What: arrange server as import and json and os and signal; why: the real process recovery test consumes this named precondition before exercising the behavior.
# What: arrange the exact import json os signal subprocess sys fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact from http server import base httprequest handler httpserver fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact model port resistant sys argv fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact worker subprocess popen sys executable c import time fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact if resistant yes fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact signal signal signal sigterm signal sig ign fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact class handler base httprequest handler fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact def log message args pass fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact def do get fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact if self path health fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact body status error if model bad fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact maintenance serving worker pid worker pid fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact else fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact body requests prompt tokens total completion tokens total fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact uptime s reachable fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact data json dumps body encode fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact self send response fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact self send header content length str len data fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact self end headers fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact self wfile write data fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact def do post fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact if self path v1 chat completions fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact length int self headers get content length fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact request json loads self rfile read length or b fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact body data model s echo s fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact data done n n model json dumps fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact data body encode fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact self send response fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact self send header content type text event stream fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact self send header content length str len data fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact self end headers fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact self wfile write data fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact return fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact self send error fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact httpserver int port handler serve forever fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
# What: arrange the exact the grouped expression fixture fragment; why: the real process recovery scenario feeds this byte-preserved fragment through server before asserting its protocol or parser result.
SERVER = r'''
import json, os, signal, subprocess, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
model, port, resistant = sys.argv[1:]
worker = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
if resistant == "yes":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        if self.path == "/health":
            body = {"status": "error" if model == "bad" else "ok",
                    "maintenance": "serving", "worker_pid": worker.pid}
        else:
            body = {"requests": {"promptTokensTotal": 0, "completionTokensTotal": 0},
                    "uptimeS": 0, "reachable": True}
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def do_POST(self):
        if self.path == "/v1/chat/completions":
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length) or b"{}")
            body = ('data: {"model":"%s","echo":%s}\n\n'
                    'data: [DONE]\n\n') % (model, json.dumps(request.get("model")))
            data = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_error(404)
HTTPServer(("127.0.0.1", int(port)), Handler).serve_forever()
'''


# What: define the json_get test helper around port and path; why: the json get scenario calls this helper to produce or observe the exact behavior checked by its assertions.
def json_get(port, path):
    # What: enter the urllib.request.urlopen managed context before return json load response; why: json_get releases this resource or lock after return json load response on both success and failure paths.
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=2) as response:
        # What: return load and response and json from the json_get test helper; why: the json get scenario uses this helper result in its subsequent act or assertion.
        return json.load(response)


# What: define the running test helper around pid; why: the running scenario calls this helper to produce or observe the exact behavior checked by its assertions.
def running(pid):
    # What: establish the handler boundary for the protected operation; why: running routes failures to file not found error and process lookup error while preserving cleanup and success flow.
    try:
        # Zombies have exited even if the host's init has not reaped them yet.
        # What: enter the open managed context before return source read rsplit split z; why: running releases this resource or lock after return source read rsplit split z on both success and failure paths.
        with open(f"/proc/{pid}/stat") as source:
            # What: return split and rsplit and read and source and z from the running test helper; why: the running scenario uses this helper result in its subsequent act or assertion.
            return source.read().rsplit(")", 1)[1].split()[0] != "Z"
    # What: handle file not found error and process lookup error by return false; why: running converts that failure into this concrete recovery, response, or cleanup behavior.
    except (FileNotFoundError, ProcessLookupError):
        # What: return false from the running test helper; why: the running scenario uses this helper result in its subsequent act or assertion.
        return False


# What: parameterize test_real_readiness_rollback_and_process_group_cleanup with the listed cases; why: pytest reruns the same arrange, act, and assertions for each input protecting test real readiness rollback and process group cleanup.
@pytest.mark.parametrize("resistant", [False, True])
# What: define the test_real_readiness_rollback_and_process_group_cleanup test around tmp path and resistant; why: this test groups the arrange, act, and assertions that protect the real readiness rollback and process group cleanup outcome.
def test_real_readiness_rollback_and_process_group_cleanup(tmp_path, resistant):
    # What: enter the socket.socket managed context before reservation bind; why: test_real_readiness_rollback_and_process_group_cleanup releases this resource or lock after reservation bind on both success and failure paths.
    with socket.socket() as reservation:
        # What: arrange the exact reservation bind fixture fragment; why: the real readiness rollback and process group cleanup scenario feeds this byte-preserved fragment through reservation.bind(("127.0.0.1", 0)) before asserting its protocol or parser result.
        reservation.bind(("127.0.0.1", 0))
        # What: act by calling reservation.getsockname and capture port; why: the real readiness rollback and process group cleanup test asserts the response, state, or failure produced by this call.
        port = reservation.getsockname()[1]
    # What: arrange children as the fixture input; why: the real readiness rollback and process group cleanup test consumes this named precondition before exercising the behavior.
    children = []
    # What: arrange workers as the fixture input; why: the real readiness rollback and process group cleanup test consumes this named precondition before exercising the behavior.
    workers = []

    # What: define the spawn test helper around model and actual port and args; why: the real readiness rollback and process group cleanup scenario calls this helper to produce or observe the exact behavior checked by its assertions.
    def spawn(model, actual_port, args):
        # What: act by calling subprocess.Popen and capture proc; why: the real readiness rollback and process group cleanup test asserts the response, state, or failure produced by this call.
        proc = subprocess.Popen([sys.executable, "-u", "-c", SERVER, model, str(actual_port),
                                 # What: arrange start new session to subprocess.Popen; why: the real readiness rollback and process group cleanup scenario binds this true value to subprocess.Popen's start new session input.
                                 "yes" if resistant else "no"], start_new_session=True,
                                # What: arrange stdin to subprocess.Popen; why: the real readiness rollback and process group cleanup scenario binds this devnull and subprocess value to subprocess.Popen's stdin input.
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                # What: arrange stderr to subprocess.Popen; why: the real readiness rollback and process group cleanup scenario binds this devnull and subprocess value to subprocess.Popen's stderr input.
                                stderr=subprocess.DEVNULL)
        # What: act by calling PopenChild and capture child; why: the real readiness rollback and process group cleanup test asserts the response, state, or failure produced by this call.
        child = PopenChild(proc, None)
        # What: act by calling children.append with child; why: the real readiness rollback and process group cleanup scenario observes the children.append return value during return child.
        children.append(child)
        # What: return child from the spawn test helper; why: the real readiness rollback and process group cleanup scenario uses this helper result in its subsequent act or assertion.
        return child

    # What: act by calling ServeStateStore and capture store; why: the real readiness rollback and process group cleanup test asserts the response, state, or failure produced by this call.
    store = ServeStateStore(str(tmp_path / "serve.json"))
    # What: act by calling ServeManager and capture manager; why: the real readiness rollback and process group cleanup test asserts the response, state, or failure produced by this call.
    manager = ServeManager(LogRing(), store, spawn_fn=spawn, apply_oom=False,
                           # What: arrange grace s to ServeManager; why: the real readiness rollback and process group cleanup scenario binds this 0 2 value to ServeManager's grace s input.
                           grace_s=0.2, reap_wait_s=3,
                           # What: arrange the p input for test_real_readiness_rollback_and_process_group_cleanup; why: test_real_readiness_rollback_and_process_group_cleanup consumes p during signature binding, so callers must bind it with the other signature inputs.
                           read_stats=lambda p: json_get(p, "/v1/stats"))
    # What: act by calling ServeProbe and capture probe; why: the real readiness rollback and process group cleanup test asserts the response, state, or failure produced by this call.
    probe = ServeProbe()
    # What: establish the handler boundary for the protected operation; why: test_real_readiness_rollback_and_process_group_cleanup routes failures to the unconditional cleanup block while preserving cleanup and success flow.
    try:
        # What: act by calling manager.start and capture first; why: the real readiness rollback and process group cleanup test asserts the response, state, or failure produced by this call.
        first = manager.start("good", port, ["original-argument"])
        # What: assert that wait for ready manager probe pid first pid port port timeout s 5; why: this assertion protects the real readiness rollback and process group cleanup regression after the test's arranged inputs and exercised call.
        assert wait_for_ready(manager, probe, pid=first["pid"], port=port, timeout_s=5)["ready"]
        # What: arrange the exact workers append json get port health worker pid fixture fragment; why: the real readiness rollback and process group cleanup scenario feeds this byte-preserved fragment through workers.append(json_get(port, "/health")["worker_pid"]) before asserting its protocol or parser result.
        workers.append(json_get(port, "/health")["worker_pid"])
        # What: act by calling manager.switch_for_readiness and capture replacement and ticket; why: the real readiness rollback and process group cleanup test asserts the response, state, or failure produced by this call.
        replacement, ticket = manager.switch_for_readiness("bad", port)
        # What: act by calling wait_for_ready and capture failed; why: the real readiness rollback and process group cleanup test asserts the response, state, or failure produced by this call.
        failed = wait_for_ready(manager, probe, pid=replacement["pid"], port=port, timeout_s=5)
        # What: assert that failed reason equals engine error; why: this assertion protects the real readiness rollback and process group cleanup regression after the test's arranged inputs and exercised call.
        assert failed["reason"] == "engine-error"
        # What: arrange the exact workers append json get port health worker pid fixture fragment; why: the real readiness rollback and process group cleanup scenario feeds this byte-preserved fragment through workers.append(json_get(port, "/health")["worker_pid"]) before asserting its protocol or parser result.
        workers.append(json_get(port, "/health")["worker_pid"])
        # What: act by calling manager.recover_switch and capture recovery; why: the real readiness rollback and process group cleanup test asserts the response, state, or failure produced by this call.
        recovery = manager.recover_switch(ticket)
        # What: assert that recovery launched; why: this assertion protects the real readiness rollback and process group cleanup regression after the test's arranged inputs and exercised call.
        assert recovery["launched"]
        # What: assert that wait for ready manager probe pid recovery pid port port timeout s 5; why: this assertion protects the real readiness rollback and process group cleanup regression after the test's arranged inputs and exercised call.
        assert wait_for_ready(manager, probe, pid=recovery["pid"], port=port, timeout_s=5)["ready"]
        # What: arrange the exact workers append json get port health worker pid fixture fragment; why: the real readiness rollback and process group cleanup scenario feeds this byte-preserved fragment through workers.append(json_get(port, "/health")["worker_pid"]) before asserting its protocol or parser result.
        workers.append(json_get(port, "/health")["worker_pid"])
        # What: act by calling store.load and capture saved; why: the real readiness rollback and process group cleanup test asserts the response, state, or failure produced by this call.
        saved = store.load()
        # What: assert that saved pid equals recovery pid and saved model equals good; why: this assertion protects the real readiness rollback and process group cleanup regression after the test's arranged inputs and exercised call.
        assert saved.pid == recovery["pid"] and saved.model == "good"
        # What: assert that saved args equals original argument; why: this assertion protects the real readiness rollback and process group cleanup regression after the test's arranged inputs and exercised call.
        assert saved.args == ["original-argument"]
        # What: assert that len manager pending accounting equals 2; why: this assertion protects the real readiness rollback and process group cleanup regression after the test's arranged inputs and exercised call.
        assert len(manager.pending_accounting()) == 2
        # What: act by calling manager.stop with the declared inputs; why: the real readiness rollback and process group cleanup scenario observes the manager.stop return value during assert store load is.
        manager.stop()
        # What: assert that store load is group delimiter; why: this assertion protects the real readiness rollback and process group cleanup regression after the test's arranged inputs and exercised call.
        assert store.load() is None
        # What: assert that all child reaped is set and child proc poll is not for child in children; why: this assertion protects the real readiness rollback and process group cleanup regression after the test's arranged inputs and exercised call.
        assert all(child.reaped.is_set() and child.proc.poll() is not None for child in children)
        # What: assert that all child proc returncode equals 9 if resistant else 15 for child; why: this assertion protects the real readiness rollback and process group cleanup regression after the test's arranged inputs and exercised call.
        assert all(child.proc.returncode == (-9 if resistant else -15) for child in children)
        # What: act by calling time.monotonic and capture deadline; why: the real readiness rollback and process group cleanup test asserts the response, state, or failure produced by this call.
        deadline = time.monotonic() + 3
        # What: act across any and deadline and monotonic and running and pid to perform sleep and time; why: the real readiness rollback and process group cleanup scenario repeats the body only while or for the loop header admits an iteration.
        while any(running(pid) for pid in workers) and time.monotonic() < deadline:
            # What: act by calling time.sleep with 0 05; why: the real readiness rollback and process group cleanup scenario observes the time.sleep return value during assert not any running pid for.
            time.sleep(0.05)
        # What: assert that any running pid for pid in workers is false; why: this assertion protects the real readiness rollback and process group cleanup regression after the test's arranged inputs and exercised call.
        assert not any(running(pid) for pid in workers)
        # What: enter the socket.socket managed context before assert connection connect ex port; why: test_real_readiness_rollback_and_process_group_cleanup releases this resource or lock after assert connection connect ex port on both success and failure paths.
        with socket.socket() as connection:
            # What: assert that connection connect ex 127 0 0 1 port differs from 0; why: this assertion protects the real readiness rollback and process group cleanup regression after the test's arranged inputs and exercised call.
            assert connection.connect_ex(("127.0.0.1", port)) != 0
    # What: run test owned sessions only always clean up on every exit path; why: test_real_readiness_rollback_and_process_group_cleanup performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
    finally:
        # Test-owned sessions only. Always clean up even if an assertion fails.
        # What: act across children to perform process lookup error and killpg and pid and os and child; why: the real readiness rollback and process group cleanup scenario repeats the body only while or for the loop header admits an iteration.
        for child in children:
            # What: establish the handler boundary for the protected operation; why: test_real_readiness_rollback_and_process_group_cleanup routes failures to process lookup error while preserving cleanup and success flow.
            try:
                # What: act by calling os.killpg with pid and child and 9; why: the real readiness rollback and process group cleanup scenario observes the os.killpg return value during except process lookup error.
                os.killpg(child.pid, 9)
            # What: handle process lookup error by pass; why: test_real_readiness_rollback_and_process_group_cleanup converts that failure into this concrete recovery, response, or cleanup behavior.
            except ProcessLookupError:
                # What: ignore the anticipated exception handled by this branch; why: spawn continues its retry or cleanup path instead of re-raising that transient failure.
                pass
            # What: act on poll and proc and child before wait and proc and child; why: the real readiness rollback and process group cleanup scenario admits wait and proc and child only for this predicate and excludes the opposite state.
            if child.proc.poll() is None:
                # What: arrange timeout to child.proc.wait; why: the real readiness rollback and process group cleanup scenario binds this 3 value to child.proc.wait's timeout input.
                child.proc.wait(timeout=3)


# What: define the test_native_router_supervises_a_real_child_and_relays_sse test around tmp path; why: this test groups the arrange, act, and assertions that protect the native router supervises a real child and relays sse outcome.
def test_native_router_supervises_a_real_child_and_relays_sse(tmp_path):
    # What: enter the socket.socket managed context before reservation bind; why: test_native_router_supervises_a_real_child_and_relays_sse releases this resource or lock after reservation bind on both success and failure paths.
    with socket.socket() as reservation:
        # What: arrange the exact reservation bind fixture fragment; why: the native router supervises a real child and relays sse scenario feeds this byte-preserved fragment through reservation.bind(("127.0.0.1", 0)) before asserting its protocol or parser result.
        reservation.bind(("127.0.0.1", 0))
        # What: act by calling reservation.getsockname and capture port; why: the native router supervises a real child and relays sse test asserts the response, state, or failure produced by this call.
        port = reservation.getsockname()[1]
    # What: arrange children as the fixture input; why: the native router supervises a real child and relays sse test consumes this named precondition before exercising the behavior.
    children = []

    # What: define the spawn test helper around model and actual port and args; why: the native router supervises a real child and relays sse scenario calls this helper to produce or observe the exact behavior checked by its assertions.
    def spawn(model, actual_port, args):
        # What: act by calling subprocess.Popen and capture proc; why: the native router supervises a real child and relays sse test asserts the response, state, or failure produced by this call.
        proc = subprocess.Popen(
            # What: act by calling str with actual port; why: the native router supervises a real child and relays sse scenario observes the str return value during start new session stdin subprocess devnull stdout subprocess devnull.
            [sys.executable, "-u", "-c", SERVER, model, str(actual_port), "no"],
            # What: arrange start new session to subprocess.Popen; why: the native router supervises a real child and relays sse scenario binds this true value to subprocess.Popen's start new session input.
            start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            # What: arrange stderr to subprocess.Popen; why: the native router supervises a real child and relays sse scenario binds this devnull and subprocess value to subprocess.Popen's stderr input.
            stderr=subprocess.DEVNULL,
        # What: arrange the grouped source fragment for the scenario; why: test real process recovery test native router supervises a real child and relays sse requires this concrete input or helper state before exercising the behavior under test.
        )
        # What: act by calling PopenChild and capture child; why: the native router supervises a real child and relays sse test asserts the response, state, or failure produced by this call.
        child = PopenChild(proc, None)
        # What: act by calling children.append with child; why: the native router supervises a real child and relays sse scenario observes the children.append return value during return child.
        children.append(child)
        # What: return child from the spawn test helper; why: the native router supervises a real child and relays sse scenario uses this helper result in its subsequent act or assertion.
        return child

    # What: act by calling ServeStateStore and capture store; why: the native router supervises a real child and relays sse test asserts the response, state, or failure produced by this call.
    store = ServeStateStore(str(tmp_path / "serve.json"))
    # What: act by calling ServeManager and capture manager; why: the native router supervises a real child and relays sse test asserts the response, state, or failure produced by this call.
    manager = ServeManager(LogRing(), store, spawn_fn=spawn, apply_oom=False,
                           # What: arrange grace s to ServeManager; why: the native router supervises a real child and relays sse scenario binds this 0 2 value to ServeManager's grace s input.
                           grace_s=0.2, reap_wait_s=3,
                           # What: arrange the p input for test_native_router_supervises_a_real_child_and_relays_sse; why: test_native_router_supervises_a_real_child_and_relays_sse consumes p during signature binding, so callers must bind it with the other signature inputs.
                           read_stats=lambda p: json_get(p, "/v1/stats"))
    # What: act by calling ServeProbe and capture probe; why: the native router supervises a real child and relays sse test asserts the response, state, or failure produced by this call.
    probe = ServeProbe()
    # What: act by calling ModelCatalog and capture catalog; why: the native router supervises a real child and relays sse test asserts the response, state, or failure produced by this call.
    catalog = ModelCatalog(
        # What: arrange the good field as model profile and port and good and good; why: test_native_router_supervises_a_real_child_and_relays_sse carries good through catalog into lifecycle pool lifecycle proxy pool proxy catalog catalog.
        {"good": ModelProfile("good", "good", (), port=port)},
        # What: arrange settings to RouterSettings; why: the native router supervises a real child and relays sse scenario binds this router settings and true value to RouterSettings's settings input.
        settings=RouterSettings(send_loading_state=True),
    # What: arrange the ModelCatalog call with settings; why: test_native_router_supervises_a_real_child_and_relays_sse groups the supplied clauses as one ModelCatalog call before its value is consumed.
    )
    # What: establish the handler boundary for the protected operation; why: test_native_router_supervises_a_real_child_and_relays_sse routes failures to the unconditional cleanup block while preserving cleanup and success flow.
    try:
        # What: enter the ThreadPoolExecutor and ThreadPoolExecutor managed context before app build app; why: test_native_router_supervises_a_real_child_and_relays_sse releases this resource or lock after app build app on both success and failure paths.
        with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(2) as proxy:
            # What: act by calling build_app and capture app; why: the native router supervises a real child and relays sse test asserts the response, state, or failure produced by this call.
            app = build_app(
                # What: arrange the pid input for test_native_router_supervises_a_real_child_and_relays_sse; why: test_native_router_supervises_a_real_child_and_relays_sse consumes pid during signature binding, so callers must bind it with the other signature inputs.
                manager=manager, ring=LogRing(), probe=probe, footprint_fn=lambda pid: {},
                # What: arrange lifecycle pool to build_app; why: the native router supervises a real child and relays sse scenario binds this lifecycle value to build_app's lifecycle pool input.
                lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog,
            # What: arrange the build_app call with manager and ring and probe and footprint fn and lifecycle pool; why: test_native_router_supervises_a_real_child_and_relays_sse groups the supplied clauses as one build_app call before its value is consumed.
            )
            # What: act by calling operation.post and capture response; why: the native router supervises a real child and relays sse test asserts the response, state, or failure produced by this call.
            response = TestClient(app).post(
                # What: arrange the model field as good; why: test_native_router_supervises_a_real_child_and_relays_sse sends this field through response so the router selects the canonical model or alias for upstream dispatch.
                "/v1/chat/completions", json={"model": "good", "stream": True},
            # What: arrange the operation.post call with json; why: test_native_router_supervises_a_real_child_and_relays_sse groups the supplied clauses as one operation.post call before its value is consumed.
            )
        # What: assert that response status code equals 200; why: this assertion protects the native router supervises a real child and relays sse regression after the test's arranged inputs and exercised call.
        assert response.status_code == 200
        # What: assert that b reasoning content freetoken swap loading model good is present in response content; why: this assertion protects the native router supervises a real child and relays sse regression after the test's arranged inputs and exercised call.
        assert b'"reasoning_content":"freetoken-swap loading model: good\\n"' in response.content
        # What: assert that b model good is present in response content; why: this assertion protects the native router supervises a real child and relays sse regression after the test's arranged inputs and exercised call.
        assert b'"model":"good"' in response.content
        # What: assert that response content endswith b data done n n; why: this assertion protects the native router supervises a real child and relays sse regression after the test's arranged inputs and exercised call.
        assert response.content.endswith(b"data: [DONE]\n\n")
        # What: assert that manager status running is true; why: this assertion protects the native router supervises a real child and relays sse regression after the test's arranged inputs and exercised call.
        assert manager.status()["running"] is True
        # What: assert that store load is not group delimiter; why: this assertion protects the native router supervises a real child and relays sse regression after the test's arranged inputs and exercised call.
        assert store.load() is not None
        # What: act by calling manager.stop with the declared inputs; why: the native router supervises a real child and relays sse scenario observes the manager.stop return value during assert store load is.
        manager.stop()
        # What: assert that store load is group delimiter; why: this assertion protects the native router supervises a real child and relays sse regression after the test's arranged inputs and exercised call.
        assert store.load() is None
        # What: assert that children 0 reaped is set; why: this assertion protects the native router supervises a real child and relays sse regression after the test's arranged inputs and exercised call.
        assert children[0].reaped.is_set()
    # What: run for child in children on every exit path; why: test_native_router_supervises_a_real_child_and_relays_sse performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
    finally:
        # What: act across children to perform process lookup error and killpg and pid and os and child; why: the native router supervises a real child and relays sse scenario repeats the body only while or for the loop header admits an iteration.
        for child in children:
            # What: establish the handler boundary for the protected operation; why: test_native_router_supervises_a_real_child_and_relays_sse routes failures to process lookup error while preserving cleanup and success flow.
            try:
                # What: act by calling os.killpg with pid and child and 9; why: the native router supervises a real child and relays sse scenario observes the os.killpg return value during except process lookup error.
                os.killpg(child.pid, 9)
            # What: handle process lookup error by pass; why: test_native_router_supervises_a_real_child_and_relays_sse converts that failure into this concrete recovery, response, or cleanup behavior.
            except ProcessLookupError:
                # What: ignore the anticipated exception handled by this branch; why: spawn continues its retry or cleanup path instead of re-raising that transient failure.
                pass
            # What: act on poll and proc and child before wait and proc and child; why: the native router supervises a real child and relays sse scenario admits wait and proc and child only for this predicate and excludes the opposite state.
            if child.proc.poll() is None:
                # What: arrange timeout to child.proc.wait; why: the native router supervises a real child and relays sse scenario binds this 3 value to child.proc.wait's timeout input.
                child.proc.wait(timeout=3)


# What: define the test_native_router_binds_and_routes_a_real_readopted_child test around tmp path; why: this test groups the arrange, act, and assertions that protect the native router binds and routes a real readopted child outcome.
def test_native_router_binds_and_routes_a_real_readopted_child(tmp_path):
    # What: enter the socket.socket managed context before reservation bind; why: test_native_router_binds_and_routes_a_real_readopted_child releases this resource or lock after reservation bind on both success and failure paths.
    with socket.socket() as reservation:
        # What: arrange the exact reservation bind fixture fragment; why: the native router binds and routes a real readopted child scenario feeds this byte-preserved fragment through reservation.bind(("127.0.0.1", 0)) before asserting its protocol or parser result.
        reservation.bind(("127.0.0.1", 0))
        # What: act by calling reservation.getsockname and capture port; why: the native router binds and routes a real readopted child test asserts the response, state, or failure produced by this call.
        port = reservation.getsockname()[1]
    # What: act by calling subprocess.Popen and capture proc; why: the native router binds and routes a real readopted child test asserts the response, state, or failure produced by this call.
    proc = subprocess.Popen(
        # What: act by calling str with port; why: the native router binds and routes a real readopted child scenario observes the str return value during start new session stdin subprocess devnull stdout subprocess devnull.
        [sys.executable, "-u", "-c", SERVER, "good", str(port), "no"],
        # What: arrange start new session to subprocess.Popen; why: the native router binds and routes a real readopted child scenario binds this true value to subprocess.Popen's start new session input.
        start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        # What: arrange stderr to subprocess.Popen; why: the native router binds and routes a real readopted child scenario binds this devnull and subprocess value to subprocess.Popen's stderr input.
        stderr=subprocess.DEVNULL,
    # What: arrange the subprocess.Popen call with start new session and stdin and stdout and stderr; why: test_native_router_binds_and_routes_a_real_readopted_child groups the supplied clauses as one subprocess.Popen call before its value is consumed.
    )
    # What: act by calling ServeStateStore and capture store; why: the native router binds and routes a real readopted child test asserts the response, state, or failure produced by this call.
    store = ServeStateStore(str(tmp_path / "serve.json"))
    # What: arrange the exact store save serve state model good port port fixture fragment; why: the native router binds and routes a real readopted child scenario feeds this byte-preserved fragment through store.save(ServeState(model="good", port=port, pid=proc.pid, args=["--ad before asserting its protocol or parser.
    store.save(ServeState(model="good", port=port, pid=proc.pid, args=["--adopted"]))
    # What: act by calling ServeProbe and capture probe; why: the native router binds and routes a real readopted child test asserts the response, state, or failure produced by this call.
    probe = ServeProbe()
    # What: act by calling time.monotonic and capture deadline; why: the native router binds and routes a real readopted child test asserts the response, state, or failure produced by this call.
    deadline = time.monotonic() + 5
    # What: act across deadline and monotonic and time to perform oserror and sleep and json get and port and time; why: the native router binds and routes a real readopted child scenario repeats the body only while or for the loop header admits an iteration.
    while time.monotonic() < deadline:
        # What: establish the handler boundary for the protected operation; why: test_native_router_binds_and_routes_a_real_readopted_child routes failures to oserror while preserving cleanup and success flow.
        try:
            # What: act on json get and port before the computed value; why: the native router binds and routes a real readopted child scenario admits the computed value only for this predicate and excludes the opposite state.
            if json_get(port, "/health")["status"] == "ok":
                # What: arrange the break portion of the enclosing predicate; why: this clause remains in the native router binds and routes a real readopted child scenario\'s enclosing expression so its grouping and evaluation order stay intact.
                break
        # What: handle oserror by time sleep 0 05; why: test_native_router_binds_and_routes_a_real_readopted_child converts that failure into this concrete recovery, response, or cleanup behavior.
        except OSError:
            # What: act by calling time.sleep with 0 05; why: the native router binds and routes a real readopted child scenario observes the time.sleep return value during else.
            time.sleep(0.05)
    # What: select the remaining branch that performs raise assertion error test child did not; why: test_native_router_binds_and_routes_a_real_readopted_child covers the state excluded by the preceding predicate without conflating the two outcomes.
    else:
        # What: raise AssertionError for the caller; why: test_native_router_binds_and_routes_a_real_readopted_child stops this rejected path before it can mutate state, dispatch work, or report success.
        raise AssertionError("test child did not become ready")

    # What: act by calling AdoptedChild and capture adopted; why: the native router binds and routes a real readopted child test asserts the response, state, or failure produced by this call.
    adopted = AdoptedChild(
        # What: arrange alive check to running; why: the native router binds and routes a real readopted child scenario binds this running and pid and proc value to running's alive check input.
        proc.pid, port, None, None, alive_check=lambda: running(proc.pid),
        # What: arrange sleep to AdoptedChild; why: the native router binds and routes a real readopted child scenario binds this sleep and time value to AdoptedChild's sleep input.
        sleep=time.sleep, poll_interval=0.05,
    # What: arrange the AdoptedChild call with alive check and sleep and poll interval; why: test_native_router_binds_and_routes_a_real_readopted_child groups the supplied clauses as one AdoptedChild call before its value is consumed.
    )
    # What: act by calling ServeManager and capture manager; why: the native router binds and routes a real readopted child test asserts the response, state, or failure produced by this call.
    manager = ServeManager(
        # What: act by calling LogRing with the declared inputs; why: the native router binds and routes a real readopted child scenario observes the LogRing return value during spawn fn lambda args value for value.
        LogRing(), store,
        # What: arrange the args input for test_native_router_binds_and_routes_a_real_readopted_child; why: test_native_router_binds_and_routes_a_real_readopted_child consumes args during signature binding, so callers must bind it with the other signature inputs.
        spawn_fn=lambda *args: (_ for _ in ()).throw(AssertionError("unexpected second spawn")),
        # What: arrange the state input for test_native_router_binds_and_routes_a_real_readopted_child; why: test_native_router_binds_and_routes_a_real_readopted_child consumes state during signature binding, so callers must bind it with the other signature inputs.
        adopt_fn=lambda state: adopted,
        # What: arrange apply oom to ServeManager; why: the native router binds and routes a real readopted child scenario binds this false value to ServeManager's apply oom input.
        apply_oom=False, grace_s=0.2, reap_wait_s=3,
        # What: arrange the p input for test_native_router_binds_and_routes_a_real_readopted_child; why: test_native_router_binds_and_routes_a_real_readopted_child consumes p during signature binding, so callers must bind it with the other signature inputs.
        read_stats=lambda p: json_get(p, "/v1/stats"),
    # What: arrange the ServeManager call with spawn fn and adopt fn and apply oom and grace s and reap wait s; why: test_native_router_binds_and_routes_a_real_readopted_child groups the supplied clauses as one ServeManager call before its value is consumed.
    )
    # What: act by calling ModelCatalog and capture catalog; why: the native router binds and routes a real readopted child test asserts the response, state, or failure produced by this call.
    catalog = ModelCatalog({
        # What: arrange the good field as model profile and port and good and good and adopted; why: test_native_router_binds_and_routes_a_real_readopted_child carries good through catalog into router routing coordinator manager catalog probe.
        "good": ModelProfile("good", "good", ("--adopted",), port=port),
    # What: arrange the ModelCatalog call with model profile; why: test_native_router_binds_and_routes_a_real_readopted_child groups the supplied clauses as one ModelCatalog call before its value is consumed.
    })
    # What: establish the handler boundary for the protected operation; why: test_native_router_binds_and_routes_a_real_readopted_child routes failures to the unconditional cleanup block while preserving cleanup and success flow.
    try:
        # What: assert that manager readopt is true; why: this assertion protects the native router binds and routes a real readopted child regression after the test's arranged inputs and exercised call.
        assert manager.readopt() is True
        # What: act by calling RoutingCoordinator and capture router; why: the native router binds and routes a real readopted child test asserts the response, state, or failure produced by this call.
        router = RoutingCoordinator(manager, catalog, probe)
        # What: assert that router status active profile equals good; why: this assertion protects the native router binds and routes a real readopted child regression after the test's arranged inputs and exercised call.
        assert router.status()["activeProfile"] == "good"
        # What: assert that router status active identity matches engine is true; why: this assertion protects the native router binds and routes a real readopted child regression after the test's arranged inputs and exercised call.
        assert router.status()["activeIdentityMatchesEngine"] is True
        # What: enter the ThreadPoolExecutor and ThreadPoolExecutor managed context before app build app; why: test_native_router_binds_and_routes_a_real_readopted_child releases this resource or lock after app build app on both success and failure paths.
        with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(2) as proxy:
            # What: act by calling build_app and capture app; why: the native router binds and routes a real readopted child test asserts the response, state, or failure produced by this call.
            app = build_app(
                # What: arrange the pid input for test_native_router_binds_and_routes_a_real_readopted_child; why: test_native_router_binds_and_routes_a_real_readopted_child consumes pid during signature binding, so callers must bind it with the other signature inputs.
                manager=manager, ring=LogRing(), probe=probe, footprint_fn=lambda pid: {},
                # What: arrange lifecycle pool to build_app; why: the native router binds and routes a real readopted child scenario binds this lifecycle value to build_app's lifecycle pool input.
                lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog, router=router,
            # What: arrange the build_app call with manager and ring and probe and footprint fn and lifecycle pool; why: test_native_router_binds_and_routes_a_real_readopted_child groups the supplied clauses as one build_app call before its value is consumed.
            )
            # What: act by calling operation.post and capture response; why: the native router binds and routes a real readopted child test asserts the response, state, or failure produced by this call.
            response = TestClient(app).post(
                # What: arrange the model field as good; why: test_native_router_binds_and_routes_a_real_readopted_child sends this field through response so the router selects the canonical model or alias for upstream dispatch.
                "/v1/chat/completions", json={"model": "good", "stream": True},
            # What: arrange the operation.post call with json; why: test_native_router_binds_and_routes_a_real_readopted_child groups the supplied clauses as one operation.post call before its value is consumed.
            )
        # What: assert that response status code equals 200; why: this assertion protects the native router binds and routes a real readopted child regression after the test's arranged inputs and exercised call.
        assert response.status_code == 200
        # What: assert that response content endswith b data done n n; why: this assertion protects the native router binds and routes a real readopted child regression after the test's arranged inputs and exercised call.
        assert response.content.endswith(b"data: [DONE]\n\n")
        # What: assert that manager status pid equals proc pid and manager status adopted is true; why: this assertion protects the native router binds and routes a real readopted child regression after the test's arranged inputs and exercised call.
        assert manager.status()["pid"] == proc.pid and manager.status()["adopted"] is True
        # What: assert that router status activations equals 0; why: this assertion protects the native router binds and routes a real readopted child regression after the test's arranged inputs and exercised call.
        assert router.status()["activations"] == 0
        # What: act by calling manager.stop with the declared inputs; why: the native router binds and routes a real readopted child scenario observes the manager.stop return value during proc wait timeout.
        manager.stop()
        # What: arrange timeout to proc.wait; why: the native router binds and routes a real readopted child scenario binds this 3 value to proc.wait's timeout input.
        proc.wait(timeout=3)
        # What: assert that store load is group delimiter; why: this assertion protects the native router binds and routes a real readopted child regression after the test's arranged inputs and exercised call.
        assert store.load() is None
    # What: run if proc poll is on every exit path; why: test_native_router_binds_and_routes_a_real_readopted_child performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
    finally:
        # What: act on poll and proc before process lookup error and killpg and pid and os and proc; why: the native router binds and routes a real readopted child scenario admits process lookup error and killpg and pid and os and proc only for this predicate and excludes the opposite state.
        if proc.poll() is None:
            # What: establish the handler boundary for the protected operation; why: test_native_router_binds_and_routes_a_real_readopted_child routes failures to process lookup error while preserving cleanup and success flow.
            try:
                # What: act by calling os.killpg with pid and proc and 9; why: the native router binds and routes a real readopted child scenario observes the os.killpg return value during except process lookup error.
                os.killpg(proc.pid, 9)
            # What: handle process lookup error by pass; why: test_native_router_binds_and_routes_a_real_readopted_child converts that failure into this concrete recovery, response, or cleanup behavior.
            except ProcessLookupError:
                # What: ignore the anticipated exception handled by this branch; why: test_native_router_binds_and_routes_a_real_readopted_child continues its retry or cleanup path instead of re-raising that transient failure.
                pass
            # What: arrange timeout to proc.wait; why: the native router binds and routes a real readopted child scenario binds this 3 value to proc.wait's timeout input.
            proc.wait(timeout=3)


# What: define the test_native_router_uses_fresh_dynamic_ports_for_real_child_reactivation test around tmp path; why: this test groups the arrange, act, and assertions that protect the native router uses fresh dynamic ports for real child reactivation outcome.
def test_native_router_uses_fresh_dynamic_ports_for_real_child_reactivation(tmp_path):
    # What: define the free_port test helper around captured fixture state; why: the native router uses fresh dynamic ports for real child reactivation scenario calls this helper to produce or observe the exact behavior checked by its assertions.
    def free_port():
        # What: enter the socket.socket managed context before reservation bind; why: free_port releases this resource or lock after reservation bind on both success and failure paths.
        with socket.socket() as reservation:
            # What: arrange the exact reservation bind fixture fragment; why: the native router uses fresh dynamic ports for real child reactivation scenario feeds this byte-preserved fragment through reservation.bind(("127.0.0.1", 0)) before asserting its protocol or parser result.
            reservation.bind(("127.0.0.1", 0))
            # What: return getsockname and reservation and 1 from the free_port test helper; why: the native router uses fresh dynamic ports for real child reactivation scenario uses this helper result in its subsequent act or assertion.
            return reservation.getsockname()[1]

    # What: act by calling free_port and capture first port and second port; why: the native router uses fresh dynamic ports for real child reactivation test asserts the response, state, or failure produced by this call.
    first_port, second_port = free_port(), free_port()
    # What: assert that first port differs from second port; why: this assertion protects the native router uses fresh dynamic ports for real child reactivation regression after the test's arranged inputs and exercised call.
    assert first_port != second_port
    # What: arrange children as the fixture input; why: the native router uses fresh dynamic ports for real child reactivation test consumes this named precondition before exercising the behavior.
    children = []

    # What: define the spawn test helper around model and actual port and args; why: the native router uses fresh dynamic ports for real child reactivation scenario calls this helper to produce or observe the exact behavior checked by its assertions.
    def spawn(model, actual_port, args):
        # What: act by calling subprocess.Popen and capture proc; why: the native router uses fresh dynamic ports for real child reactivation test asserts the response, state, or failure produced by this call.
        proc = subprocess.Popen(
            # What: act by calling str with actual port; why: the native router uses fresh dynamic ports for real child reactivation scenario observes the str return value during start new session stdin subprocess devnull stdout subprocess devnull.
            [sys.executable, "-u", "-c", SERVER, model, str(actual_port), "no"],
            # What: arrange start new session to subprocess.Popen; why: the native router uses fresh dynamic ports for real child reactivation scenario binds this true value to subprocess.Popen's start new session input.
            start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            # What: arrange stderr to subprocess.Popen; why: the native router uses fresh dynamic ports for real child reactivation scenario binds this devnull and subprocess value to subprocess.Popen's stderr input.
            stderr=subprocess.DEVNULL,
        # What: arrange the grouped source fragment for the scenario; why: test real process recovery test native router uses fresh dynamic ports for real child reactivation requires this concrete input or helper state before exercising the behavior under test.
        )
        # What: act by calling PopenChild and capture child; why: the native router uses fresh dynamic ports for real child reactivation test asserts the response, state, or failure produced by this call.
        child = PopenChild(proc, None)
        # What: act by calling children.append with child; why: the native router uses fresh dynamic ports for real child reactivation scenario observes the children.append return value during return child.
        children.append(child)
        # What: return child from the spawn test helper; why: the native router uses fresh dynamic ports for real child reactivation scenario uses this helper result in its subsequent act or assertion.
        return child

    # What: act by calling ServeStateStore and capture store; why: the native router uses fresh dynamic ports for real child reactivation test asserts the response, state, or failure produced by this call.
    store = ServeStateStore(str(tmp_path / "serve.json"))
    # What: act by calling ServeManager and capture manager; why: the native router uses fresh dynamic ports for real child reactivation test asserts the response, state, or failure produced by this call.
    manager = ServeManager(LogRing(), store, spawn_fn=spawn, apply_oom=False,
                           # What: arrange grace s to ServeManager; why: the native router uses fresh dynamic ports for real child reactivation scenario binds this 0 2 value to ServeManager's grace s input.
                           grace_s=0.2, reap_wait_s=3,
                           # What: arrange the p input for test_native_router_uses_fresh_dynamic_ports_for_real_child_reactivation; why: test_native_router_uses_fresh_dynamic_ports_for_real_child_reactivation consumes p during signature binding, so callers must bind it with the other signature inputs.
                           read_stats=lambda p: json_get(p, "/v1/stats"))
    # What: act by calling ServeProbe and capture probe; why: the native router uses fresh dynamic ports for real child reactivation test asserts the response, state, or failure produced by this call.
    probe = ServeProbe()
    # What: act by calling ModelCatalog and capture catalog; why: the native router uses fresh dynamic ports for real child reactivation test asserts the response, state, or failure produced by this call.
    catalog = ModelCatalog({"good": ModelProfile("good", "good", (), port=0)})
    # What: act by calling iter and capture ports; why: the native router uses fresh dynamic ports for real child reactivation test asserts the response, state, or failure produced by this call.
    ports = iter((first_port, second_port))
    # What: act by calling RoutingCoordinator and capture router; why: the native router uses fresh dynamic ports for real child reactivation test asserts the response, state, or failure produced by this call.
    router = RoutingCoordinator(manager, catalog, probe, port_allocator=lambda: next(ports))
    # What: establish the handler boundary for the protected operation; why: test_native_router_uses_fresh_dynamic_ports_for_real_child_reactivation routes failures to the unconditional cleanup block while preserving cleanup and success flow.
    try:
        # What: enter the ThreadPoolExecutor and ThreadPoolExecutor managed context before app build app; why: test_native_router_uses_fresh_dynamic_ports_for_real_child_reactivation releases this resource or lock after app build app on both success and failure paths.
        with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(2) as proxy:
            # What: act by calling build_app and capture app; why: the native router uses fresh dynamic ports for real child reactivation test asserts the response, state, or failure produced by this call.
            app = build_app(
                # What: arrange the pid input for test_native_router_uses_fresh_dynamic_ports_for_real_child_reactivation; why: test_native_router_uses_fresh_dynamic_ports_for_real_child_reactivation consumes pid during signature binding, so callers must bind it with the other signature inputs.
                manager=manager, ring=LogRing(), probe=probe, footprint_fn=lambda pid: {},
                # What: arrange lifecycle pool to build_app; why: the native router uses fresh dynamic ports for real child reactivation scenario binds this lifecycle value to build_app's lifecycle pool input.
                lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog, router=router,
            # What: arrange the build_app call with manager and ring and probe and footprint fn and lifecycle pool; why: test_native_router_uses_fresh_dynamic_ports_for_real_child_reactivation groups the supplied clauses as one build_app call before its value is consumed.
            )
            # What: act by calling TestClient and capture client; why: the native router uses fresh dynamic ports for real child reactivation test asserts the response, state, or failure produced by this call.
            client = TestClient(app)
            # What: act by calling client.post and capture first; why: the native router uses fresh dynamic ports for real child reactivation test asserts the response, state, or failure produced by this call.
            first = client.post("/v1/chat/completions", json={"model": "good", "stream": True})
            # What: assert that first status code equals 200; why: this assertion protects the native router uses fresh dynamic ports for real child reactivation regression after the test's arranged inputs and exercised call.
            assert first.status_code == 200
            # What: assert that manager status port equals first port; why: this assertion protects the native router uses fresh dynamic ports for real child reactivation regression after the test's arranged inputs and exercised call.
            assert manager.status()["port"] == first_port
            # What: assert that router evict idle good is true; why: this assertion protects the native router uses fresh dynamic ports for real child reactivation regression after the test's arranged inputs and exercised call.
            assert router.evict_idle("good") is True
            # What: act by calling client.post and capture second; why: the native router uses fresh dynamic ports for real child reactivation test asserts the response, state, or failure produced by this call.
            second = client.post("/v1/chat/completions", json={"model": "good", "stream": True})
        # What: assert that second status code equals 200; why: this assertion protects the native router uses fresh dynamic ports for real child reactivation regression after the test's arranged inputs and exercised call.
        assert second.status_code == 200
        # What: assert that manager status port equals second port; why: this assertion protects the native router uses fresh dynamic ports for real child reactivation regression after the test's arranged inputs and exercised call.
        assert manager.status()["port"] == second_port
        # What: assert that router status activations equals 2; why: this assertion protects the native router uses fresh dynamic ports for real child reactivation regression after the test's arranged inputs and exercised call.
        assert router.status()["activations"] == 2
        # What: assert that len children equals 2 and children 0 reaped is set; why: this assertion protects the native router uses fresh dynamic ports for real child reactivation regression after the test's arranged inputs and exercised call.
        assert len(children) == 2 and children[0].reaped.is_set()
        # What: act by calling manager.stop with the declared inputs; why: the native router uses fresh dynamic ports for real child reactivation scenario observes the manager.stop return value during assert children reaped is set and store load is.
        manager.stop()
        # What: assert that children 1 reaped is set and store load is; why: this assertion protects the native router uses fresh dynamic ports for real child reactivation regression after the test's arranged inputs and exercised call.
        assert children[1].reaped.is_set() and store.load() is None
    # What: run for child in children on every exit path; why: test_native_router_uses_fresh_dynamic_ports_for_real_child_reactivation performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
    finally:
        # What: act across children to perform process lookup error and killpg and pid and os and child; why: the native router uses fresh dynamic ports for real child reactivation scenario repeats the body only while or for the loop header admits an iteration.
        for child in children:
            # What: establish the handler boundary for the protected operation; why: test_native_router_uses_fresh_dynamic_ports_for_real_child_reactivation routes failures to process lookup error while preserving cleanup and success flow.
            try:
                # What: act by calling os.killpg with pid and child and 9; why: the native router uses fresh dynamic ports for real child reactivation scenario observes the os.killpg return value during except process lookup error.
                os.killpg(child.pid, 9)
            # What: handle process lookup error by pass; why: test_native_router_uses_fresh_dynamic_ports_for_real_child_reactivation converts that failure into this concrete recovery, response, or cleanup behavior.
            except ProcessLookupError:
                # What: ignore the anticipated exception handled by this branch; why: spawn continues its retry or cleanup path instead of re-raising that transient failure.
                pass
            # What: act on poll and proc and child before wait and proc and child; why: the native router uses fresh dynamic ports for real child reactivation scenario admits wait and proc and child only for this predicate and excludes the opposite state.
            if child.proc.poll() is None:
                # What: arrange timeout to child.proc.wait; why: the native router uses fresh dynamic ports for real child reactivation scenario binds this 3 value to child.proc.wait's timeout input.
                child.proc.wait(timeout=3)
