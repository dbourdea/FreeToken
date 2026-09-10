"""CPU tests of cancellation evidence gates, not real-model qualification."""

import importlib.util
import io
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


@pytest.fixture
def qualifier():
    path = Path(__file__).parents[2] / "benchmarks/swap/qualify.py"
    spec = importlib.util.spec_from_file_location("swap_qualifier", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stats(active, *, instance="same", completed=3):
    return {"instance_id": instance, "requests": {"active": active, "completed": completed}}


@pytest.mark.parametrize("outcome", ["abort", "restart", "completion", "already-done", "timeout"])
def test_cancellation_requires_terminal_abort_without_restart(qualifier, monkeypatch, outcome):
    stream = io.BytesIO(b'data: {"choices":[{"delta":{"content":"1"}}]}\n\n')
    monkeypatch.setattr(qualifier.urllib.request, "urlopen", lambda *a, **k: stream)
    during = stats(0 if outcome == "already-done" else 1)
    after = stats(1 if outcome == "timeout" else 0,
                  instance="new" if outcome == "restart" else "same",
                  completed=4 if outcome == "completion" else 3)
    snapshots = iter([stats(0), during, after])
    monkeypatch.setattr(qualifier, "http", lambda *a, **k: json.dumps(next(snapshots)).encode())
    if outcome == "abort":
        prefix, evidence = qualifier.cancellation_canary("http://test", "model-a", seconds=0)
        assert evidence["passed"]
        assert b'"content":"1"' in prefix
    elif outcome == "timeout":
        with pytest.raises(TimeoutError, match="terminal abort"):
            qualifier.cancellation_canary("http://test", "model-a", seconds=0)
    else:
        with pytest.raises(AssertionError):
            qualifier.cancellation_canary("http://test", "model-a", seconds=0)
    assert stream.closed


@pytest.mark.parametrize("body", [b"data: [DONE]\n\n", b"", b": heartbeat\n\n"])
def test_completed_or_empty_stream_is_not_cancellation(qualifier, monkeypatch, body):
    stream = io.BytesIO(body)
    monkeypatch.setattr(qualifier.urllib.request, "urlopen", lambda *a, **k: stream)
    monkeypatch.setattr(qualifier, "http", lambda *a, **k: json.dumps(stats(0)).encode())
    with pytest.raises(RuntimeError):
        qualifier.cancellation_canary("http://test", "model-a")
    assert stream.closed


def test_cancellation_closes_real_local_http_stream(qualifier):
    """Exercise the HTTP transport too, using a CPU-only streaming backend."""
    state = {"active": 0}
    disconnected = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            body = json.dumps(stats(state["active"])).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            state["active"] = 1
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            try:
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    self.wfile.write(b'data: {"choices":[{"delta":{"content":"1"}}]}\n\n')
                    self.wfile.flush()
                    time.sleep(0.01)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                disconnected.set()
                state["active"] = 0

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        _, evidence = qualifier.cancellation_canary(
            f"http://127.0.0.1:{server.server_port}", "model-a", seconds=3
        )
        assert evidence["passed"] and disconnected.is_set()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(3)
