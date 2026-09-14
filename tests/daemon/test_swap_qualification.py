"""CPU tests of cancellation evidence gates, not real-model qualification."""

import importlib.util
import io
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from freetoken.daemon.catalog import ModelCatalog


@pytest.fixture
def qualifier():
    path = Path(__file__).parents[2] / "benchmarks/swap/qualify.py"
    spec = importlib.util.spec_from_file_location("swap_qualifier", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def native_router_qualifier():
    path = Path(__file__).parents[2] / "benchmarks/swap/qualify_native_router.py"
    spec = importlib.util.spec_from_file_location("native_router_qualifier", path)
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


def test_native_router_benchmark_canary_records_first_byte_and_preserves_sse(native_router_qualifier, monkeypatch):
    stream = io.BytesIO(
        b'data: {"choices":[{"delta":{"content":"4"}}]}\n\n'
        b'data: {"choices":[],"usage":{"completion_tokens":1}}\n\n'
        b"data: [DONE]\n\n"
    )
    monkeypatch.setattr(native_router_qualifier.urllib.request, "urlopen", lambda *a, **k: stream)
    clock = iter([10.0, 10.25, 11.25])
    monkeypatch.setattr(native_router_qualifier.time, "monotonic", lambda: next(clock))

    raw, observation = native_router_qualifier.canary("http://test", "model-a", direct=False)

    assert raw.endswith(b"data: [DONE]\n\n")
    assert observation["route"] == "native_router"
    assert observation["model"] == "model-a"
    assert observation["passed"] is True
    assert observation["firstByteSeconds"] is not None
    assert observation["durationSeconds"] >= observation["firstByteSeconds"]
    assert observation["decodeSeconds"] == 1.0
    assert observation["completionTokens"] == 1
    assert observation["completionTokensPerSecond"] == 1.0
    assert observation["responseBytes"] == len(raw)
    assert stream.closed


def test_native_router_benchmark_rejects_nonterminal_or_wrong_answer_streams(native_router_qualifier, monkeypatch):
    stream = io.BytesIO(b'data: {"choices":[{"delta":{"content":"5"}}]}\n\n')
    monkeypatch.setattr(native_router_qualifier.urllib.request, "urlopen", lambda *a, **k: stream)

    with pytest.raises(RuntimeError):
        native_router_qualifier.canary("http://test", "model-a", direct=True)
    assert stream.closed


def test_native_router_benchmark_rejects_completed_stream_without_usage(native_router_qualifier, monkeypatch):
    stream = io.BytesIO(
        b'data: {"choices":[{"delta":{"content":"4"}}]}\n\n'
        b"data: [DONE]\n\n"
    )
    monkeypatch.setattr(native_router_qualifier.urllib.request, "urlopen", lambda *a, **k: stream)

    with pytest.raises(RuntimeError, match="usage missing"):
        native_router_qualifier.canary("http://test", "model-a", direct=True)
    assert stream.closed


def test_native_router_reload_conflict_canary_preserves_active_identity(
    native_router_qualifier, monkeypatch, tmp_path
):
    def request_json(url, body=None, **kwargs):
        if url.endswith("/router/reload"):
            raise native_router_qualifier.urllib.error.HTTPError(url, 409, "conflict", {}, io.BytesIO())
        assert url.endswith("/router/status")
        return b"{}", {"activeProfile": "model-a", "activeIdentityMatchesEngine": True}

    monkeypatch.setattr(native_router_qualifier, "request_json", request_json)
    catalog = tmp_path / "models.toml"
    observation = native_router_qualifier.reload_conflict_canary(
        "http://test", catalog, "/private/a.gguf", "/private/b.gguf"
    )

    assert observation == {
        "activeProfile": "model-a", "rejectedStatus": 409,
        "activeIdentityPreserved": True, "passed": True,
    }
    assert "priority = 1" in catalog.read_text(encoding="utf-8")


def test_native_router_failed_switch_canary_requires_rollback_and_restored_completion(
    native_router_qualifier, monkeypatch
):
    statuses = iter((
        {
            "activeProfile": "model-a", "activeIdentityMatchesEngine": True,
            "activeRequests": 0, "activationFailures": 3,
        },
        {
            "activeProfile": "model-a", "activeIdentityMatchesEngine": True,
            "activeRequests": 0, "activationFailures": 4,
        },
    ))
    failure = json.dumps({
        "error": {"type": "engine_not_ready", "message": "private failure"},
        "recovery": {"launched": True},
    }).encode()
    pending = iter((
        {"receipts": [{"receiptId": "existing-receipt"}]},
        {"receipts": [
            {"receiptId": "existing-receipt"},
            {"receiptId": "failed-switch-receipt"},
        ]},
    ))

    def request_json(url, body=None, **kwargs):
        if url.endswith("/router/status"):
            return b"{}", next(statuses)
        if url.endswith("/accounting/pending"):
            return b"{}", next(pending)
        assert url.endswith("/router/load") and body == {"name": "model-invalid"}
        raise native_router_qualifier.urllib.error.HTTPError(
            url, 503, "unavailable", {}, io.BytesIO(failure)
        )

    monkeypatch.setattr(native_router_qualifier, "request_json", request_json)
    monkeypatch.setattr(
        native_router_qualifier, "canary",
        lambda base, model, *, direct: (b"data: [DONE]\n\n", {"passed": True}),
    )

    failure_raw, restored_raw, observation = native_router_qualifier.failed_switch_canary(
        "http://test", "model-invalid", "model-a"
    )

    assert failure_raw == failure
    assert restored_raw == b"data: [DONE]\n\n"
    assert observation == {
        "failedProfile": "model-invalid", "restoredProfile": "model-a",
        "failureType": "engine_not_ready", "rollbackLaunched": True,
        "activationFailureIncremented": True, "newAccountingReceiptCount": 1,
        "restoredCompletionPassed": True,
        "passed": True,
    }


def test_native_router_ttl_canary_reloads_temporary_catalog_and_closes_listener(
    native_router_qualifier, monkeypatch, tmp_path
):
    statuses = iter((
        {"evictions": 2, "activeProfile": "model-a"},
        {"evictions": 3, "activeProfile": None},
    ))

    def request_json(url, body=None, **kwargs):
        if url.endswith("/router/status"):
            return b"{}", next(statuses)
        if url.endswith("/router/unload"):
            return b'{"unloaded":true}', {"unloaded": True}
        if url.endswith("/router/reload"):
            return b'{"reloaded":true}', {"reloaded": True}
        assert url.endswith("/router/load") and body == {"name": "model-a"}
        return b'{"profile":"model-a","port":24567}', {"profile": "model-a", "port": 24567}

    closed = []
    monkeypatch.setattr(native_router_qualifier, "request_json", request_json)
    monkeypatch.setattr(native_router_qualifier, "require_listener_closed", closed.append)
    catalog = tmp_path / "models.toml"
    observation = native_router_qualifier.ttl_eviction_canary(
        "http://test", catalog, "/private/a.gguf", "/private/b.gguf", seconds=1
    )

    assert closed == [24567]
    assert observation == {
        "profile": "model-a", "ttlSeconds": 2, "port": 24567,
        "evictionIncremented": True, "listenerClosed": True, "passed": True,
    }
    assert "ttl_s = 2" in catalog.read_text(encoding="utf-8")


def test_native_router_persistent_capacity_canary_requires_release_before_switch(
    native_router_qualifier, monkeypatch, tmp_path
):
    calls = {"model-b": 0}
    rejection = b'{"error":{"type":"capacity_unavailable"}}'

    def request_json(url, body=None, **kwargs):
        if url.endswith("/router/unload"):
            return b"{}", {"unloaded": True}
        if url.endswith("/router/reload"):
            return b"{}", {"reloaded": True}
        if url.endswith("/router/status"):
            return b"{}", {
                "activeProfile": "model-a", "activeIdentityMatchesEngine": True,
                "persistent": True,
            }
        if url.endswith("/engine/status"):
            return b"{}", {"pid": 71}
        assert url.endswith("/router/load")
        if body == {"name": "model-a"}:
            return b"{}", {
                "profile": "model-a", "pid": 71,
                "router": {"persistent": True, "activeIdentityMatchesEngine": True},
            }
        calls["model-b"] += 1
        if calls["model-b"] == 1:
            raise native_router_qualifier.urllib.error.HTTPError(
                url, 409, "capacity", {}, io.BytesIO(rejection)
            )
        return b"{}", {
            "profile": "model-b", "pid": 72,
            "router": {"activeIdentityMatchesEngine": True},
        }

    monkeypatch.setattr(native_router_qualifier, "request_json", request_json)
    catalog = tmp_path / "models.toml"
    raw, observation = native_router_qualifier.persistent_capacity_canary(
        "http://test", catalog, "a.gguf", "b.gguf"
    )

    assert raw == rejection
    assert observation["passed"] is True
    assert observation["residentPidPreserved"] is True
    parsed = ModelCatalog.load(str(catalog))
    assert parsed.group_for("model-a").persistent is True


def test_native_router_concurrent_canaries_require_same_residency(native_router_qualifier, monkeypatch):
    snapshots = iter((
        {"activeProfile": "model-a", "activations": 4, "activeRequests": 0},
        {"activeProfile": "model-a", "activations": 4, "activeRequests": 0},
    ))
    monkeypatch.setattr(native_router_qualifier, "request_json", lambda *a, **k: (b"{}", next(snapshots)))

    def fake_canary(base, model, *, direct):
        assert base == "http://test" and model == "model-a" and direct is False
        time.sleep(0.01)
        return b"data: [DONE]\n\n", {"passed": True}

    monkeypatch.setattr(native_router_qualifier, "canary", fake_canary)
    rows, observation = native_router_qualifier.concurrent_canaries("http://test", "model-a", seconds=2)

    assert len(rows) == 2
    assert observation == {
        "route": "native_router",
        "model": "model-a",
        "requests": 2,
        "activationDelta": 0,
        "activeRequestsAfter": 0,
        "passed": True,
    }


def test_native_router_conflicting_request_canary_queues_then_switches(
    native_router_qualifier, monkeypatch
):
    cancelled = threading.Event()
    statuses = iter((
        {"activeProfile": "model-a", "activations": 10},
        {
            "activeProfile": "model-a", "activations": 10,
            "queuedRequests": 1, "activeRequests": 1,
            "activeIdentityMatchesEngine": True,
        },
        {"activeProfile": "model-b", "activations": 11, "activeRequests": 0},
        {"activeProfile": "model-a", "activations": 12, "activeRequests": 0},
    ))

    class ActiveResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __iter__(self):
            yield b'data: {"choices":[{"delta":{"content":"1"}}]}\n\n'
            cancelled.wait(2)

    def request_json(url, body=None, **kwargs):
        if url.endswith("/router/status"):
            return b"{}", next(statuses)
        assert url.endswith("/router/requests/native-qualification-conflict/cancel")
        cancelled.set()
        return b"{}", {"cancelled": True, "id": "native-qualification-conflict"}

    canary_calls = []

    def fake_canary(base, model, *, direct):
        canary_calls.append(model)
        if model == "model-b":
            cancelled.wait(2)
        return f"data: {model}\n\ndata: [DONE]\n\n".encode(), {"passed": True}

    monkeypatch.setattr(native_router_qualifier, "request_json", request_json)
    monkeypatch.setattr(native_router_qualifier.urllib.request, "urlopen", lambda *a, **k: ActiveResponse())
    monkeypatch.setattr(native_router_qualifier, "canary", fake_canary)

    active, waiting, restored, observation = native_router_qualifier.conflicting_request_canary(
        "http://test", "model-a", "model-b", seconds=2
    )

    assert b"data: [DONE]" not in active
    assert b"model-b" in waiting and b"model-a" in restored
    assert canary_calls == ["model-b", "model-a"]
    assert observation["queuedBehindActive"] is True
    assert observation["activationDelta"] == 2
    assert observation["passed"] is True


def test_native_router_cancellation_canary_requires_idle_without_completion_credit(native_router_qualifier):
    state = {"active": 0, "cancellations": 0, "terminal": 0}
    cancelled = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _json(self, body):
            raw = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            assert self.path == "/router/status"
            self._json({
                "activeRequests": state["active"],
                "cancellations": state["cancellations"],
                "terminalStreams": state["terminal"],
            })

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if self.path == "/v1/chat/completions":
                state["active"] = 1
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(b'data: {"choices":[{"delta":{"content":"1"}}]}\n\n')
                self.wfile.flush()
                cancelled.wait(3)
                state["active"] = 0
                return
            assert self.path == "/router/requests/native-qualification-cancel/cancel"
            state["cancellations"] += 1
            cancelled.set()
            self._json({"cancelled": True, "id": "native-qualification-cancel"})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        raw, observation = native_router_qualifier.cancellation_canary(
            f"http://127.0.0.1:{server.server_port}", "model-a", seconds=3
        )
        assert b'"content":"1"' in raw
        assert b"data: [DONE]" not in raw
        assert observation["passed"] is True
        assert observation["cancellationIncremented"] is True
        assert observation["normalCompletionCredited"] is False
        assert state == {"active": 0, "cancellations": 1, "terminal": 0}
    finally:
        server.shutdown()
        server.server_close()
        worker.join(3)


def test_native_router_benchmark_keeps_prometheus_capture_private_bytes(native_router_qualifier, monkeypatch):
    stream = io.BytesIO(b"freetoken_swap_admissions_total 3\n")
    monkeypatch.setattr(native_router_qualifier.urllib.request, "urlopen", lambda *a, **k: stream)

    assert native_router_qualifier.request_bytes("http://test/metrics") == b"freetoken_swap_admissions_total 3\n"
    assert stream.closed


def test_native_router_credentials_are_scoped_to_the_temporary_origin(
    native_router_qualifier, monkeypatch
):
    requests = []

    def urlopen(request, **kwargs):
        requests.append(request)
        return io.BytesIO(b'{}')

    monkeypatch.setattr(native_router_qualifier.urllib.request, "urlopen", urlopen)
    native_router_qualifier.configure_native_auth("http://native.test:1964", "private-key")

    native_router_qualifier.request_json("http://native.test:1964/router/status")
    native_router_qualifier.request_json("http://protected.test:8000/health")
    native_router_qualifier.request_json("http://native.test:24567/v1/models")

    assert requests[0].get_header("Authorization") == "Bearer private-key"
    assert requests[1].get_header("Authorization") is None
    assert requests[2].get_header("Authorization") is None


def test_native_router_control_plane_canary_requires_auth_and_captures_evidence(
    native_router_qualifier, tmp_path
):
    authorized_paths = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, body, *, content_type="application/json"):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.headers.get("Authorization") != "Bearer private-key":
                self.send_response(401)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            authorized_paths.append(self.path)
            if self.path == "/v1/models":
                body = {"data": [{"id": "model-a"}, {"id": "model-b"}]}
            elif self.path == "/router/models":
                body = {"data": [
                    {"name": "model-a", "resident": True},
                    {"name": "model-b", "resident": False},
                ]}
            elif self.path == "/router/profiles":
                body = {
                    "activeProfile": "model-a",
                    "data": [{"name": "model-a"}, {"name": "model-b"}],
                }
            elif self.path == "/metrics":
                self._send(
                    b"freetoken_swap_admissions_total 1\n",
                    content_type="text/plain; version=0.0.4",
                )
                return
            elif self.path == "/router/logs?since=0":
                self._send(
                    b'event: router\ndata: {"event":"startup"}\n\n'
                    b'event: router\ndata: {"event":"management_loaded"}\n\n',
                    content_type="text/event-stream",
                )
                return
            else:
                self.send_error(404)
                return
            self._send(json.dumps(body).encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    native_router_qualifier.configure_native_auth(base, "private-key")
    try:
        observation = native_router_qualifier.control_plane_canary(base, tmp_path)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(3)

    assert observation["passed"] is True
    assert observation["unauthenticatedControlRejected"] is True
    assert observation["unauthenticatedInferenceRejected"] is True
    assert observation["residentProfile"] == "model-a"
    assert authorized_paths == [
        "/v1/models", "/router/models", "/router/profiles", "/metrics",
        "/router/logs?since=0",
    ]
    assert b"management_loaded" in (tmp_path / "control-router-log.sse").read_bytes()
    assert (tmp_path / "control-metrics.prom").read_bytes().startswith(
        b"freetoken_swap_admissions_total"
    )


def test_native_router_benchmark_validates_warm_and_swap_activation_labels(native_router_qualifier):
    status_a = {"activeProfile": "model-a", "activeRequests": 0, "activations": 1}
    status_b = {"activeProfile": "model-b", "activeRequests": 0, "activations": 2}
    assert native_router_qualifier.validate_routed_trial(
        status_a, alias="model-a", prior_activations=1, expected_delta=0
    ) == 1
    assert native_router_qualifier.validate_routed_trial(
        status_b, alias="model-b", prior_activations=1, expected_delta=1
    ) == 2


def test_native_router_benchmark_captures_private_hardware_observation(
    native_router_qualifier, monkeypatch, tmp_path
):
    captured = b'{"engine":{"running":true,"pid":7,"port":1234},"memory":{"ramBytes":3,"vramBytes":4}}'
    monkeypatch.setattr(native_router_qualifier, "request_json", lambda *a, **k: (captured, {
        "engine": {"running": True, "pid": 7, "port": 1234},
        "memory": {"ramBytes": 3, "vramBytes": 4},
    }))

    hardware = native_router_qualifier.capture_hardware("http://test", tmp_path, "warm-a")

    assert hardware["engine"]["pid"] == 7
    assert (tmp_path / "warm-a.hardware.json").read_bytes() == captured


def test_native_router_benchmark_validates_same_process_re_adoption(native_router_qualifier):
    before = {"running": True, "pid": 41, "port": 24567, "adopted": False}
    after = {"running": True, "pid": 41, "port": 24567, "adopted": True}
    router = {
        "activeProfile": "model-a", "activeIdentityMatchesEngine": True,
        "activations": 0,
    }

    assert native_router_qualifier.validate_re_adoption(before, after, router) == {
        "profile": "model-a", "samePid": True, "samePort": True,
        "managerAdopted": True, "activationDelta": 0,
    }
    with pytest.raises(RuntimeError, match="exact adopted residency"):
        native_router_qualifier.validate_re_adoption(
            before, {**after, "pid": 42}, router
        )


@pytest.mark.parametrize(
    "hardware",
    [
        {"engine": {"running": False, "pid": 7, "port": 1234}, "memory": {"ramBytes": 3, "vramBytes": 4}},
        {"engine": {"running": True, "pid": None, "port": 1234}, "memory": {"ramBytes": 3, "vramBytes": 4}},
        {"engine": {"running": True, "pid": 0, "port": 1234}, "memory": {"ramBytes": 3, "vramBytes": 4}},
        {"engine": {"running": True, "pid": 7, "port": 0}, "memory": {"ramBytes": 3, "vramBytes": 4}},
        {"engine": {"running": True, "pid": 7, "port": 1234}, "memory": {"ramBytes": None, "vramBytes": 4}},
    ],
)
def test_native_router_benchmark_rejects_incomplete_hardware_observation(
    native_router_qualifier, monkeypatch, tmp_path, hardware
):
    monkeypatch.setattr(native_router_qualifier, "request_json", lambda *a, **k: (b"{}", hardware))
    with pytest.raises(RuntimeError):
        native_router_qualifier.capture_hardware("http://test", tmp_path, "bad")


def test_native_router_benchmark_requires_final_engine_listener_to_close(native_router_qualifier):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        with pytest.raises(RuntimeError, match="listener"):
            native_router_qualifier.require_listener_closed(listener.getsockname()[1])
        port = listener.getsockname()[1]
    native_router_qualifier.require_listener_closed(port)


def test_native_router_benchmark_generates_a_valid_dynamic_port_catalog(native_router_qualifier, tmp_path):
    catalog_path = tmp_path / "models.toml"
    catalog_path.write_text(
        native_router_qualifier.native_catalog_text(
            "first.gguf", "second.gguf", api_key="private-key"
        ),
        encoding="utf-8",
    )

    catalog = ModelCatalog.load(str(catalog_path))

    assert catalog.settings.upstream_timeout_s == 660
    assert catalog.settings.api_keys == ("private-key",)
    assert catalog.get("model-a").model == "first.gguf"
    assert catalog.get("model-a").port == 0
    assert catalog.get("model-a").ttl_s == 0
    assert "model-a" in catalog.get("model-a").args
    assert catalog.get("model-b").model == "second.gguf"


@pytest.mark.parametrize(
    "status,alias,prior,delta",
    [
        ({"activeProfile": "model-a", "activeRequests": 1, "activations": 1}, "model-a", 1, 0),
        ({"activeProfile": "model-b", "activeRequests": 0, "activations": 1}, "model-a", 1, 0),
        ({"activeProfile": "model-a", "activeRequests": 0, "activations": 2}, "model-a", 1, 0),
    ],
)
def test_native_router_benchmark_rejects_mislabeled_routed_trials(
    native_router_qualifier, status, alias, prior, delta
):
    with pytest.raises(RuntimeError):
        native_router_qualifier.validate_routed_trial(
            status, alias=alias, prior_activations=prior, expected_delta=delta
        )
