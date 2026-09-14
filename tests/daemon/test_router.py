from __future__ import annotations

import threading
import json
import time
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from freetoken.daemon.catalog import ModelCatalog, ModelProfile, RouterSettings, RoutingGroup
from freetoken.daemon.app import build_app
from freetoken.daemon.inference_proxy import UpstreamResponse, filter_request_body
from freetoken.daemon.logring import LogRing
from freetoken.daemon.router import RoutingCoordinator, RoutingError


class Manager:
    def __init__(self):
        self.model = None
        self.port = None
        self.args = []
        self.pid = 100
        self.calls = []

    def status(self):
        return {"running": self.model is not None, "model": self.model, "port": self.port, "pid": self.pid}

    def serve_args(self):
        return list(self.args)

    def start(self, model, port, args):
        self.calls.append(("start", model))
        self.model, self.port, self.args = model, port, list(args)
        self.pid += 1
        return {"pid": self.pid}

    def switch_for_readiness(self, model, port, args):
        self.calls.append(("switch", model))
        previous = self.model, self.port, list(self.args)
        self.model, self.port, self.args = model, port, list(args)
        self.pid += 1
        return {"pid": self.pid}, previous

    def recover_switch(self, ticket):
        self.model, self.port, self.args = ticket
        self.pid += 1
        return {"launched": True, "pid": self.pid}

    def stop(self, timeout):
        self.calls.append(("stop", timeout))
        self.model = None
        return {"stopped": True}


def catalog():
    return ModelCatalog({
        "low": ModelProfile("low", "low.gguf", (), priority=0),
        "high": ModelProfile("high", "high.gguf", (), priority=10),
    })


def ready(manager, probe, *, pid, port, timeout_s):
    return {"ready": True, "health": {"status": "ok"}}


def test_routes_to_ready_engine_then_shares_its_lease():
    manager = Manager()
    router = RoutingCoordinator(manager, catalog(), object(), ready_fn=ready)
    first = router.acquire("low")
    second = router.acquire("low")
    assert manager.calls == [("start", "low.gguf")]
    assert router.status()["activeRequests"] == 2
    second.release()
    first.release()
    assert router.status()["activeRequests"] == 0


def test_unknown_model_is_a_stable_404_router_error():
    with pytest.raises(RoutingError, match="unknown model") as exc:
        RoutingCoordinator(Manager(), catalog(), object(), ready_fn=ready).acquire("missing")
    assert exc.value.code == "unknown_model"
    assert exc.value.status_code == 404


def test_dynamic_profile_port_is_stable_while_resident_and_fresh_after_a_swap():
    manager = Manager()
    catalog_doc = ModelCatalog({
        "dynamic": ModelProfile("dynamic", "dynamic.gguf", (), port=0),
        "other": ModelProfile("other", "other.gguf", (), port=19555),
    })
    allocated = iter([20101, 20102])
    router = RoutingCoordinator(
        manager, catalog_doc, object(), ready_fn=ready, port_allocator=lambda: next(allocated),
    )

    first = router.acquire("dynamic")
    first.release()
    warm = router.acquire("dynamic")
    assert (first.port, warm.port) == (20101, 20101)
    warm.release()
    router.acquire("other").release()
    cold_again = router.acquire("dynamic")
    assert cold_again.port == 20102
    cold_again.release()
    assert manager.calls == [
        ("start", "dynamic.gguf"),
        ("switch", "other.gguf"),
        ("switch", "dynamic.gguf"),
    ]


def test_switch_waits_until_an_active_lease_finishes():
    manager = Manager()
    router = RoutingCoordinator(manager, catalog(), object(), ready_fn=ready)
    lease = router.acquire("low")
    entered = threading.Event()
    released = threading.Event()
    result = []

    def acquire_high():
        entered.set()
        held = router.acquire("high")
        result.append(held)
        released.set()

    thread = threading.Thread(target=acquire_high)
    thread.start()
    assert entered.wait(1)
    assert not released.wait(0.05)
    lease.release()
    assert released.wait(1)
    result.pop().release()
    thread.join(1)
    assert manager.calls == [("start", "low.gguf"), ("switch", "high.gguf")]


def test_queued_higher_priority_profile_runs_before_an_earlier_lower_priority_request():
    manager = Manager()
    catalog_doc = ModelCatalog({
        "active": ModelProfile("active", "active.gguf", (), priority=0),
        "low": ModelProfile("low", "low.gguf", (), priority=0),
        "high": ModelProfile("high", "high.gguf", (), priority=10),
    })
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    active = router.acquire("active")
    completed = []

    def acquire_then_release(name):
        lease = router.acquire(name)
        completed.append(name)
        lease.release()

    low_thread = threading.Thread(target=acquire_then_release, args=("low",))
    high_thread = threading.Thread(target=acquire_then_release, args=("high",))
    low_thread.start()
    for _ in range(100):
        if router.status()["queuedRequests"] == 1:
            break
        threading.Event().wait(0.01)
    assert router.status()["queuedRequests"] == 1
    high_thread.start()
    for _ in range(100):
        if router.status()["queuedRequests"] == 2:
            break
        threading.Event().wait(0.01)
    assert router.status()["queuedRequests"] == 2
    active.release()
    low_thread.join(1)
    high_thread.join(1)
    assert not low_thread.is_alive() and not high_thread.is_alive()
    assert manager.calls == [
        ("start", "active.gguf"),
        ("switch", "high.gguf"),
        ("switch", "low.gguf"),
    ]
    assert completed == ["high", "low"]


def test_failed_readiness_restores_previous_engine_before_reporting_error():
    manager = Manager()
    router = RoutingCoordinator(manager, catalog(), object(), ready_fn=ready)
    router.acquire("low").release()

    def not_ready(manager, probe, *, pid, port, timeout_s):
        return {"ready": False, "reason": "engine-error"}

    router = RoutingCoordinator(manager, catalog(), object(), ready_fn=not_ready)
    with pytest.raises(RoutingError, match="not ready") as exc:
        router.acquire("high")
    assert exc.value.code == "engine_not_ready"
    assert exc.value.recovery["launched"] is True
    assert manager.model == "low.gguf"


def test_ttl_evicts_only_after_final_lease_and_uses_profile_timeout():
    class Timer:
        def __init__(self, delay, callback):
            self.delay = delay
            self.callback = callback
            self.started = False
            self.cancelled = False

        def start(self):
            self.started = True

        def cancel(self):
            self.cancelled = True

    manager = Manager()
    catalog_doc = ModelCatalog({
        "low": ModelProfile("low", "low.gguf", (), ttl_s=12, unload_timeout_s=7),
    })
    timers = []
    router = RoutingCoordinator(
        manager, catalog_doc, object(), ready_fn=ready,
        timer_factory=lambda delay, callback: timers.append(Timer(delay, callback)) or timers[-1],
    )
    first = router.acquire("low")
    second = router.acquire("low")
    first.release()
    assert timers == []
    second.release()
    assert len(timers) == 1
    assert timers[0].delay == 12
    assert timers[0].started is True
    assert router.evict_idle("low") is True
    assert manager.calls == [("start", "low.gguf"), ("stop", 7)]
    assert router.status()["evictions"] == 1


def test_openai_and_anthropic_requests_use_native_router_and_preserve_sse(monkeypatch):
    manager = Manager()
    catalog_doc = ModelCatalog({
        "low": ModelProfile("low", "low.gguf", ()),
    })
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    calls = []

    def upstream(**kwargs):
        calls.append(kwargs)
        return UpstreamResponse(
            status=200,
            headers={"Content-Type": "text/event-stream", "X-Upstream": "yes"},
            raw=BytesIO(b"data: first\\n\\ndata: [DONE]\\n\\n"),
        )

    monkeypatch.setattr("freetoken.daemon.app.open_upstream", upstream)
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        client = TestClient(app)
        for path in ("/v1/chat/completions", "/v1/messages"):
            response = client.post(path, json={"model": "low", "stream": True})
            assert response.status_code == 200
            assert response.content == b"data: first\\n\\ndata: [DONE]\\n\\n"
            assert response.headers["x-upstream"] == "yes"
        status = client.get("/router/status")
        assert status.status_code == 200
        assert status.json()["activeRequests"] == 0
        routed_models = client.get("/router/models").json()
        assert routed_models["data"][0]["resident"] is True
        assert routed_models["capacity"] == {"maxResidentModels": 1, "availableResidentSlots": 0}
        assert client.get("/router/profiles").json()["activeProfile"] == "low"
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert "freetoken_swap_admissions_total 2" in metrics.text
        passthrough = client.get("/upstream/low/v1/models?limit=3")
        assert passthrough.status_code == 200
        blocked = client.post("/upstream/low/v1/admin/prepare-stop")
        assert blocked.status_code == 403
    assert manager.calls == [("start", "low.gguf")]
    assert [item["path_and_query"] for item in calls] == [
        "/v1/chat/completions", "/v1/messages", "/v1/models?limit=3",
    ]
    assert calls[-1]["method"] == "GET"
    assert calls[-1]["timeout_s"] == 900.0
    assert router.status()["activeRequests"] == 0


def test_router_inference_requires_configured_bearer_key():
    manager = Manager()
    catalog_doc = ModelCatalog(
        {"low": ModelProfile("low", "low.gguf", ())},
        settings=RouterSettings(api_keys=("key",)),
    )
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        client = TestClient(app)
        denied = client.post("/v1/chat/completions", json={"model": "low"})
        assert denied.status_code == 401
        assert client.get("/router/status").status_code == 401
        allowed = client.get("/router/status", headers={"Authorization": "Bearer key"})
        assert allowed.status_code == 200
        assert manager.calls == []


def test_router_reload_atomically_replaces_a_valid_catalog(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text("[models.one]\nmodel = 'one.gguf'\n", encoding="utf-8")
    manager = Manager()
    catalog_doc = ModelCatalog.load(str(path))
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
            catalog_path=str(path),
        )
        client = TestClient(app)
        path.write_text("[models.two]\nmodel = 'two.gguf'\n", encoding="utf-8")
        reloaded = client.post("/router/reload")
        assert reloaded.status_code == 200
        assert [item["name"] for item in reloaded.json()["models"]] == ["two"]
        path.write_text("[models.bad]\nmodel = ''\n", encoding="utf-8")
        rejected = client.post("/router/reload")
        assert rejected.status_code == 400
        assert [item["name"] for item in client.get("/models").json()["data"]] == ["two"]


def test_router_reload_rejects_redefining_active_profile():
    manager = Manager()
    router = RoutingCoordinator(manager, catalog(), object(), ready_fn=ready)
    lease = router.acquire("low")
    replacement = ModelCatalog({"low": ModelProfile("low", "changed.gguf", ())})
    with pytest.raises(RoutingError, match="cannot redefine") as exc:
        router.replace_catalog(replacement)
    assert exc.value.status_code == 409
    lease.release()


def test_persistent_group_protects_the_single_resident_slot_until_unloaded():
    manager = Manager()
    catalog_doc = ModelCatalog(
        {
            "keep": ModelProfile("keep", "keep.gguf", (), group="resident"),
            "other": ModelProfile("other", "other.gguf", ()),
        },
        settings=RouterSettings(groups=(
            RoutingGroup("resident", ("keep",), swap=False, persistent=True),
        )),
    )
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    router.acquire("keep").release()
    with pytest.raises(RoutingError, match="single resident-model slot") as exc:
        router.acquire("other")
    assert exc.value.code == "capacity_unavailable"
    assert router.status()["residentProfiles"] == ["keep"]
    assert router.evict_idle("keep") is True
    router.acquire("other").release()
    assert manager.calls == [
        ("start", "keep.gguf"), ("stop", 30.0), ("start", "other.gguf"),
    ]


def test_explicit_router_cancel_closes_an_inflight_upstream(monkeypatch):
    class BlockingRaw:
        def __init__(self):
            self.read_started = threading.Event()
            self.closed = threading.Event()

        def read(self, size):
            self.read_started.set()
            self.closed.wait(2)
            return b""

        def close(self):
            self.closed.set()

    raw = BlockingRaw()
    manager = Manager()
    catalog_doc = ModelCatalog({"low": ModelProfile("low", "low.gguf", ())})
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)

    def upstream(**kwargs):
        return UpstreamResponse(200, {"Content-Type": "text/event-stream"}, raw)

    monkeypatch.setattr("freetoken.daemon.app.open_upstream", upstream)
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        client = TestClient(app)
        response = []
        thread = threading.Thread(target=lambda: response.append(client.post(
            "/v1/chat/completions", json={"model": "low"}, headers={"X-FT-Request-ID": "cancel-me"},
        )))
        thread.start()
        assert raw.read_started.wait(1)
        active = client.get("/router/requests").json()["data"]
        assert active == [{"id": "cancel-me", "profile": "low"}]
        cancelled = client.post("/router/requests/cancel-me/cancel")
        assert cancelled.json() == {"cancelled": True, "id": "cancel-me"}
        thread.join(2)
        assert not thread.is_alive()
    assert response[0].status_code == 200
    assert router.status()["cancellations"] == 1
    assert router.status()["activeRequests"] == 0


def test_native_proxy_uses_a_real_loopback_http_upstream_and_preserves_sse_bytes():
    seen = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            seen["path"] = self.path
            seen["body"] = self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("X-Engine", "loopback")
            self.end_headers()
            self.wfile.write(b"data: {\"ok\":true}\n\ndata: [DONE]\n\n")

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        manager = Manager()
        port = server.server_address[1]
        catalog_doc = ModelCatalog({"low": ModelProfile("low", "low.gguf", (), port=port)})
        router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
        with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
            app = build_app(
                manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
                lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
            )
            payload = b'{"model":"low","stream":true,"messages":[]}'
            response = TestClient(app).post(
                "/v1/chat/completions", content=payload,
                headers={"Content-Type": "application/json"},
            )
        assert response.status_code == 200
        assert response.headers["x-engine"] == "loopback"
        assert response.content == b"data: {\"ok\":true}\n\ndata: [DONE]\n\n"
        assert seen == {"path": "/v1/chat/completions", "body": payload}
        assert router.status()["activeRequests"] == 0
        assert router.status()["terminalStreams"] == 1
        assert router.status()["lastTtftMs"] is not None
        assert router.status()["lastDurationMs"] is not None
        assert "freetoken_swap_last_ttft_ms" in router.prometheus()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(2)


def test_request_filter_is_explicit_top_level_removal_and_default_is_byte_preserving():
    raw = b'{"model":"low", "metadata":{"private":true}, "user":"operator"}'
    assert filter_request_body(raw, ()) == raw
    assert filter_request_body(raw, ("metadata", "user")) == b'{"model":"low"}'


def test_router_event_log_is_bounded_private_and_protected(monkeypatch):
    """Router events are useful operational evidence without retaining prompts or secrets."""
    manager = Manager()
    catalog_doc = ModelCatalog(
        {"low": ModelProfile("low", "low.gguf", ())},
        settings=RouterSettings(api_keys=("router-test-key",)),
    )
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    router_ring = LogRing(capacity=1)

    def upstream(**kwargs):
        return UpstreamResponse(200, {"Content-Type": "application/json"}, BytesIO(b'{"ok":true}'))

    monkeypatch.setattr("freetoken.daemon.app.open_upstream", upstream)
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
            router_ring=router_ring,
        )
        client = TestClient(app)
        assert client.get("/router/logs").status_code == 401
        response = client.post(
            "/upstream/low/private-token-in-path?access_token=do-not-log",
            content=b'{"model":"low","messages":["private prompt"]}',
            headers={"Content-Type": "application/json", "Authorization": "Bearer router-test-key"},
        )
        # A legacy direct lifecycle request must not replace a resident routed
        # child behind the coordinator's lease/residency bookkeeping.
        blocked = client.post("/engine/stop", headers={"Authorization": "Bearer router-test-key"})
    assert response.status_code == 200
    assert blocked.status_code == 409
    assert manager.model == "low.gguf"
    records, cursor = router_ring.since(0)
    assert cursor == 2
    assert len(records) == 1  # the configured bounded ring evicted admission
    events = [json.loads(record["text"]) for record in records]
    assert [event["event"] for event in events] == ["request_finished"]
    assert events[-1]["responseBytes"] == len(b'{"ok":true}')
    serialized = json.dumps(events)
    assert "private prompt" not in serialized
    assert "do-not-log" not in serialized
    assert "private-token-in-path" not in serialized
    assert "router-test-key" not in serialized


def test_invalid_router_request_id_cannot_activate_an_engine(monkeypatch):
    manager = Manager()
    catalog_doc = ModelCatalog({"low": ModelProfile("low", "low.gguf", ())})
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)

    def unexpected_upstream(**kwargs):  # pragma: no cover - establishes the no-activation contract
        raise AssertionError("invalid request ids must be rejected before proxy connection")

    monkeypatch.setattr("freetoken.daemon.app.open_upstream", unexpected_upstream)
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        response = TestClient(app).post(
            "/v1/chat/completions", json={"model": "low"}, headers={"X-FT-Request-ID": "x" * 129},
        )
    assert response.status_code == 400
    assert manager.calls == []


def test_router_management_load_uses_native_admission_and_authentication():
    manager = Manager()
    catalog_doc = ModelCatalog(
        {"low": ModelProfile("low", "low.gguf", (), port=0)},
        settings=RouterSettings(api_keys=("router-test-key",)),
    )
    router = RoutingCoordinator(
        manager, catalog_doc, object(), ready_fn=ready, port_allocator=lambda: 20777,
    )
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        client = TestClient(app)
        assert client.post("/router/load", json={"name": "low"}).status_code == 401
        loaded = client.post(
            "/router/load", json={"name": "low"}, headers={"Authorization": "Bearer router-test-key"},
        )
        missing = client.post(
            "/router/load", json={"name": "missing"}, headers={"Authorization": "Bearer router-test-key"},
        )
    assert loaded.status_code == 200
    assert loaded.json()["profile"] == "low"
    assert loaded.json()["port"] == 20777
    assert loaded.json()["router"]["activeProfile"] == "low"
    assert loaded.json()["router"]["activeRequests"] == 0
    assert missing.status_code == 404
    assert missing.json()["error"]["type"] == "unknown_model"
    assert manager.calls == [("start", "low.gguf")]


def test_router_model_list_hides_model_paths_and_ready_never_cold_loads():
    manager = Manager()
    catalog_doc = ModelCatalog(
        {"low": ModelProfile("low", "/private/models/low.gguf", ())},
        settings=RouterSettings(api_keys=("router-test-key",)),
    )
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)

    class Probe:
        def fresh_health(self, port):
            return {"reachable": True, "status": "ok", "maintenance": "serving"}

    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=Probe(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        client = TestClient(app)
        assert client.get("/ready").status_code == 503
        assert manager.calls == []
        assert client.get("/v1/models").status_code == 401
        listed = client.get("/v1/models", headers={"Authorization": "Bearer router-test-key"})
        router.acquire("low").release()
        assert client.get("/ready").status_code == 200
    assert listed.status_code == 200
    assert listed.json() == {
        "object": "list",
        "data": [{"id": "low", "object": "model", "created": 0, "owned_by": "freetoken"}],
    }


def test_router_management_ui_has_no_embedded_operational_data_and_hardware_is_gated():
    manager = Manager()
    catalog_doc = ModelCatalog(
        {"low": ModelProfile("low", "/private/models/low.gguf", ())},
        settings=RouterSettings(api_keys=("router-test-key",)),
    )
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(),
            footprint_fn=lambda pid: {"ramBytes": 123, "vramBytes": 456},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        client = TestClient(app)
        page = client.get("/ui/")
        assert client.get("/router/hardware").status_code == 401
        hardware = client.get("/router/hardware", headers={"Authorization": "Bearer router-test-key"})
    assert page.status_code == 200
    assert "/router/load" in page.text
    assert "/router/hardware" in page.text
    assert "/private/models/low.gguf" not in page.text
    assert "router-test-key" not in page.text
    assert hardware.json() == {
        "engine": {"running": False, "pid": 100, "port": None},
        "memory": {"ramBytes": 123, "vramBytes": 456},
    }


def test_catalog_watcher_applies_only_valid_idle_replacements(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text("[models.a]\nmodel = 'a.gguf'\n", encoding="utf-8")
    manager = Manager()
    catalog_doc = ModelCatalog.load(str(path))
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)

    def wait_for(client, result):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if client.get("/router/status").json()["catalogWatch"].get("lastResult") == result:
                return
            time.sleep(0.02)
        raise AssertionError(f"catalog watcher did not report {result}")

    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
            catalog_path=str(path), catalog_watch_interval_s=0.01,
        )
        with TestClient(app) as client:
            path.write_text("[models.b]\nmodel = 'b.gguf'\n", encoding="utf-8")
            wait_for(client, "reloaded")
            assert [model["name"] for model in client.get("/router/models").json()["data"]] == ["b"]
            path.write_text("[models.b]\nmodel = [\n", encoding="utf-8")
            wait_for(client, "invalid_catalog")
            assert [model["name"] for model in client.get("/router/models").json()["data"]] == ["b"]
    assert app.state.catalog_watch_stop.is_set()
