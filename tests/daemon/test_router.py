from __future__ import annotations

import asyncio
import base64
import threading
import json
import time
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import httpx
from fastapi.testclient import TestClient

from freetoken.daemon.catalog import ModelCatalog, ModelProfile, RouterSettings, RoutingGroup
from freetoken.daemon.app import build_app
from freetoken.daemon.inference_proxy import (
    UpstreamResponse,
    filter_request_body,
    forward_headers,
    response_headers,
)
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


@pytest.mark.parametrize("configured_port", [1919, 0, None])
def test_router_binds_unambiguous_exact_manager_re_adoption(configured_port):
    manager = Manager()
    manager.model = "adopted.gguf"
    manager.port = 1919
    manager.args = ["--served-model-name", "adopted"]
    catalog_doc = ModelCatalog({
        "adopted": ModelProfile(
            "adopted", "adopted.gguf", tuple(manager.args), port=configured_port
        ),
    })

    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    assert router.status()["activeProfile"] == "adopted"
    assert router.status()["activeIdentityMatchesEngine"] is True
    lease = router.acquire("adopted")
    lease.release()
    assert manager.calls == []
    assert router.status()["activations"] == 0


def test_router_refuses_ambiguous_or_argument_mismatched_re_adoption():
    manager = Manager()
    manager.model = "shared.gguf"
    manager.port = 1919
    manager.args = ["--actual"]
    ambiguous = ModelCatalog({
        "one": ModelProfile("one", "shared.gguf", tuple(manager.args), port=0),
        "two": ModelProfile("two", "shared.gguf", tuple(manager.args), port=0),
    })
    mismatched = ModelCatalog({
        "one": ModelProfile("one", "shared.gguf", ("--different",), port=1919),
    })

    assert RoutingCoordinator(manager, ambiguous, object(), ready_fn=ready).status()["activeProfile"] is None
    assert RoutingCoordinator(manager, mismatched, object(), ready_fn=ready).status()["activeProfile"] is None


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


def test_cancelled_queued_http_request_cannot_trigger_a_later_swap(monkeypatch):
    manager = Manager()
    router = RoutingCoordinator(manager, catalog(), object(), ready_fn=ready)
    active = router.acquire("low")
    monkeypatch.setattr(
        "freetoken.daemon.app.open_upstream",
        lambda **kwargs: pytest.fail("cancelled queued request reached upstream"),
    )

    async def scenario(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            request = asyncio.create_task(client.post(
                "/v1/chat/completions", json={"model": "high"},
                headers={"X-FT-Request-ID": "cancelled-while-queued"},
            ))
            for _ in range(100):
                if router.status()["queuedRequests"] == 1:
                    break
                await asyncio.sleep(0.01)
            assert router.status()["queuedRequests"] == 1
            request.cancel()
            with pytest.raises(asyncio.CancelledError):
                await request
            for _ in range(100):
                if router.status()["queuedRequests"] == 0:
                    break
                await asyncio.sleep(0.01)
            assert router.status()["queuedRequests"] == 0
            assert (await client.get("/router/requests")).json()["data"] == []
            retry = await client.post(
                "/v1/chat/completions", json={"model": "missing"},
                headers={"X-FT-Request-ID": "cancelled-while-queued"},
            )
            assert retry.status_code == 404
            assert retry.json()["error"]["type"] == "unknown_model"

    with ThreadPoolExecutor(2) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog(), router=router,
        )
        asyncio.run(scenario(app))

    active.release()
    assert manager.calls == [("start", "low.gguf")]
    assert router.status()["cancellations"] == 1
    assert router.status()["activeRequests"] == 0


def test_default_profile_concurrency_limit_is_shared_by_alternate_ids():
    manager = Manager()
    profile = ModelProfile("low", "low.gguf", (), aliases=("alternate",))
    router = RoutingCoordinator(
        manager, ModelCatalog({"low": profile}), object(), ready_fn=ready
    )
    leases = [router.acquire("low") for _ in range(10)]

    with pytest.raises(RoutingError, match="concurrency limit") as exc:
        router.acquire("alternate")
    assert exc.value.status_code == 429
    assert exc.value.code == "concurrency_limit"
    assert router.status()["reservedRequests"] == 10
    assert router.status()["queuedRequests"] == 0

    leases[0].release()
    replacement = router.acquire("alternate")
    with pytest.raises(ValueError, match="already released"):
        leases[0].release()
    assert router.status()["reservedRequests"] == 10
    replacement.release()
    for lease in leases[1:]:
        lease.release()
    assert router.status()["reservedRequests"] == 0
    assert manager.calls == [("start", "low.gguf")]


def test_global_concurrency_limit_rejects_conflicting_model_before_it_queues():
    manager = Manager()
    catalog_doc = ModelCatalog(
        {
            "low": ModelProfile("low", "low.gguf", ()),
            "high": ModelProfile("high", "high.gguf", ()),
        },
        settings=RouterSettings(global_concurrency_limit=1),
    )
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    lease = router.acquire("low")

    with pytest.raises(RoutingError) as exc:
        router.acquire("high")
    assert (exc.value.code, exc.value.status_code) == ("concurrency_limit", 429)
    assert router.status()["queuedRequests"] == 0
    assert router.status()["reservedRequests"] == 1
    lease.release()


def test_http_concurrency_rejection_returns_retry_after_and_releases_request_id(monkeypatch):
    manager = Manager()
    profile = ModelProfile("low", "low.gguf", (), concurrency_limit=1)
    catalog_doc = ModelCatalog({"low": profile})
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    lease = router.acquire("low")
    monkeypatch.setattr(
        "freetoken.daemon.app.open_upstream",
        lambda **kwargs: pytest.fail("over-limit request reached upstream"),
    )

    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        client = TestClient(app)
        rejected = client.post(
            "/v1/messages",
            json={"model": "low", "messages": []},
            headers={"X-FT-Request-ID": "over-limit"},
        )
        assert client.get("/router/requests").json()["data"] == []

    assert rejected.status_code == 429
    assert rejected.headers["retry-after"] == "1"
    assert rejected.json()["error"]["type"] == "concurrency_limit"
    assert router.status()["reservedRequests"] == 1
    lease.release()


def test_dynamic_port_failure_releases_concurrency_reservation():
    router = RoutingCoordinator(
        Manager(),
        ModelCatalog({"dynamic": ModelProfile("dynamic", "dynamic.gguf", (), port=0)}),
        object(),
        ready_fn=ready,
        port_allocator=lambda: (_ for _ in ()).throw(OSError("no port")),
    )

    with pytest.raises(OSError, match="no port"):
        router.acquire("dynamic")
    assert router.status()["reservedRequests"] == 0
    assert router.status()["queuedRequests"] == 0


def test_concurrent_cold_dynamic_requests_share_one_head_ticket_port():
    manager = Manager()
    activation_started = threading.Event()
    finish_activation = threading.Event()
    allocated = []

    def allocate():
        port = 21000 + len(allocated)
        allocated.append(port)
        return port

    def blocking_ready(manager, probe, *, pid, port, timeout_s):
        activation_started.set()
        assert finish_activation.wait(2)
        return {"ready": True}

    router = RoutingCoordinator(
        manager,
        ModelCatalog({"dynamic": ModelProfile("dynamic", "dynamic.gguf", (), port=0)}),
        object(),
        ready_fn=blocking_ready,
        port_allocator=allocate,
    )
    leases = []
    first = threading.Thread(target=lambda: leases.append(router.acquire("dynamic")))
    second = threading.Thread(target=lambda: leases.append(router.acquire("dynamic")))
    first.start()
    assert activation_started.wait(1)
    second.start()
    for _ in range(100):
        if router.status()["queuedRequests"] == 1:
            break
        time.sleep(0.01)
    assert router.status()["queuedRequests"] == 1
    finish_activation.set()
    first.join(2)
    second.join(2)

    assert not first.is_alive() and not second.is_alive()
    assert allocated == [21000]
    assert [lease.port for lease in leases] == [21000, 21000]
    assert manager.calls == [("start", "dynamic.gguf")]
    for lease in leases:
        lease.release()


def test_explicit_cancel_removes_a_queued_request_before_it_can_swap(monkeypatch):
    manager = Manager()
    router = RoutingCoordinator(manager, catalog(), object(), ready_fn=ready)
    active = router.acquire("low")
    monkeypatch.setattr(
        "freetoken.daemon.app.open_upstream",
        lambda **kwargs: pytest.fail("cancelled queued request reached upstream"),
    )

    async def scenario(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            request = asyncio.create_task(client.post(
                "/v1/chat/completions", json={"model": "high"},
                headers={"X-FT-Request-ID": "operator-cancelled-queue"},
            ))
            for _ in range(100):
                if router.status()["queuedRequests"] == 1:
                    break
                await asyncio.sleep(0.01)
            assert router.status()["queuedRequests"] == 1
            assert (await client.get("/router/requests")).json()["data"] == [
                {"id": "operator-cancelled-queue", "profile": "high"}
            ]
            cancelled = await client.post(
                "/router/requests/operator-cancelled-queue/cancel"
            )
            assert cancelled.json() == {
                "cancelled": True, "id": "operator-cancelled-queue"
            }
            repeated = await client.post(
                "/router/requests/operator-cancelled-queue/cancel"
            )
            assert repeated.json() == {"cancelled": False, "reason": "not_found"}
            response = await asyncio.wait_for(request, 1)
            assert response.status_code == 409
            assert response.json()["error"]["type"] == "request_cancelled"
            assert (await client.get("/router/requests")).json()["data"] == []

    with ThreadPoolExecutor(2) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog(), router=router,
        )
        asyncio.run(scenario(app))

    active.release()
    assert manager.calls == [("start", "low.gguf")]
    assert router.status()["queuedRequests"] == 0
    assert router.status()["activeRequests"] == 0
    assert router.status()["cancellations"] == 1


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
    assert router.status()["activatingProfile"] is None
    _, loaded_profiles = router.model_listing_snapshot()
    assert loaded_profiles == frozenset({"low"})
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


def test_all_supported_openai_and_anthropic_requests_use_native_router_and_preserve_sse(monkeypatch):
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
            headers={
                "Content-Type": "text/event-stream", "X-Upstream": "yes",
                "Connection": "keep-alive", "Keep-Alive": "timeout=5",
                "Transfer-Encoding": "chunked", "Content-Length": "999",
            },
            raw=BytesIO(b"data: first\\n\\ndata: [DONE]\\n\\n"),
        )

    monkeypatch.setattr("freetoken.daemon.app.open_upstream", upstream)
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        client = TestClient(app)
        for path in (
            "/v1/chat/completions",
            "/v1/completions",
            "/v1/responses",
            "/v1/messages",
            "/v1/messages/count_tokens",
        ):
            response = client.post(path, json={"model": "low", "stream": True})
            assert response.status_code == 200
            assert response.content == b"data: first\\n\\ndata: [DONE]\\n\\n"
            assert response.headers["x-upstream"] == "yes"
            assert "connection" not in response.headers
            assert "keep-alive" not in response.headers
            assert "transfer-encoding" not in response.headers
            assert "content-length" not in response.headers
        status = client.get("/router/status")
        assert status.status_code == 200
        assert status.json()["activeRequests"] == 0
        routed_models = client.get("/router/models").json()
        assert routed_models["data"][0]["resident"] is True
        assert routed_models["capacity"] == {"maxResidentModels": 1, "availableResidentSlots": 0}
        assert client.get("/router/profiles").json()["activeProfile"] == "low"
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert "freetoken_swap_admissions_total 5" in metrics.text
        passthrough = client.get("/upstream/low/v1/models?limit=3")
        assert passthrough.status_code == 200
        legacy_body = b'{"prompt":"fixture","max_tokens":2}'
        assert client.post("/generate", content=legacy_body).status_code == 404
        legacy = client.post(
            "/upstream/low/generate", content=legacy_body,
            headers={"Content-Type": "application/json"},
        )
        assert legacy.status_code == 200
        assert legacy.content == response.content
        blocked = client.post("/upstream/low/v1/admin/prepare-stop")
        assert blocked.status_code == 403
    assert manager.calls == [("start", "low.gguf")]
    assert [item["path_and_query"] for item in calls] == [
        "/v1/chat/completions", "/v1/completions", "/v1/responses",
        "/v1/messages", "/v1/messages/count_tokens", "/v1/models?limit=3", "/generate",
    ]
    assert calls[-2]["method"] == "GET"
    assert calls[-1]["method"] == "POST"
    assert calls[-1]["body"] == legacy_body
    assert calls[-1]["timeout_s"] == 900.0
    assert router.status()["activeRequests"] == 0


@pytest.mark.parametrize(
    "path",
    (
        "/v1/chat/completions",
        "/v1/completions",
        "/v1/responses",
        "/v1/messages",
        "/v1/messages/count_tokens",
    ),
)
def test_all_routed_text_endpoints_share_stable_unknown_model_error(path, monkeypatch):
    manager = Manager()
    catalog_doc = ModelCatalog({"known": ModelProfile("known", "known.gguf", ())})
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    monkeypatch.setattr(
        "freetoken.daemon.app.open_upstream",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("unknown model reached upstream")),
    )
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        client = TestClient(app)
        response = client.post(
            path, json={"model": "missing"}, headers={"X-FT-Request-ID": "reusable-failure"}
        )
        repeated = client.post(
            path, json={"model": "missing"}, headers={"X-FT-Request-ID": "reusable-failure"}
        )

    assert response.status_code == 404
    assert response.json()["error"]["type"] == "unknown_model"
    assert "missing" in response.json()["error"]["message"]
    assert repeated.status_code == 404
    assert repeated.json()["error"]["type"] == "unknown_model"
    assert manager.calls == []


def test_router_preserves_upstream_error_status_headers_and_body(monkeypatch):
    manager = Manager()
    catalog_doc = ModelCatalog({"low": ModelProfile("low", "low.gguf", ())})
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)

    def upstream(**kwargs):
        assert kwargs["path_and_query"] == "/v1/responses"
        return UpstreamResponse(
            status=429,
            headers={"Content-Type": "application/json", "Retry-After": "2", "Content-Length": "999"},
            raw=BytesIO(b'{"error":{"message":"busy"}}'),
        )

    monkeypatch.setattr("freetoken.daemon.app.open_upstream", upstream)
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        response = TestClient(app).post("/v1/responses", json={"model": "low", "input": "private"})

    assert response.status_code == 429
    assert response.headers["retry-after"] == "2"
    assert response.content == b'{"error":{"message":"busy"}}'
    assert "content-length" not in response.headers
    assert router.status()["activeRequests"] == 0
    assert router.status()["terminalStreams"] == 1


def test_failed_upstream_connect_releases_lease_and_request_id_reservation(monkeypatch):
    manager = Manager()
    catalog_doc = ModelCatalog({"low": ModelProfile("low", "low.gguf", ())})
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    monkeypatch.setattr(
        "freetoken.daemon.app.open_upstream",
        lambda **kwargs: (_ for _ in ()).throw(OSError("fixture unavailable")),
    )
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        client = TestClient(app)
        responses = [
            client.post(
                "/v1/chat/completions", json={"model": "low"},
                headers={"X-FT-Request-ID": "retry-after-connect-failure"},
            )
            for _ in range(2)
        ]

    assert [response.status_code for response in responses] == [502, 502]
    assert all(response.json()["error"]["type"] == "upstream_unavailable" for response in responses)
    assert router.status()["activeRequests"] == 0
    assert router.status()["admissions"] == 2


def test_alias_routes_to_canonical_residency_and_model_list_respects_visibility(monkeypatch):
    manager = Manager()
    catalog_doc = ModelCatalog(
        {
            "canonical": ModelProfile(
                "canonical", "shared.gguf", (), aliases=("compat-id",)
            ),
            "hidden": ModelProfile(
                "hidden", "hidden.gguf", (), aliases=("private-id",), unlisted=True
            ),
        },
        settings=RouterSettings(include_aliases_in_list=True),
    )
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    calls = []

    def upstream(**kwargs):
        calls.append(kwargs)
        return UpstreamResponse(
            status=200,
            headers={"Content-Type": "application/json"},
            raw=BytesIO(b'{"ok":true}'),
        )

    monkeypatch.setattr("freetoken.daemon.app.open_upstream", upstream)
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        client = TestClient(app)
        listed = client.get("/v1/models")
        alias_response = client.post(
            "/v1/chat/completions", content=b'{"model":"compat-id","max_tokens":1}',
            headers={"Content-Type": "application/json"},
        )
        loaded = client.get("/v1/models")
        canonical_response = client.post(
            "/v1/chat/completions", json={"model": "canonical", "max_tokens": 1}
        )
        hidden_response = client.post(
            "/v1/chat/completions", json={"model": "private-id", "max_tokens": 1}
        )
        unloaded = client.post("/router/unload", json={"name": "private-id"})

    listed_data = listed.json()["data"]
    assert [item["id"] for item in listed_data] == ["canonical", "compat-id"]
    assert {item["status"]["value"] for item in listed_data} == {"unloaded"}
    loaded_data = loaded.json()["data"]
    assert {item["id"]: item["status"]["value"] for item in loaded_data} == {
        "canonical": "loaded", "compat-id": "loaded",
    }
    assert alias_response.status_code == canonical_response.status_code == 200
    assert hidden_response.status_code == 200
    assert unloaded.json()["unloaded"] is True
    assert manager.calls == [
        ("start", "shared.gguf"),
        ("switch", "hidden.gguf"),
        ("stop", 30.0),
    ]
    assert calls[0]["body"] == b'{"model":"compat-id","max_tokens":1}'
    assert router.status()["activeProfile"] is None


def test_openai_model_list_reports_canonical_and_alias_loaded_while_activating():
    manager = Manager()
    activation_started = threading.Event()
    finish_activation = threading.Event()
    catalog_doc = ModelCatalog(
        {"canonical": ModelProfile(
            "canonical", "shared.gguf", (), aliases=("compat-id",)
        )},
        settings=RouterSettings(include_aliases_in_list=True),
    )

    def blocking_ready(manager, probe, *, pid, port, timeout_s):
        activation_started.set()
        assert finish_activation.wait(2)
        return {"ready": True, "health": {"status": "ok"}}

    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=blocking_ready)
    with (
        ThreadPoolExecutor(1) as activation,
        ThreadPoolExecutor(1) as lifecycle,
        ThreadPoolExecutor(1) as proxy,
    ):
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        client = TestClient(app)
        future = activation.submit(router.acquire, "compat-id")
        assert activation_started.wait(2)
        try:
            status = client.get("/router/status").json()
            listed = client.get("/v1/models").json()["data"]
        finally:
            finish_activation.set()
        lease = future.result(timeout=2)
        lease.release()

    assert status["activeProfile"] is None
    assert status["activatingProfile"] == "canonical"
    assert {item["id"]: item["status"]["value"] for item in listed} == {
        "canonical": "loaded", "compat-id": "loaded",
    }
    assert router.status()["activatingProfile"] is None


def test_model_listing_does_not_claim_loaded_before_manager_owns_starting_child():
    start_entered = threading.Event()
    finish_start = threading.Event()

    class BlockingStartManager(Manager):
        def start(self, model, port, args):
            start_entered.set()
            assert finish_start.wait(2)
            return super().start(model, port, args)

    manager = BlockingStartManager()
    router = RoutingCoordinator(manager, catalog(), object(), ready_fn=ready)
    with ThreadPoolExecutor(1) as activation:
        future = activation.submit(router.acquire, "low")
        assert start_entered.wait(2)
        try:
            _, loaded_profiles = router.model_listing_snapshot()
            status = router.status()
        finally:
            finish_start.set()
        lease = future.result(timeout=2)
        lease.release()

    assert loaded_profiles == frozenset()
    assert status["activatingProfile"] == "low"
    assert router.model_listing_snapshot()[1] == frozenset({"low"})


def test_browser_cors_preflight_is_side_effect_free_and_sanitizes_headers():
    manager = Manager()
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog(), token="control-secret",
        )
        client = TestClient(app)
        preflight = client.options(
            "/does-not-exist",
            headers={"Access-Control-Request-Headers": "Content-Type, bad header, X-FT-Token"},
        )
        default_preflight = client.options("/v1/chat/completions")

    assert preflight.status_code == 204
    assert preflight.headers["access-control-allow-origin"] == "*"
    assert preflight.headers["access-control-allow-methods"] == (
        "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    )
    assert preflight.headers["access-control-allow-headers"] == "Content-Type, X-FT-Token"
    assert preflight.headers["access-control-max-age"] == "86400"
    assert default_preflight.headers["access-control-allow-headers"] == (
        "Content-Type, Authorization, Accept, X-Requested-With"
    )
    assert manager.calls == []


def test_models_alias_matches_public_listing_and_keeps_control_auth_separate(monkeypatch):
    monkeypatch.setattr("freetoken.daemon.app.time.time", lambda: 1234567890)
    manager = Manager()
    catalog_doc = ModelCatalog(
        {"visible": ModelProfile("visible", "private.gguf", ())},
        settings=RouterSettings(api_keys=("router-key",)),
    )
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc,
            token="control-secret",
        )
        client = TestClient(app)
        denied = client.get("/v1/models", headers={"Origin": "https://client.example"})
        listed = client.get(
            "/v1/models",
            headers={"Origin": "https://client.example", "Authorization": "Bearer router-key"},
        )
        alias_denied = client.get("/models", headers={"X-FT-Token": "control-secret"})
        alias = client.get(
            "/models",
            headers={"Origin": "https://client.example", "Authorization": "Bearer router-key"},
        )
        profiles = client.get(
            "/router/profiles", headers={"X-FT-Token": "control-secret"}
        )
        profiles_denied = client.get(
            "/router/profiles", headers={"Authorization": "Bearer router-key"}
        )

    assert denied.status_code == 401
    assert listed.status_code == 200
    assert listed.headers["access-control-allow-origin"] == "https://client.example"
    assert [item["id"] for item in listed.json()["data"]] == ["visible"]
    assert alias_denied.status_code == 401
    assert alias.status_code == 200
    assert alias.json() == listed.json()
    assert alias.headers["access-control-allow-origin"] == "https://client.example"
    assert profiles.status_code == 200
    assert profiles.json()["data"][0]["model"] == "private.gguf"
    assert profiles_denied.status_code == 401


def test_explicit_cancel_while_upstream_connects_closes_result_and_releases_lease(monkeypatch):
    manager = Manager()
    catalog_doc = ModelCatalog({"low": ModelProfile("low", "low.gguf", ())})
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    connecting = threading.Event()
    finish_connect = threading.Event()
    raw = BytesIO(b"must not stream")

    def upstream(**kwargs):
        connecting.set()
        assert finish_connect.wait(2)
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
            "/v1/chat/completions", json={"model": "low"},
            headers={"X-FT-Request-ID": "cancel-during-connect"},
        )))
        thread.start()
        assert connecting.wait(1)
        assert client.get("/router/requests").json()["data"] == [
            {"id": "cancel-during-connect", "profile": "low"}
        ]
        cancelled = client.post("/router/requests/cancel-during-connect/cancel")
        assert cancelled.json() == {"cancelled": True, "id": "cancel-during-connect"}
        finish_connect.set()
        thread.join(2)
        assert not thread.is_alive()

    assert response[0].status_code == 409
    assert response[0].json()["error"]["type"] == "request_cancelled"
    assert raw.closed
    assert router.status()["activeRequests"] == 0
    assert router.status()["admissions"] == 1
    assert router.status()["cancellations"] == 1
    assert router.status()["terminalStreams"] == 0


def test_disconnect_while_upstream_connects_closes_orphaned_result(monkeypatch):
    manager = Manager()
    catalog_doc = ModelCatalog({"low": ModelProfile("low", "low.gguf", ())})
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    connecting = threading.Event()
    finish_connect = threading.Event()
    raw = BytesIO(b"must not stream")

    def upstream(**kwargs):
        connecting.set()
        assert finish_connect.wait(2)
        return UpstreamResponse(200, {"Content-Type": "text/event-stream"}, raw)

    monkeypatch.setattr("freetoken.daemon.app.open_upstream", upstream)

    async def scenario(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            request = asyncio.create_task(client.post(
                "/v1/chat/completions", json={"model": "low"},
                headers={"X-FT-Request-ID": "disconnect-during-connect"},
            ))
            for _ in range(100):
                if connecting.is_set():
                    break
                await asyncio.sleep(0.01)
            assert connecting.is_set()
            request.cancel()
            with pytest.raises(asyncio.CancelledError):
                await request
            assert router.status()["activeRequests"] == 0
            assert (await client.get("/router/requests")).json()["data"] == []
            finish_connect.set()
            for _ in range(100):
                if raw.closed:
                    break
                await asyncio.sleep(0.01)
            assert raw.closed

    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        asyncio.run(scenario(app))

    assert router.status()["admissions"] == 1
    assert router.status()["cancellations"] == 1
    assert router.status()["terminalStreams"] == 0


@pytest.mark.parametrize(
    "headers",
    [
        {"Authorization": "Bearer key"},
        {"Authorization": "bearer key"},
        {"Authorization": "Basic " + base64.b64encode(b"operator:key").decode()},
        {"X-Api-Key": "key"},
        {"Authorization": "Basic !!!not-base64", "X-Api-Key": "key"},
    ],
)
def test_router_inference_and_management_accept_pinned_api_key_forms(headers):
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
        assert denied.headers["www-authenticate"] == 'Basic realm="freetoken-swap"'
        assert client.get("/router/status").status_code == 401
        allowed = client.get("/router/status", headers=headers)
        assert allowed.status_code == 200
        assert manager.calls == []


@pytest.mark.parametrize(
    "authorization",
    [
        "Bearer wrong",
        "Basic " + base64.b64encode(b"operator:wrong").decode(),
        "Basic " + base64.b64encode(b"operator:\xff").decode(),
    ],
)
def test_explicit_authorization_key_takes_precedence_over_x_api_key(authorization):
    catalog_doc = ModelCatalog(
        {"low": ModelProfile("low", "low.gguf", ())},
        settings=RouterSettings(api_keys=("key",)),
    )
    manager = Manager()
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc,
        )
        response = TestClient(app).get(
            "/router/status",
            headers={"Authorization": authorization, "X-Api-Key": "key"},
        )

    assert response.status_code == 401
    assert manager.calls == []


def test_router_terminates_local_authentication_before_proxying(monkeypatch):
    manager = Manager()
    catalog_doc = ModelCatalog(
        {"low": ModelProfile("low", "low.gguf", ())},
        settings=RouterSettings(api_keys=("router-test-key",)),
    )
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    observed = {}

    def upstream(**kwargs):
        observed.update({key.lower(): value for key, value in forward_headers(kwargs["headers"]).items()})
        return UpstreamResponse(200, {"Content-Type": "application/json"}, BytesIO(b'{"ok":true}'))

    monkeypatch.setattr("freetoken.daemon.app.open_upstream", upstream)
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
            token="daemon-control-secret",
        )
        response = TestClient(app).post(
            "/v1/messages",
            content=b'{"model":"low","messages":[]}',
            headers={
                "Content-Type": "application/json",
                "Authorization": "Basic !!!not-base64",
                "X-Api-Key": "router-test-key",
                "X-FT-Token": "daemon-control-secret",
                "X-Correlation-ID": "client-safe-id",
            },
        )
    assert response.status_code == 200
    assert observed["x-correlation-id"] == "client-safe-id"
    assert "authorization" not in observed
    assert "x-api-key" not in observed
    assert "x-ft-token" not in observed


def test_proxy_response_headers_do_not_apply_inbound_credential_filtering():
    assert response_headers(
        {
            "Authorization": "Engine challenge metadata",
            "X-FT-Token": "engine-defined-response-value",
            "Connection": "close",
        }
    ) == {
        "Authorization": "Engine challenge metadata",
        "X-FT-Token": "engine-defined-response-value",
    }


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
        assert [item["name"] for item in client.get("/router/profiles").json()["data"]] == ["two"]


def test_router_catalog_reload_rotates_bearer_keys_atomically(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text(
        "[router]\napi_keys = ['first-key']\n[models.low]\nmodel = 'low.gguf'\n",
        encoding="utf-8",
    )
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
        path.write_text(
            "[router]\napi_keys = ['second-key']\n[models.low]\nmodel = 'low.gguf'\n",
            encoding="utf-8",
        )
        reloaded = client.post("/router/reload", headers={"Authorization": "Bearer first-key"})
        old_key = client.get("/router/status", headers={"Authorization": "Bearer first-key"})
        new_key = client.get("/router/status", headers={"Authorization": "Bearer second-key"})
    assert reloaded.status_code == 200
    assert old_key.status_code == 401
    assert new_key.status_code == 200


def test_router_reload_rejects_redefining_active_profile():
    manager = Manager()
    router = RoutingCoordinator(manager, catalog(), object(), ready_fn=ready)
    lease = router.acquire("low")
    replacement = ModelCatalog({"low": ModelProfile("low", "changed.gguf", ())})
    with pytest.raises(RoutingError, match="cannot redefine") as exc:
        router.replace_catalog(replacement)
    assert exc.value.status_code == 409
    lease.release()


def test_router_reload_refuses_active_scheduling_or_effective_lifecycle_changes():
    manager = Manager()
    current = ModelCatalog(
        {"low": ModelProfile("low", "low.gguf", (), group="g")},
        settings=RouterSettings(
            default_ttl_s=4,
            unload_timeout_s=12,
            groups=(RoutingGroup("g", ("low",), swap=True, persistent=False),),
        ),
    )
    router = RoutingCoordinator(manager, current, object(), ready_fn=ready)
    lease = router.acquire("low")

    changed_priority = ModelCatalog(
        {"low": ModelProfile("low", "low.gguf", (), priority=1, group="g")},
        settings=RouterSettings(
            default_ttl_s=4,
            unload_timeout_s=12,
            groups=(RoutingGroup("g", ("low",), swap=True, persistent=False),),
        ),
    )
    changed_default_ttl = ModelCatalog(
        {"low": ModelProfile("low", "low.gguf", (), group="g")},
        settings=RouterSettings(
            default_ttl_s=5,
            unload_timeout_s=12,
            groups=(RoutingGroup("g", ("low",), swap=True, persistent=False),),
        ),
    )
    changed_default_unload = ModelCatalog(
        {"low": ModelProfile("low", "low.gguf", (), group="g")},
        settings=RouterSettings(
            default_ttl_s=4,
            unload_timeout_s=13,
            groups=(RoutingGroup("g", ("low",), swap=True, persistent=False),),
        ),
    )
    changed_group_policy = ModelCatalog(
        {"low": ModelProfile("low", "low.gguf", (), group="g")},
        settings=RouterSettings(
            default_ttl_s=4,
            unload_timeout_s=12,
            groups=(RoutingGroup("g", ("low",), swap=False, persistent=True),),
        ),
    )
    for replacement in (changed_priority, changed_default_ttl, changed_default_unload, changed_group_policy):
        with pytest.raises(RoutingError, match="cannot redefine") as exc:
            router.replace_catalog(replacement)
        assert exc.value.status_code == 409
    assert router.catalog is current
    lease.release()


def test_router_reload_cannot_race_atomic_profile_lookup_and_dynamic_port_binding():
    entered = threading.Event()
    release_status = threading.Event()

    class BlockingStatusManager(Manager):
        block_next_status = False

        def status(self):
            if self.block_next_status:
                self.block_next_status = False
                entered.set()
                assert release_status.wait(2)
            return super().status()

    manager = BlockingStatusManager()
    current = ModelCatalog({"low": ModelProfile("low", "low.gguf", (), port=0)})
    router = RoutingCoordinator(
        manager, current, object(), ready_fn=ready, port_allocator=lambda: 20101
    )
    manager.block_next_status = True
    acquired = []
    acquire_thread = threading.Thread(target=lambda: acquired.append(router.acquire("low")))
    acquire_thread.start()
    assert entered.wait(1)

    replacement = ModelCatalog({"low": ModelProfile("low", "changed.gguf", (), port=0)})
    reload_result = {}

    def reload_catalog():
        try:
            router.replace_catalog(replacement)
        except RoutingError as exc:
            reload_result["error"] = exc

    reload_thread = threading.Thread(target=reload_catalog)
    reload_thread.start()
    time.sleep(0.05)
    assert reload_thread.is_alive()

    release_status.set()
    acquire_thread.join(2)
    reload_thread.join(2)
    assert not acquire_thread.is_alive() and not reload_thread.is_alive()
    assert reload_result["error"].code == "reload_conflict"
    assert router.catalog is current
    assert manager.model == "low.gguf"
    acquired.pop().release()


def test_router_reload_cannot_redefine_a_profile_already_queued_for_admission():
    manager = Manager()
    current = catalog()
    router = RoutingCoordinator(manager, current, object(), ready_fn=ready)
    active = router.acquire("low")
    queued_lease = []
    queued = threading.Thread(target=lambda: queued_lease.append(router.acquire("high")))
    queued.start()
    for _ in range(100):
        if router.status()["queuedRequests"] == 1:
            break
        time.sleep(0.01)
    assert router.status()["queuedRequests"] == 1

    replacement = ModelCatalog({
        "low": ModelProfile("low", "low.gguf", ()),
        "high": ModelProfile("high", "changed.gguf", (), priority=10),
    })
    with pytest.raises(RoutingError, match="admission or lifecycle") as exc:
        router.replace_catalog(replacement)
    assert exc.value.code == "reload_conflict"
    assert router.catalog is current

    active.release()
    queued.join(2)
    assert not queued.is_alive()
    assert manager.model == "high.gguf"
    queued_lease.pop().release()


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
    upstream_calls = []

    def upstream(**kwargs):
        upstream_calls.append(kwargs)
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
        duplicate = client.post(
            "/v1/chat/completions", json={"model": "low"},
            headers={"X-FT-Request-ID": "cancel-me"},
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["type"] == "request_conflict"
        assert len(upstream_calls) == 1
        assert router.status()["admissions"] == 1
        cancelled = client.post("/router/requests/cancel-me/cancel")
        assert cancelled.json() == {"cancelled": True, "id": "cancel-me"}
        thread.join(2)
        assert not thread.is_alive()
    assert response[0].status_code == 200
    assert router.status()["cancellations"] == 1
    assert router.status()["terminalStreams"] == 0
    assert "freetoken_swap_terminal_streams_total 0" in router.prometheus()
    assert router.status()["activeRequests"] == 0


def test_native_proxy_uses_a_real_loopback_http_upstream_and_preserves_sse_bytes():
    seen = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            seen["path"] = self.path
            seen["body"] = self.rfile.read(int(self.headers["Content-Length"]))
            seen["authorization"] = self.headers.get("Authorization")
            seen["daemon_token"] = self.headers.get("X-FT-Token")
            seen["correlation"] = self.headers.get("X-Correlation-ID")
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
        catalog_doc = ModelCatalog(
            {"low": ModelProfile("low", "low.gguf", (), port=port)},
            settings=RouterSettings(api_keys=("router-test-key",)),
        )
        router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
        with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
            app = build_app(
                manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
                lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
                token="daemon-control-secret",
            )
            payload = b'{"model":"low","stream":true,"messages":[]}'
            response = TestClient(app).post(
                "/v1/chat/completions", content=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer router-test-key",
                    "X-FT-Token": "daemon-control-secret",
                    "X-Correlation-ID": "client-safe-id",
                },
            )
        assert response.status_code == 200
        assert response.headers["x-engine"] == "loopback"
        assert response.content == b"data: {\"ok\":true}\n\ndata: [DONE]\n\n"
        assert seen == {
            "path": "/v1/chat/completions",
            "body": payload,
            "authorization": None,
            "daemon_token": None,
            "correlation": "client-safe-id",
        }
        assert router.status()["activeRequests"] == 0
        assert router.status()["terminalStreams"] == 1
        assert router.status()["lastTtftMs"] is not None
        assert router.status()["lastDurationMs"] is not None
        assert router.status()["lastActivationMs"] is not None
        assert router.status()["lastQueueWaitMs"] is not None
        assert router.status()["lastResponseBytes"] == len(response.content)
        assert router.status()["lastProxyBytesPerSecond"] is not None
        metrics = router.prometheus()
        assert "freetoken_swap_last_ttft_ms" in metrics
        assert "freetoken_swap_last_activation_ms" in metrics
        assert "freetoken_swap_last_queue_wait_ms" in metrics
        assert f"freetoken_swap_last_response_bytes {len(response.content)}" in metrics
        assert "freetoken_swap_last_proxy_bytes_per_second" in metrics
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


def test_router_management_load_preserves_failed_switch_recovery_evidence():
    manager = Manager()
    catalog_doc = catalog()

    def selective_ready(manager, probe, *, pid, port, timeout_s):
        return {"ready": manager.model == "low.gguf", "reason": "fixture-not-ready"}

    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=selective_ready)
    router.acquire("low").release()
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        response = TestClient(app).post("/router/load", json={"name": "high"})

    assert response.status_code == 503
    assert response.json()["error"]["type"] == "engine_not_ready"
    assert response.json()["recovery"]["launched"] is True
    assert manager.model == "low.gguf"
    assert router.status()["activeProfile"] == "low"
    assert router.status()["activeIdentityMatchesEngine"] is True


def test_router_management_unloads_one_or_all_under_single_resident_policy():
    manager = Manager()
    catalog_doc = catalog()
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        client = TestClient(app)
        assert client.post("/router/load", json={"name": "low"}).status_code == 200
        wrong = client.post("/router/unload", json={"name": "high"})
        assert wrong.json()["unloaded"] is False
        assert wrong.json()["router"]["activeProfile"] == "low"
        one = client.post("/router/unload", json={"name": "low"})
        assert one.json()["unloaded"] is True
        assert one.json()["router"]["activeProfile"] is None

        assert client.post("/router/load", json={"name": "high"}).status_code == 200
        all_residents = client.post("/router/unload")
        assert all_residents.json()["unloaded"] is True
        assert all_residents.json()["router"]["residentProfiles"] == []

    assert manager.calls == [
        ("start", "low.gguf"), ("stop", 30.0),
        ("start", "high.gguf"), ("stop", 30.0),
    ]


def test_router_model_list_hides_model_paths_and_ready_never_cold_loads():
    manager = Manager()
    catalog_doc = ModelCatalog(
        {"low": ModelProfile(
            "low", "/private/models/low.gguf", (), description="Public description"
        )},
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
        manager.model = "unexpected.gguf"
        assert client.get("/ready").status_code == 503
        stale_listing = client.get(
            "/v1/models", headers={"Authorization": "Bearer router-test-key"}
        )
        assert stale_listing.json()["data"][0]["status"] == {"value": "unloaded"}
        stale_status = client.get("/router/status", headers={"Authorization": "Bearer router-test-key"})
        assert stale_status.json()["residentProfiles"] == []
        assert stale_status.json()["activeIdentityMatchesEngine"] is False
        stale_metrics = client.get("/metrics", headers={"Authorization": "Bearer router-test-key"})
        assert "freetoken_swap_active_identity_matches_engine 0" in stale_metrics.text
        stale_models = client.get("/router/models", headers={"Authorization": "Bearer router-test-key"})
        assert stale_models.json()["data"][0]["resident"] is False
        assert stale_models.json()["capacity"] == {"maxResidentModels": 1, "availableResidentSlots": 0}
        manager.model = "/private/models/low.gguf"
        manager.args = ["--unexpected"]
        assert client.get("/ready").status_code == 503
        manager.args = []
        manager.port = 1999
        assert client.get("/ready").status_code == 503
    assert listed.status_code == 200
    listed_doc = listed.json()
    assert listed_doc["object"] == "list"
    assert len(listed_doc["data"]) == 1
    public_model = listed_doc["data"][0]
    assert public_model["id"] == "low"
    assert public_model["object"] == "model"
    assert public_model["owned_by"] == "freetoken"
    assert public_model["description"] == "Public description"
    assert public_model["status"] == {"value": "unloaded"}
    assert isinstance(public_model["created"], int) and public_model["created"] > 0
    assert "/private/models" not in json.dumps(listed_doc)


def test_ready_probe_linearizes_before_a_conflicting_swap():
    manager = Manager()
    probe_started = threading.Event()
    finish_probe = threading.Event()

    class Probe:
        def fresh_health(self, port):
            probe_started.set()
            assert finish_probe.wait(2)
            return {"reachable": True, "status": "ok", "maintenance": "serving"}

    probe = Probe()
    router = RoutingCoordinator(manager, catalog(), probe, ready_fn=ready)
    router.acquire("low").release()
    ready_response = []
    switched = []

    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=probe, footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog(), router=router,
        )
        client = TestClient(app)
        ready_thread = threading.Thread(
            target=lambda: ready_response.append(client.get("/ready"))
        )
        ready_thread.start()
        assert probe_started.wait(1)

        def switch():
            lease = router.acquire("high")
            switched.append(lease.profile.name)
            lease.release()

        switch_thread = threading.Thread(target=switch)
        switch_thread.start()
        switch_thread.join(0.05)
        assert switch_thread.is_alive()
        assert manager.calls == [("start", "low.gguf")]
        finish_probe.set()
        ready_thread.join(2)
        switch_thread.join(2)
        assert not ready_thread.is_alive() and not switch_thread.is_alive()

    assert ready_response[0].status_code == 200
    assert switched == ["high"]
    assert manager.calls == [("start", "low.gguf"), ("switch", "high.gguf")]


def test_manual_engine_start_holds_router_lifecycle_barrier():
    entered = threading.Event()
    finish_manual = threading.Event()

    class BlockingManager(Manager):
        def start(self, model, port, args):
            self.calls.append(("manual-start", model))
            entered.set()
            assert finish_manual.wait(2)
            self.model, self.port, self.args = model, port, list(args)
            self.pid += 1
            return {"pid": self.pid}

    manager = BlockingManager()
    catalog_doc = catalog()
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    manual_response = []
    routed_lease = []

    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        client = TestClient(app)
        manual_thread = threading.Thread(target=lambda: manual_response.append(client.post(
            "/engine/start", json={"model": "manual.gguf", "port": 1930}
        )))
        manual_thread.start()
        assert entered.wait(1)

        def acquire_routed():
            lease = router.acquire("low")
            routed_lease.append(lease)

        routed_thread = threading.Thread(target=acquire_routed)
        routed_thread.start()
        for _ in range(100):
            if router.status()["queuedRequests"] == 1:
                break
            threading.Event().wait(0.01)
        assert router.status()["queuedRequests"] == 1
        assert manager.calls == [("manual-start", "manual.gguf")]
        finish_manual.set()
        manual_thread.join(2)
        routed_thread.join(2)
        assert not manual_thread.is_alive() and not routed_thread.is_alive()

    assert manual_response[0].status_code == 200
    assert manager.calls == [("manual-start", "manual.gguf"), ("switch", "low.gguf")]
    routed_lease.pop().release()
    assert router.status()["activeRequests"] == 0


def test_manual_lifecycle_claim_rejects_router_ownership_and_requires_matching_token():
    router = RoutingCoordinator(Manager(), catalog(), object(), ready_fn=ready)
    lease = router.acquire("low")
    with pytest.raises(RoutingError) as conflict:
        router.begin_manual_lifecycle()
    assert conflict.value.code == "router_owned"
    assert conflict.value.status_code == 409
    lease.release()
    with pytest.raises(RoutingError, match="router owns"):
        router.begin_manual_lifecycle()

    router = RoutingCoordinator(Manager(), catalog(), object(), ready_fn=ready)
    owner = router.begin_manual_lifecycle()
    with pytest.raises(ValueError, match="not owned"):
        router.end_manual_lifecycle(object())
    assert router.status()["switching"] is True
    newer_owner = router.begin_manual_lifecycle(preempt_manual=True)
    router.end_manual_lifecycle(owner)
    assert router.status()["switching"] is True
    router.end_manual_lifecycle(newer_owner)
    assert router.status()["switching"] is False


def test_cancelled_manual_start_keeps_barrier_until_executor_finishes():
    entered = threading.Event()
    finish_manual = threading.Event()

    class BlockingManager(Manager):
        def start(self, model, port, args):
            self.calls.append(("manual-start", model))
            entered.set()
            assert finish_manual.wait(2)
            self.model, self.port, self.args = model, port, list(args)
            self.pid += 1
            return {"pid": self.pid}

    manager = BlockingManager()
    catalog_doc = catalog()
    router = RoutingCoordinator(manager, catalog_doc, object(), ready_fn=ready)
    routed_lease = []

    async def scenario(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            manual = asyncio.create_task(client.post(
                "/engine/start", json={"model": "manual.gguf", "port": 1930}
            ))
            for _ in range(100):
                if entered.is_set():
                    break
                await asyncio.sleep(0.01)
            assert entered.is_set()
            manual.cancel()

            def acquire_routed():
                routed_lease.append(router.acquire("low"))

            routed_thread = threading.Thread(target=acquire_routed)
            routed_thread.start()
            for _ in range(100):
                if router.status()["queuedRequests"] == 1:
                    break
                await asyncio.sleep(0.01)
            assert router.status()["queuedRequests"] == 1
            assert not manual.done()
            assert manager.calls == [("manual-start", "manual.gguf")]
            manual.cancel()
            await asyncio.sleep(0.05)
            assert not manual.done()
            finish_manual.set()
            with pytest.raises(asyncio.CancelledError):
                await manual
            routed_thread.join(2)
            assert not routed_thread.is_alive()

    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        asyncio.run(scenario(app))

    assert manager.calls == [("manual-start", "manual.gguf"), ("switch", "low.gguf")]
    routed_lease.pop().release()
    assert router.status()["activeRequests"] == 0


def test_cancelled_manual_profile_switch_completes_failed_readiness_rollback():
    readiness_entered = threading.Event()
    finish_readiness = threading.Event()

    class RecoveringManager(Manager):
        def switch_for_readiness(self, model, port, args, force=False):
            self.calls.append(("switch", model))
            previous = self.model, self.port, list(self.args)
            self.model, self.port, self.args = model, port, list(args)
            self.pid += 1
            return {"pid": self.pid}, previous

        def recover_switch(self, ticket, force=False):
            self.calls.append(("recover", ticket[0]))
            self.model, self.port, self.args = ticket
            self.pid += 1
            return {"launched": True, "pid": self.pid, "port": self.port}

    class Probe:
        def fresh_health(self, port):
            if port == 1923:
                readiness_entered.set()
                assert finish_readiness.wait(2)
                return {"reachable": True, "status": "error", "maintenance": "serving"}
            return {"reachable": True, "status": "ok", "maintenance": "serving"}

    manager = RecoveringManager()
    manager.model, manager.port, manager.args = "legacy.gguf", 1922, []
    catalog_doc = ModelCatalog({
        "high": ModelProfile("high", "high.gguf", (), port=1923, ready_timeout_s=1),
    })
    probe = Probe()
    router = RoutingCoordinator(manager, catalog_doc, probe, ready_fn=ready)

    async def scenario(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            request = asyncio.create_task(client.post(
                "/engine/switch-profile", json={"name": "high"}
            ))
            for _ in range(100):
                if readiness_entered.is_set():
                    break
                await asyncio.sleep(0.01)
            if request.done():
                response = request.result()
                pytest.fail(f"switch-profile exited early: {response.status_code} {response.text}")
            assert readiness_entered.is_set()
            request.cancel()
            assert router.status()["switching"] is True
            finish_readiness.set()
            with pytest.raises(asyncio.CancelledError):
                await request

    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=probe, footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog_doc, router=router,
        )
        asyncio.run(scenario(app))

    assert manager.calls == [("switch", "high.gguf"), ("recover", "legacy.gguf")]
    assert manager.model == "legacy.gguf"
    assert router.status()["switching"] is False


def test_router_shutdown_drains_active_lease_and_rejects_queued_and_new_admission():
    class ShutdownManager(Manager):
        def shutdown(self, timeout=None, force=False):
            self.calls.append(("shutdown", force))
            self.model = None
            return {"stopped": True, "already": False, "accounting": None}

    manager = ShutdownManager()
    router = RoutingCoordinator(manager, catalog(), object(), ready_fn=ready)
    active = router.acquire("low")
    queued_result = {}

    def acquire_queued():
        try:
            router.acquire("high")
        except RoutingError as exc:
            queued_result["error"] = exc

    queued = threading.Thread(target=acquire_queued)
    queued.start()
    for _ in range(100):
        if router.status()["queuedRequests"] == 1:
            break
        time.sleep(0.01)
    assert router.status()["queuedRequests"] == 1

    shutdown_result = {}
    shutdown = threading.Thread(
        target=lambda: shutdown_result.setdefault("result", router.shutdown(force=True))
    )
    shutdown.start()
    for _ in range(100):
        if router.status()["shuttingDown"]:
            break
        time.sleep(0.01)
    queued.join(2)
    assert not queued.is_alive()
    assert queued_result["error"].code == "router_shutting_down"
    assert shutdown.is_alive()
    assert router.is_ready() is False
    assert "freetoken_swap_shutting_down 1" in router.prometheus()
    assert manager.calls == [("start", "low.gguf")]
    with pytest.raises(RoutingError) as exc:
        router.acquire("low")
    assert exc.value.code == "router_shutting_down"

    active.release()
    shutdown.join(2)
    assert not shutdown.is_alive()
    assert shutdown_result["result"]["stopped"] is True
    assert manager.calls == [("start", "low.gguf"), ("shutdown", True)]
    assert router.status()["activeProfile"] is None


def test_failed_router_shutdown_reopens_admission_and_preserves_resident():
    class FailingShutdownManager(Manager):
        def shutdown(self, timeout=None, force=False):
            raise RuntimeError("stop failed")

    manager = FailingShutdownManager()
    router = RoutingCoordinator(manager, catalog(), object(), ready_fn=ready)
    router.acquire("low").release()

    with pytest.raises(RuntimeError, match="stop failed"):
        router.shutdown()

    assert router.status()["shuttingDown"] is False
    assert router.status()["activeProfile"] == "low"
    lease = router.acquire("low")
    lease.release()


def test_cancelled_daemon_shutdown_finishes_stop_and_requests_process_exit():
    entered = threading.Event()
    finish = threading.Event()

    class BlockingShutdownManager(Manager):
        def shutdown(self, timeout=None, force=False):
            entered.set()
            assert finish.wait(2)
            self.model = None
            return {"stopped": True, "already": False, "accounting": None}

    manager = BlockingShutdownManager()
    router = RoutingCoordinator(manager, catalog(), object(), ready_fn=ready)
    exits = []

    async def scenario(app):
        app.state.request_shutdown = lambda: exits.append("requested")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            request = asyncio.create_task(client.post("/shutdown", json={"force": True}))
            for _ in range(100):
                if entered.is_set():
                    break
                await asyncio.sleep(0.01)
            assert entered.is_set()
            request.cancel()
            request.cancel()
            await asyncio.sleep(0.05)
            assert not request.done()
            finish.set()
            with pytest.raises(asyncio.CancelledError):
                await request

    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog(), router=router,
        )
        asyncio.run(scenario(app))

    assert exits == ["requested"]
    assert router.status()["shuttingDown"] is True


def test_daemon_shutdown_latches_before_single_lifecycle_worker_is_available():
    start_entered = threading.Event()
    finish_start = threading.Event()

    class BlockingLifecycleManager(Manager):
        def start(self, model, port, args):
            self.calls.append(("start", model))
            start_entered.set()
            assert finish_start.wait(2)
            self.model, self.port, self.args = model, port, list(args)
            self.pid += 1
            return {"pid": self.pid}

        def shutdown(self, timeout=None, force=False):
            self.calls.append(("shutdown", force))
            self.model = None
            return {"stopped": True, "already": False, "accounting": None}

    manager = BlockingLifecycleManager()
    router = RoutingCoordinator(manager, catalog(), object(), ready_fn=ready)
    exits = []

    async def scenario(app):
        app.state.request_shutdown = lambda: exits.append("requested")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            manual = asyncio.create_task(client.post(
                "/engine/start", json={"model": "legacy.gguf", "port": 1930}
            ))
            for _ in range(100):
                if start_entered.is_set():
                    break
                await asyncio.sleep(0.01)
            assert start_entered.is_set()

            shutdown = asyncio.create_task(client.post("/shutdown", json={}))
            for _ in range(100):
                if router.status()["shuttingDown"]:
                    break
                await asyncio.sleep(0.01)
            assert router.status()["shuttingDown"] is True
            assert not shutdown.done()
            with pytest.raises(RoutingError) as exc:
                router.acquire("low")
            assert exc.value.code == "router_shutting_down"

            finish_start.set()
            assert (await manual).status_code == 200
            response = await shutdown
            assert response.status_code == 200

    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=object(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=catalog(), router=router,
        )
        asyncio.run(scenario(app))

    assert manager.calls == [("start", "legacy.gguf"), ("shutdown", False)]
    assert exits == ["requested"]


def test_coordinated_daemon_exit_drains_then_detaches_once_for_readoption():
    class DetachingManager(Manager):
        def detach(self):
            self.calls.append(("detach", self.model))

    manager = DetachingManager()
    router = RoutingCoordinator(manager, catalog(), object(), ready_fn=ready)
    active = router.acquire("low")
    result = {}
    exiting = threading.Thread(
        target=lambda: result.setdefault(
            "value", router.coordinated_exit(stop_child=False)
        )
    )
    exiting.start()
    for _ in range(100):
        if router.status()["shuttingDown"]:
            break
        time.sleep(0.01)
    assert router.status()["shuttingDown"] is True
    assert exiting.is_alive()
    assert manager.calls == [("start", "low.gguf")]

    active.release()
    exiting.join(2)
    assert not exiting.is_alive()
    assert result["value"] is None
    assert manager.calls == [("start", "low.gguf"), ("detach", "low.gguf")]
    assert manager.model == "low.gguf"
    assert router.status()["activeProfile"] is None

    # Uvicorn lifespan can run after POST /shutdown already completed. The
    # repeated exit hook must not detach or stop the child a second time.
    assert router.coordinated_exit(stop_child=False) is None
    assert manager.calls == [("start", "low.gguf"), ("detach", "low.gguf")]


def test_coordinated_exit_waits_for_preempted_manual_transaction_token():
    class DetachingManager(Manager):
        def detach(self):
            self.calls.append(("detach", self.model))

    manager = DetachingManager()
    router = RoutingCoordinator(manager, catalog(), object(), ready_fn=ready)
    older = router.begin_manual_lifecycle()
    newer = router.begin_manual_lifecycle(preempt_manual=True)
    router.end_manual_lifecycle(newer)
    assert router.status()["switching"] is False

    exiting = threading.Thread(
        target=lambda: router.coordinated_exit(stop_child=False)
    )
    exiting.start()
    for _ in range(100):
        if router.status()["shuttingDown"]:
            break
        time.sleep(0.01)
    assert router.status()["shuttingDown"] is True
    assert exiting.is_alive()
    assert manager.calls == []

    router.end_manual_lifecycle(older)
    exiting.join(2)
    assert not exiting.is_alive()
    assert manager.calls == [("detach", None)]


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
