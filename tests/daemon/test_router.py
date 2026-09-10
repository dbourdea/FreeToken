from __future__ import annotations

import threading
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from freetoken.daemon.catalog import ModelCatalog, ModelProfile, RouterSettings, RoutingGroup
from freetoken.daemon.app import build_app
from freetoken.daemon.inference_proxy import UpstreamResponse
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
