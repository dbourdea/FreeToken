"""Linux CPU integration: real process groups, HTTP probes, and durable recovery.

No model runtime or production endpoint is used. The subprocess below is a small
test HTTP server, not a substitute for the separate GPU qualification gates.
"""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

from freetoken.daemon.logring import LogRing
from freetoken.daemon.pidfile import ServeStateStore
from freetoken.daemon.proxy import ServeProbe
from freetoken.daemon.readiness import wait_for_ready
from freetoken.daemon.serve_manager import PopenChild, ServeManager


pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux process-group integration")

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
HTTPServer(("127.0.0.1", int(port)), Handler).serve_forever()
'''


def json_get(port, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=2) as response:
        return json.load(response)


def running(pid):
    try:
        # Zombies have exited even if the host's init has not reaped them yet.
        with open(f"/proc/{pid}/stat") as source:
            return source.read().rsplit(")", 1)[1].split()[0] != "Z"
    except FileNotFoundError:
        return False


@pytest.mark.parametrize("resistant", [False, True])
def test_real_readiness_rollback_and_process_group_cleanup(tmp_path, resistant):
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    children = []
    workers = []

    def spawn(model, actual_port, args):
        proc = subprocess.Popen([sys.executable, "-u", "-c", SERVER, model, str(actual_port),
                                 "yes" if resistant else "no"], start_new_session=True,
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        child = PopenChild(proc, None)
        children.append(child)
        return child

    store = ServeStateStore(str(tmp_path / "serve.json"))
    manager = ServeManager(LogRing(), store, spawn_fn=spawn, apply_oom=False,
                           grace_s=0.2, reap_wait_s=3,
                           read_stats=lambda p: json_get(p, "/v1/stats"))
    probe = ServeProbe()
    try:
        first = manager.start("good", port, ["original-argument"])
        assert wait_for_ready(manager, probe, pid=first["pid"], port=port, timeout_s=5)["ready"]
        workers.append(json_get(port, "/health")["worker_pid"])
        replacement, ticket = manager.switch_for_readiness("bad", port)
        failed = wait_for_ready(manager, probe, pid=replacement["pid"], port=port, timeout_s=5)
        assert failed["reason"] == "engine-error"
        workers.append(json_get(port, "/health")["worker_pid"])
        recovery = manager.recover_switch(ticket)
        assert recovery["launched"]
        assert wait_for_ready(manager, probe, pid=recovery["pid"], port=port, timeout_s=5)["ready"]
        workers.append(json_get(port, "/health")["worker_pid"])
        saved = store.load()
        assert saved.pid == recovery["pid"] and saved.model == "good"
        assert saved.args == ["original-argument"]
        assert len(manager.pending_accounting()) == 2
        manager.stop()
        assert store.load() is None
        assert all(child.reaped.is_set() and child.proc.poll() is not None for child in children)
        deadline = time.monotonic() + 3
        while any(running(pid) for pid in workers) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not any(running(pid) for pid in workers)
        with socket.socket() as connection:
            assert connection.connect_ex(("127.0.0.1", port)) != 0
    finally:
        # Test-owned sessions only. Always clean up even if an assertion fails.
        for child in children:
            if child.proc.poll() is None:
                os.killpg(child.pid, 9)
                child.proc.wait(timeout=3)
