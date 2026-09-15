"""The daemon's HTTP control plane. camelCase JSON throughout. Loopback by default; an optional
``X-FT-Token`` shared secret gates everything except the daemon's own ``/health`` liveness probe.

Handlers are ``async`` and push every blocking call to an executor so the event loop never
blocks. Two executors: a small **lifecycle** pool for start/stop/switch, kept separate from the
**proxy/metrics** pool, so a storm of health/metrics polls against a loading serve can never
starve an operator's stop."""

from __future__ import annotations

import asyncio
import base64
import binascii
import collections
import functools
import json
import os
import re
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable
from urllib.parse import quote_from_bytes

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response, StreamingResponse
from pydantic import BaseModel

from .accounting import AccountingOutboxError, AccountingPrepareError
from .catalog import CatalogError, ModelCatalog
from .inference_proxy import (
    RequestModelError,
    filter_request_body,
    open_upstream,
    request_model,
    response_headers,
)
from .logring import LogRing
from .readiness import wait_for_ready
from .router import RoutingCoordinator, RoutingError, allocate_loopback_port
from .serve_manager import Conflict, SwitchLaunchError
from .version import DAEMON_VERSION


_HTTP_TOKEN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_DEFAULT_CORS_HEADERS = "Content-Type, Authorization, Accept, X-Requested-With"


def _cors_request_headers(value: str | None) -> str:
    """Echo only syntactically valid HTTP header names in a CORS preflight."""
    if value is None:
        return _DEFAULT_CORS_HEADERS
    return ", ".join(
        part for raw in value.split(",")
        if (part := raw.strip()) and _HTTP_TOKEN.fullmatch(part)
    )


def _escaped_path_suffix(raw_path: bytes, decoded_prefix: str) -> str | None:
    """Remove a decoded prefix while retaining the suffix's original escaping."""
    prefix = decoded_prefix.encode("utf-8")
    raw_index = prefix_index = 0
    while raw_index < len(raw_path) and prefix_index < len(prefix):
        end = raw_index + 1
        value = raw_path[raw_index]
        if value == ord("%"):
            if raw_index + 3 > len(raw_path):
                return None
            try:
                value = int(raw_path[raw_index + 1:raw_index + 3], 16)
            except ValueError:
                return None
            end = raw_index + 3
        if value != prefix[prefix_index]:
            return None
        raw_index = end
        prefix_index += 1
    if prefix_index != len(prefix):
        return None
    suffix = raw_path[raw_index:]
    try:
        return suffix.decode("ascii")
    except UnicodeDecodeError:
        return quote_from_bytes(suffix, safe="/%:@!$&'()*+,;=-._~")


def _extract_api_key(authorization: str | None, x_api_key: str | None) -> str | None:
    """Apply the pinned Basic-password, Bearer, then x-api-key contract."""
    bearer_key = None
    basic_key = None
    if authorization:
        scheme, separator, credentials = authorization.partition(" ")
        if separator and scheme.lower() == "bearer":
            bearer_key = credentials or None
        elif separator and scheme.lower() == "basic":
            try:
                decoded = base64.b64decode(credentials, validate=True).decode(
                    "utf-8", errors="surrogateescape"
                )
            except (binascii.Error, ValueError):
                pass
            else:
                if ":" in decoded:
                    basic_key = decoded.split(":", 1)[1] or None
    return basic_key or bearer_key or x_api_key


class StartBody(BaseModel):
    model: str
    port: int | None = None
    args: list[str] = []


class StopBody(BaseModel):
    force: bool = False


class SwitchBody(StartBody):
    force: bool = False


class ProfileBody(BaseModel):
    name: str
    force: bool = False


class RoutingProfileSelectionBody(BaseModel):
    name: str | None


class RouterUnloadBody(BaseModel):
    name: str | None = None


class RouterLoadBody(BaseModel):
    name: str


class AccountingAckBody(BaseModel):
    receiptId: str


class CheckpointBody(BaseModel):
    id: str
    args: list[str] = []


class CancelBody(BaseModel):
    id: str


class BenchBody(BaseModel):
    # Raw `ft bench bw` args (e.g. ["--dtype", "nvfp4", "--threshold", "2.5"]); empty = all dtypes.
    args: list[str] = []


# Deliberately dependency-free management view. It never embeds catalog data,
# local paths, tokens, or machine identifiers in the initial HTML response;
# authenticated JSON API calls populate the view only after the operator enters
# a bearer token for this browser session.
_ROUTER_UI = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FreeToken swap</title><style>
body{font:15px system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#18212b}button,input{font:inherit;padding:.4rem;margin:.2rem}pre{background:#f3f5f7;padding:1rem;overflow:auto}.row{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap}
</style></head><body><h1>FreeToken swap</h1><p>Enter a router bearer key to inspect or control this local daemon. The key is kept only in this page's memory.</p>
<div class="row"><label>Bearer key <input id="key" type="password" autocomplete="off"></label><button id="refresh">Refresh</button><button id="reload">Reload catalog</button><button id="unload">Unload resident</button></div>
<h2>Status</h2><pre id="status">Not loaded.</pre><h2>Models</h2><div id="models"></div><h2>Hardware</h2><pre id="hardware">Not loaded.</pre>
<script>
const $=id=>document.getElementById(id), headers=()=>({Authorization:'Bearer '+$('key').value});
async function api(path,opt={}){let r=await fetch(path,{...opt,headers:{...headers(),...(opt.headers||{})}});let d=await r.json();if(!r.ok)throw new Error(d.detail||d.error?.message||r.status);return d}
function show(id,value){$(id).textContent=JSON.stringify(value,null,2)}
async function refresh(){try{let [s,m,h]=await Promise.all([api('/router/status'),api('/router/models'),api('/router/hardware')]);show('status',s);show('hardware',h);let box=$('models');box.replaceChildren();for(const p of m.data){let b=document.createElement('button');b.textContent='Load '+p.name;b.onclick=async()=>{await api('/router/load',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:p.name})});refresh()};box.append(b)}}catch(e){show('status',{error:e.message})}}
$('refresh').onclick=refresh;$('reload').onclick=async()=>{await api('/router/reload',{method:'POST'});refresh()};$('unload').onclick=async()=>{await api('/router/unload',{method:'POST'});refresh()};
</script></body></html>"""


def _bench_profile_path(gpu_uuid: str | None) -> str | None:
    # per-GPU profiles and no torch here: the serve's own card when its --gpu names one, else the newest file
    from freetoken.moe.bench_profile import default_profile_path, latest_profile_path  # torch-free

    if gpu_uuid:
        path = default_profile_path(gpu_uuid)
        if os.path.isfile(path):
            return path
    return latest_profile_path()


def _serve_gpu_uuid(args: list[str]) -> str | None:
    """The full UUID a serve's `--gpu` pins, or None when there is none or it cannot be resolved."""
    for i, a in enumerate(args):
        val = a[len("--gpu="):] if a.startswith("--gpu=") else (args[i + 1] if a == "--gpu" and i + 1 < len(args) else None)
        if not val:
            continue
        from freetoken.gpu_select import resolve_gpu_uuids

        try:
            resolved = resolve_gpu_uuids([val])
        except ValueError:
            return None
        if resolved:
            return resolved[0]
        # no NVML: a UUID value still keys the profile file (canonical prefix), an index cannot
        return "GPU-" + val[len("GPU-"):] if val.upper().startswith("GPU-") else None
    return None


def _read_bench_profile(path: str | None) -> dict | None:
    if path is None:
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _bench_sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _parse_ftbench(line: str) -> dict | None:
    """``FTBENCH <done> <total> <label>`` -> a progress dict (mirrors ft checkpoint's FTCONVERT)."""
    parts = line.split(maxsplit=3)
    if len(parts) < 4 or parts[0] != "FTBENCH":
        return None
    try:
        return {"done": int(parts[1]), "total": int(parts[2]), "label": parts[3]}
    except ValueError:
        return None


def build_app(
    *,
    manager,
    ring,
    probe,
    footprint_fn: Callable[[int | None], dict],
    lifecycle_pool: ThreadPoolExecutor,
    proxy_pool: ThreadPoolExecutor,
    default_serve_port: int = 1919,
    token: str | None = None,
    checkpoints=None,
    started_wall: float = 0.0,
    wall_now: Callable[[], float] | None = None,
    shutdown_hook: Callable[[], None] | None = None,
    catalog: ModelCatalog | None = None,
    router: RoutingCoordinator | None = None,
    catalog_path: str | None = None,
    router_ring: LogRing | None = None,
    catalog_watch_interval_s: float = 0.0,
) -> FastAPI:
    import time as _time

    wall_now = wall_now or _time.time
    app = FastAPI(title="FreeToken daemon", version=DAEMON_VERSION)

    @app.middleware("http")
    async def cors_preflight(request: Request, call_next):
        # Match the pinned compatibility server's side-effect-free global
        # preflight contract. Actual requests still pass through normal route
        # authentication and lifecycle ownership.
        if request.method != "OPTIONS":
            return await call_next(request)
        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": _cors_request_headers(
                    request.headers.get("access-control-request-headers")
                ),
                "Access-Control-Max-Age": "86400",
            },
        )
    catalog = catalog or ModelCatalog.empty()
    router = router or RoutingCoordinator(
        manager, catalog, probe, default_port=default_serve_port
    )
    # Keep router events separate from captured engine stdout. Apart from
    # making an operator's engine-log view useful, this prevents a noisy child
    # from evicting the bounded lifecycle/proxy audit trail. The event payload
    # deliberately contains no headers, query strings, request body, or model
    # path: those may carry credentials or prompts.
    router_ring = router_ring or LogRing(capacity=1000)
    app.state.router_ring = router_ring
    inflight_lock = threading.Lock()
    inflight: dict[str, dict] = {}
    request_reservations: dict[str, dict] = {}
    watch_stop = threading.Event()
    watch_lock = threading.Lock()
    watch_state = {
        "enabled": bool(catalog_path and catalog_watch_interval_s > 0),
        "intervalS": catalog_watch_interval_s if catalog_watch_interval_s > 0 else None,
        "lastResult": None,
    }
    app.state.catalog_watch_stop = watch_stop

    if shutdown_hook is not None:

        @app.on_event("shutdown")
        async def _on_shutdown() -> None:
            # uvicorn fires this on SIGTERM/SIGINT. Run the (blocking) hook off-loop so the grace
            # period in stop() can't wedge the event loop during shutdown.
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(None, shutdown_hook)
            except Exception:  # noqa: BLE001
                pass

    def require_token(
        x_ft_token: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ) -> None:
        if token is not None:
            if x_ft_token != token:
                raise HTTPException(status_code=401, detail="invalid or missing X-FT-Token")
            return
        keys = router.catalog.settings.api_keys
        if keys:
            supplied = _extract_api_key(authorization, x_api_key)
            if supplied not in keys:
                raise HTTPException(
                    status_code=401,
                    detail="invalid or missing API key",
                    headers={"WWW-Authenticate": 'Basic realm="freetoken-swap"'},
                )

    auth = [Depends(require_token)]

    def require_router_key(
        authorization: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ) -> None:
        keys = router.catalog.settings.api_keys
        if not keys:
            return
        supplied = _extract_api_key(authorization, x_api_key)
        if supplied not in keys:
            raise HTTPException(
                status_code=401,
                detail="invalid or missing API key",
                headers={"WWW-Authenticate": 'Basic realm="freetoken-swap"'},
            )

    async def run(pool: ThreadPoolExecutor, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(pool, functools.partial(fn, *args, **kwargs))

    async def run_to_completion(operation):
        """Defer caller cancellation until an ownership transaction is terminal."""
        task = asyncio.create_task(operation())
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            while True:
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    continue
                except BaseException:
                    break
                else:
                    break
            raise

    async def run_manual_transaction(operation, *, preempt_manual: bool = False):
        """Keep manual ownership until the complete transaction reaches a terminal state."""
        owner = begin_manual_lifecycle(preempt_manual=preempt_manual)
        try:
            return await run_to_completion(operation)
        finally:
            router.end_manual_lifecycle(owner)

    async def acquire_route(
        name: str,
        cancellation: threading.Event | None = None,
        on_reserved: Callable[[bool, int], None] | None = None,
        *,
        apply_loading_policy: bool = False,
        apply_routing_profile: bool = True,
    ):
        """Keep executor-side admission owned if its HTTP task is cancelled."""
        loop = asyncio.get_running_loop()
        cancellation = cancellation or threading.Event()
        future = loop.run_in_executor(
            lifecycle_pool,
            functools.partial(
                router.acquire,
                name,
                cancellation,
                on_reserved,
                apply_loading_policy=apply_loading_policy,
                apply_routing_profile=apply_routing_profile,
            ),
        )
        shielded = asyncio.shield(future)
        try:
            return await shielded
        except asyncio.CancelledError:
            router.cancel_acquire(cancellation)
            # Retain ownership until the executor-side admission is terminal.
            # This retrieves its expected RoutingError before the event loop
            # can close and releases a lease if admission won the race.
            try:
                orphaned = await asyncio.shield(future)
            except BaseException:
                pass
            else:
                orphaned.release()
            raise

    async def connect_upstream(**kwargs):
        """Close a connector result that arrives after its HTTP task disconnects."""
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(proxy_pool, functools.partial(open_upstream, **kwargs))
        try:
            return await asyncio.shield(future)
        except asyncio.CancelledError:
            def close_orphaned_upstream(done) -> None:
                try:
                    orphaned = done.result()
                except BaseException:
                    return
                orphaned.close()

            future.add_done_callback(close_orphaned_upstream)
            raise

    def resolve_port(explicit: int | None) -> int:
        if explicit == 0:
            return allocate_loopback_port()
        if explicit is not None:
            return explicit
        st = manager.status()
        return st.get("port") or default_serve_port

    def begin_manual_lifecycle(*, preempt_manual: bool = False) -> object:
        """Atomically keep legacy engine controls outside routed ownership."""
        try:
            return router.begin_manual_lifecycle(preempt_manual=preempt_manual)
        except RoutingError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    def accounting_error(exc: Exception) -> JSONResponse:
        code = (
            "accounting_outbox_failed"
            if isinstance(exc, AccountingOutboxError)
            else "accounting_prepare_failed"
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": str(exc),
                "code": code,
                "enginePreserved": True,
            },
        )

    # ---- daemon self-health (never gated; always answers if the daemon is up) ----

    @app.get("/health")
    async def health():
        st = manager.status()
        return {
            "status": "ok",
            "version": DAEMON_VERSION,
            "uptimeS": int(wall_now() - started_wall) if started_wall else 0,
            "engineRunning": bool(st.get("running")),
        }

    @app.get("/ready")
    async def ready():
        """Stable router readiness; it never starts a model as a probe side effect."""
        accepting = await run(proxy_pool, router.is_ready, probe)
        return JSONResponse(status_code=200 if accepting else 503, content={"ready": accepting})

    @app.get("/ui/")
    async def router_ui():
        """A static shell; authenticated APIs supply all operational data."""
        return HTMLResponse(_ROUTER_UI)

    def router_event(event: str, **fields: Any) -> None:
        router_ring.append(
            json.dumps({"event": event, **fields}, separators=(",", ":"), sort_keys=True),
            kind="event",
            ts=wall_now(),
        )

    def record_watch(result: str) -> None:
        with watch_lock:
            watch_state["lastResult"] = result
            watch_state["lastChangedAt"] = wall_now()

    def catalog_watch_snapshot() -> dict:
        with watch_lock:
            return dict(watch_state)

    def catalog_stamp() -> tuple[int, int] | None:
        if not catalog_path:
            return None
        try:
            stat = os.stat(catalog_path)
        except OSError:
            return None
        return stat.st_mtime_ns, stat.st_size

    def start_catalog_watcher() -> None:
        """Poll a local catalog safely; only a fully validated tree is installed.

        Polling keeps the daemon stdlib-only and cross-platform. A changed
        malformed file is remembered until it changes again, avoiding a log
        storm while an editor writes it. Active-profile redefinition is still
        refused by the coordinator, so a watcher cannot steal a live child.
        """
        if not watch_state["enabled"]:
            return
        interval = float(catalog_watch_interval_s)

        def watch() -> None:
            previous = catalog_stamp()
            while not watch_stop.wait(interval):
                changed = catalog_stamp()
                if changed == previous:
                    continue
                previous = changed
                try:
                    replacement = ModelCatalog.load(catalog_path)
                    router.replace_catalog(replacement)
                except CatalogError:
                    record_watch("invalid_catalog")
                    router_event("catalog_watch_rejected", code="invalid_catalog")
                except RoutingError as exc:
                    record_watch(exc.code)
                    router_event("catalog_watch_rejected", code=exc.code)
                else:
                    record_watch("reloaded")
                    router_event("catalog_watch_reloaded")

        thread = threading.Thread(target=watch, name="ft-daemon-catalog-watch", daemon=True)
        app.state.catalog_watch_thread = thread
        thread.start()

    start_catalog_watcher()

    if watch_state["enabled"]:

        @app.on_event("shutdown")
        async def _stop_catalog_watcher() -> None:
            watch_stop.set()

    async def forward_routed(
        request: Request,
        model: str,
        *,
        path_and_query: str,
        body: bytes,
        apply_request_filters: bool = False,
    ):
        """Select a configured model, then stream the engine response unchanged.

        The lease spans the full downstream iterator. If a client disconnects,
        Starlette closes that iterator, which closes the upstream socket and
        releases admission for the next model swap.
        """
        started = time.monotonic()
        request_id = request.headers.get("x-ft-request-id") or uuid.uuid4().hex
        if not request_id.isascii() or not request_id or len(request_id) > 128:
            raise HTTPException(status_code=400, detail="X-FT-Request-ID must be 1 to 128 ASCII characters")
        # Use FastAPI's registered route template, not the concrete path or
        # query. An upstream passthrough tail can itself contain a signed URL,
        # opaque bearer-like value, or tenant identifier.
        safe_route = getattr(request.scope.get("route"), "path", request.method)
        admission_cancellation = threading.Event()
        with inflight_lock:
            if request_id in request_reservations:
                router_event("request_conflict", profile=model, route=safe_route)
                return JSONResponse(
                    status_code=409,
                    content={"error": {
                        "message": "request id is already active", "type": "request_conflict",
                    }},
                )
            request_reservations[request_id] = {
                "profile": model,
                "cancellation": admission_cancellation,
                "cancelled": False,
            }

        def filtered_body(route_lease) -> bytes:
            if not apply_request_filters:
                return body
            profile = route_lease.profile
            target_model = route_lease.model_id or model
            return filter_request_body(
                body,
                profile.drop_fields,
                profile.set_fields,
                profile.set_fields_by_id,
                requested_model=target_model,
                rewrite_model=(
                    profile.use_model_name
                    or (
                        target_model
                        if route_lease.selector_id is not None
                        or route_lease.routing_profile_id is not None
                        else None
                    )
                ),
            )

        def lease_event_identity(route_lease) -> dict[str, str]:
            identity = {"profile": route_lease.profile.name}
            if route_lease.selector_id is not None:
                identity["selector"] = route_lease.selector_id
                identity["target"] = route_lease.model_id
            if route_lease.routing_profile_id is not None:
                identity["routingProfile"] = route_lease.routing_profile_id
                identity["pin"] = route_lease.pin_id
                identity.setdefault("target", route_lease.model_id)
            return identity

        def loading_frame(text: str) -> bytes:
            payload = {"choices": [{"delta": {"reasoning_content": text}}]}
            return b"data: " + json.dumps(
                payload, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8") + b"\n\n"

        def loading_error(exc: BaseException) -> bytes:
            error_type = exc.code if isinstance(exc, RoutingError) else "upstream_unavailable"
            payload: dict[str, Any] = {"error": {"message": str(exc), "type": error_type}}
            if isinstance(exc, RoutingError) and exc.recovery is not None:
                payload["recovery"] = exc.recovery
            return (
                b"data: "
                + json.dumps(payload, separators=(",", ":")).encode("utf-8")
                + b"\n\ndata: [DONE]\n\n"
            )

        abandon_state = {"done": False}

        def abandon_loading_acquisition(
            acquisition: asyncio.Task, *, record_cancellation: bool = True
        ) -> None:
            """Wake an abandoned admission and release any lease it later returns."""
            if abandon_state["done"]:
                return
            abandon_state["done"] = True
            router.cancel_acquire(admission_cancellation)
            if record_cancellation:
                router.record_cancellation()

            def release_if_admitted(done: asyncio.Task) -> None:
                try:
                    admitted = done.result()
                except BaseException:
                    return
                admitted.release()

            acquisition.add_done_callback(release_if_admitted)

        async def loading_stream(acquisition: asyncio.Task):
            """Bridge one admitted cold request into loading SSE, then its real response."""
            lease = None
            upstream = None
            first_byte_at = None
            byte_count = 0
            cancelled = False
            cancellation_recorded = False
            last_position = None
            try:
                yield loading_frame("━━━━━\n")
                yield loading_frame(f"freetoken-swap loading model: {model}\n")
                initial_position = reservation_state.get("queuePosition")
                if isinstance(initial_position, int):
                    last_position = initial_position
                    yield loading_frame(f"\nQueue position: #{initial_position} ")
                while not acquisition.done():
                    position = router.queue_position(admission_cancellation)
                    if position is not None and position != last_position:
                        last_position = position
                        yield loading_frame(f"\nQueue position: #{position} ")
                    done, _ = await asyncio.wait({acquisition}, timeout=0.75)
                    if acquisition in done:
                        lease = acquisition.result()
                    else:
                        yield loading_frame(".")
                if lease is None:
                    lease = acquisition.result()

                yield loading_frame("\n")
                yield loading_frame(f"Done! ({time.monotonic() - started:.2f}s)\n")
                yield loading_frame("━━━━━\n")
                yield loading_frame(" \n")

                with inflight_lock:
                    cancelled_before_connect = request_reservations[request_id]["cancelled"]
                if cancelled_before_connect:
                    raise RoutingError(
                        "request_cancelled",
                        "request cancelled before upstream connection",
                        status_code=409,
                    )

                outbound_body = filtered_body(lease)

                upstream = await connect_upstream(
                    port=lease.port,
                    base_url=lease.proxy_base_url,
                    path_and_query=path_and_query,
                    headers=dict(request.headers),
                    body=outbound_body,
                    method=request.method,
                    timeout_s=lease.profile.upstream_timeout_s or router.upstream_timeout_s,
                )
                with inflight_lock:
                    cancelled_while_connecting = request_reservations[request_id]["cancelled"]
                    if not cancelled_while_connecting:
                        inflight[request_id] = {
                            "profile": lease.profile.name,
                            "upstream": upstream,
                            "cancelled": False,
                        }
                if cancelled_while_connecting:
                    raise RoutingError(
                        "request_cancelled",
                        "request cancelled while opening upstream connection",
                        status_code=409,
                    )

                router_event(
                    "admitted", **lease_event_identity(lease), route=safe_route
                )
                iterator = iter(upstream.chunks())

                def next_chunk():
                    try:
                        return True, next(iterator)
                    except StopIteration:
                        return False, b""

                loop = asyncio.get_running_loop()
                while True:
                    has_chunk, chunk = await loop.run_in_executor(proxy_pool, next_chunk)
                    if not has_chunk:
                        break
                    if first_byte_at is None:
                        first_byte_at = time.monotonic()
                    byte_count += len(chunk)
                    yield chunk
            except asyncio.CancelledError:
                cancelled = True
                abandon_loading_acquisition(acquisition)
                cancellation_recorded = True
                router_event("request_cancelled", profile=model, route=safe_route)
                raise
            except Exception as exc:
                if isinstance(exc, RoutingError):
                    router_event("admission_failed", profile=model, route=safe_route, code=exc.code)
                else:
                    router_event("upstream_connect_failed", profile=model, route=safe_route)
                yield loading_error(exc)
            finally:
                ended = time.monotonic()
                # Starlette may finalize an async response iterator with
                # ``GeneratorExit`` rather than injecting ``CancelledError``.
                # A downstream that disappears must still synchronously wake
                # and cancel any queued ownership.
                if not acquisition.done():
                    cancelled = True
                    abandon_loading_acquisition(
                        acquisition, record_cancellation=not cancellation_recorded
                    )
                elif lease is None:
                    try:
                        lease = acquisition.result()
                    except BaseException:
                        pass
                    else:
                        cancelled = True
                        if not cancellation_recorded:
                            router.record_cancellation()
                if upstream is not None:
                    upstream.close()
                with inflight_lock:
                    reservation = request_reservations.get(request_id, {})
                    item = inflight.get(request_id, {})
                    cancelled = (
                        cancelled
                        or bool(reservation.get("cancelled"))
                        or bool(item.get("cancelled"))
                    )
                    if upstream is not None and item.get("upstream") is upstream:
                        inflight.pop(request_id, None)
                    request_reservations.pop(request_id, None)
                if lease is not None:
                    router.record_stream(
                        ttft_s=(first_byte_at - started) if first_byte_at is not None else None,
                        duration_s=ended - started,
                        response_bytes=byte_count,
                        completed=not cancelled,
                    )
                    lease.release()
                    router_event(
                        "request_finished",
                        **lease_event_identity(lease),
                        route=safe_route,
                        status=upstream.status if upstream is not None else 200,
                        cancelled=cancelled,
                        responseBytes=byte_count,
                    )

        loading_eligible = False
        if request.url.path == "/v1/chat/completions":
            try:
                request_doc = json.loads(body)
            except (UnicodeDecodeError, json.JSONDecodeError):
                request_doc = None
            loading_eligible = isinstance(request_doc, dict) and request_doc.get("stream") is True

        if loading_eligible:
            loop = asyncio.get_running_loop()
            reserved = asyncio.Event()
            reservation_state: dict[str, Any] = {}

            def on_reserved(loading_required: bool, queue_position: int) -> None:
                reservation_state["loadingRequired"] = loading_required
                reservation_state["queuePosition"] = queue_position
                loop.call_soon_threadsafe(reserved.set)

            acquisition = asyncio.create_task(
                acquire_route(
                    model,
                    admission_cancellation,
                    on_reserved,
                    apply_loading_policy=True,
                )
            )
            reservation_wait = asyncio.create_task(reserved.wait())
            try:
                done, _ = await asyncio.wait(
                    {acquisition, reservation_wait}, return_when=asyncio.FIRST_COMPLETED
                )
                if acquisition in done:
                    reservation_wait.cancel()
                    lease = acquisition.result()
                else:
                    if reservation_state["loadingRequired"]:
                        class AdmissionOwnedStreamingResponse(StreamingResponse):
                            async def __call__(self, scope, receive, send) -> None:
                                try:
                                    await super().__call__(scope, receive, send)
                                finally:
                                    # Async-generator finalization can be deferred
                                    # beyond response termination. The response is
                                    # the ownership barrier for both unstarted and
                                    # suspended loading iterators.
                                    with inflight_lock:
                                        owned = request_id in request_reservations
                                        request_reservations.pop(request_id, None)
                                    if owned:
                                        abandon_loading_acquisition(acquisition)

                        return AdmissionOwnedStreamingResponse(
                            loading_stream(acquisition),
                            status_code=200,
                            headers={
                                "Cache-Control": "no-cache",
                                "Connection": "keep-alive",
                                "X-FT-Request-ID": request_id,
                            },
                            media_type="text/event-stream",
                        )
                    lease = await acquisition
            except RoutingError as exc:
                reservation_wait.cancel()
                with inflight_lock:
                    request_reservations.pop(request_id, None)
                router_event("admission_failed", profile=model, route=safe_route, code=exc.code)
                content = {"error": {"message": str(exc), "type": exc.code}}
                if exc.recovery is not None:
                    content["recovery"] = exc.recovery
                return JSONResponse(
                    status_code=exc.status_code,
                    content=content,
                    headers={"Retry-After": "1"} if exc.status_code == 429 else None,
                )
            except asyncio.CancelledError:
                reservation_wait.cancel()
                with inflight_lock:
                    request_reservations.pop(request_id, None)
                abandon_loading_acquisition(acquisition)
                raise
            except BaseException:
                reservation_wait.cancel()
                with inflight_lock:
                    request_reservations.pop(request_id, None)
                if not acquisition.done():
                    abandon_loading_acquisition(acquisition, record_cancellation=False)
                raise
            finally:
                if not reservation_wait.done():
                    reservation_wait.cancel()
        else:
            lease = None
        try:
            if lease is None:
                lease = await acquire_route(model, admission_cancellation)
        except RoutingError as exc:
            with inflight_lock:
                request_reservations.pop(request_id, None)
            router_event("admission_failed", profile=model, route=safe_route, code=exc.code)
            content = {"error": {"message": str(exc), "type": exc.code}}
            if exc.recovery is not None:
                content["recovery"] = exc.recovery
            return JSONResponse(
                status_code=exc.status_code,
                content=content,
                headers={"Retry-After": "1"} if exc.status_code == 429 else None,
            )
        except asyncio.CancelledError:
            with inflight_lock:
                request_reservations.pop(request_id, None)
            router.cancel_acquire(admission_cancellation)
            router.record_cancellation()
            router_event("request_cancelled", profile=model, route=safe_route)
            raise
        except BaseException:
            with inflight_lock:
                request_reservations.pop(request_id, None)
            raise
        with inflight_lock:
            cancelled_before_connect = request_reservations[request_id]["cancelled"]
            if cancelled_before_connect:
                request_reservations.pop(request_id, None)
        if cancelled_before_connect:
            lease.release()
            return JSONResponse(
                status_code=409,
                content={"error": {
                    "message": "request cancelled before upstream connection",
                    "type": "request_cancelled",
                }},
            )
        try:
            outbound_body = filtered_body(lease)
        except RequestModelError as exc:
            lease.release()
            with inflight_lock:
                request_reservations.pop(request_id, None)
            return JSONResponse(
                status_code=400,
                content={"error": {"message": str(exc), "type": "invalid_request"}},
            )
        try:
            upstream = await connect_upstream(
                port=lease.port,
                base_url=lease.proxy_base_url,
                path_and_query=path_and_query,
                headers=dict(request.headers),
                body=outbound_body,
                method=request.method,
                timeout_s=lease.profile.upstream_timeout_s or router.upstream_timeout_s,
            )
        except asyncio.CancelledError:
            lease.release()
            with inflight_lock:
                request_reservations.pop(request_id, None)
            router.record_cancellation()
            router_event("request_cancelled", profile=model, route=safe_route)
            raise
        except Exception as exc:  # the lease must not strand a pending swap on connect failure
            lease.release()
            with inflight_lock:
                request_reservations.pop(request_id, None)
            router_event("upstream_connect_failed", profile=model, route=safe_route)
            return JSONResponse(status_code=502, content={"error": {"message": str(exc), "type": "upstream_unavailable"}})
        except BaseException:
            lease.release()
            with inflight_lock:
                request_reservations.pop(request_id, None)
            raise
        with inflight_lock:
            cancelled_while_connecting = request_reservations[request_id]["cancelled"]
            if cancelled_while_connecting:
                request_reservations.pop(request_id, None)
            else:
                inflight[request_id] = {
                    "profile": lease.profile.name,
                    "upstream": upstream,
                    "cancelled": False,
                }
        if cancelled_while_connecting:
            upstream.close()
            lease.release()
            return JSONResponse(
                status_code=409,
                content={"error": {
                    "message": "request cancelled while opening upstream connection",
                    "type": "request_cancelled",
                }},
            )
        router_event("admitted", **lease_event_identity(lease), route=safe_route)

        def stream_response():
            first_byte_at = None
            byte_count = 0
            try:
                for chunk in upstream.chunks():
                    if first_byte_at is None:
                        first_byte_at = time.monotonic()
                    byte_count += len(chunk)
                    yield chunk
            finally:
                ended = time.monotonic()
                with inflight_lock:
                    item = inflight.get(request_id, {})
                    cancelled = bool(item.get("cancelled"))
                    if item.get("upstream") is upstream:
                        inflight.pop(request_id, None)
                    request_reservations.pop(request_id, None)
                router.record_stream(
                    ttft_s=(first_byte_at - started) if first_byte_at is not None else None,
                    duration_s=ended - started,
                    response_bytes=byte_count,
                    completed=not cancelled,
                )
                lease.release()
                router_event(
                    "request_finished",
                    **lease_event_identity(lease),
                    route=safe_route,
                    status=upstream.status,
                    cancelled=cancelled,
                    responseBytes=byte_count,
                )

        headers = response_headers(upstream.headers)
        headers["X-FT-Request-ID"] = request_id
        return StreamingResponse(
            stream_response(),
            status_code=upstream.status,
            headers=headers,
            media_type=upstream.headers.get("Content-Type"),
        )

    async def route_inference(request: Request):
        body = await request.body()
        try:
            model = request_model(body)
            if not router.has_routable_id(model):
                raise CatalogError(f"unknown model profile {model!r}")
        except RequestModelError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except CatalogError as exc:
            return JSONResponse(
                status_code=404,
                content={"error": {"message": str(exc), "type": "unknown_model"}},
            )
        suffix = f"?{request.url.query}" if request.url.query else ""
        return await forward_routed(
            request,
            model,
            path_and_query=request.url.path + suffix,
            body=body,
            apply_request_filters=True,
        )

    # FreeToken's supported inference surface. All routes use the same native
    # admission and proxy path so an OpenAI or Anthropic client cannot bypass
    # lifecycle, accounting, readiness, or cancellation ownership.
    @app.post("/v1/chat/completions", dependencies=[Depends(require_router_key)])
    @app.post("/v1/completions", dependencies=[Depends(require_router_key)])
    @app.post("/v1/responses", dependencies=[Depends(require_router_key)])
    @app.post("/v1/messages", dependencies=[Depends(require_router_key)])
    @app.post("/v1/messages/count_tokens", dependencies=[Depends(require_router_key)])
    async def inference_proxy(request: Request):
        return await route_inference(request)

    # FreeToken's Responses implementation is deliberately stateless. Keep its
    # registered resource routes available at the stable daemon URL, but do not
    # activate an arbitrary model for a request that carries no model identity.
    # The envelope matches the engine contract and remains behind inference auth.
    @app.get("/v1/responses/{response_id}", dependencies=[Depends(require_router_key)])
    @app.post(
        "/v1/responses/{response_id}/cancel",
        dependencies=[Depends(require_router_key)],
    )
    async def stateless_response_not_found(response_id: str):
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "message": f"response {response_id!r} not found (stateless server)",
                    "type": "invalid_request_error",
                    "code": None,
                }
            },
        )

    @app.get("/models", dependencies=[Depends(require_router_key)])
    @app.get("/v1/models", dependencies=[Depends(require_router_key)])
    async def openai_model_list(request: Request):
        """OpenAI-compatible public metadata without exposing local model paths."""
        catalog_snapshot, loaded_profiles, active_routing_profile = (
            router.public_model_listing_snapshot()
        )
        created = int(time.time())
        data = []
        for model_id in catalog_snapshot.listed_model_ids():
            selector = catalog_snapshot.selector(model_id)
            profile = None if selector is not None else catalog_snapshot.get(model_id)
            if selector is None:
                loaded = profile.name in loaded_profiles
            else:
                targets = selector.targets[:1] if selector.strategy == "pin" else selector.targets
                loaded = any(
                    catalog_snapshot.get(target).name in loaded_profiles for target in targets
                )
            record = {
                "id": model_id,
                "object": "model",
                "created": created,
                "owned_by": "freetoken",
                "status": {
                    "value": "loaded" if loaded else "unloaded"
                },
            }
            if selector is not None:
                if selector.display_name:
                    record["name"] = selector.display_name
                if selector.description:
                    record["description"] = selector.description
                selector_metadata = selector.metadata()
                selector_metadata.update({
                    "type": "selector",
                    "strategy": selector.strategy,
                    "targets": list(selector.targets),
                })
                record["meta"] = {"freetoken": selector_metadata}
            if profile is not None:
                if profile.display_name:
                    record["name"] = profile.display_name.strip()
                if profile.description:
                    record["description"] = profile.description.strip()
                capability_fields = profile.capabilities.model_listing_fields()
                record.update(capability_fields)
                metadata = profile.metadata()
                if not profile.capabilities.empty():
                    for key in (
                        "architecture", "capabilities", "supported_parameters",
                        "context_length", "context_window",
                    ):
                        metadata.pop(key, None)
                if model_id == profile.name:
                    internal_metadata = {"type": "model"}
                    if profile.aliases:
                        internal_metadata["aliases"] = list(profile.aliases)
                else:
                    internal_metadata = {"type": "alias", "modelID": profile.name}
                metadata.update(internal_metadata)
                record.setdefault("meta", {})["freetoken"] = metadata
            data.append(record)
        routing_profile = (
            catalog_snapshot.routing_profile(active_routing_profile)
            if active_routing_profile is not None else None
        )
        if routing_profile is not None:
            for pin, target in routing_profile.pins:
                if target is None or catalog_snapshot.has_routable_id(pin):
                    continue
                data.append({
                    "id": pin,
                    "object": "model",
                    "created": created,
                    "owned_by": "freetoken",
                    "status": {"value": "unloaded"},
                    "meta": {"freetoken": {"type": "profile"}},
                })
        response = JSONResponse(content={
            "object": "list",
            "data": data,
        })
        if origin := request.headers.get("origin"):
            response.headers["Access-Control-Allow-Origin"] = origin
        return response

    @app.api_route(
        "/upstream/{upstream_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        dependencies=[Depends(require_router_key)],
    )
    async def upstream_proxy(request: Request, upstream_path: str):
        try:
            source_model, model, _, remaining_path = router.resolve_upstream_path(
                upstream_path
            )
        except CatalogError as exc:
            return JSONResponse(
                status_code=404,
                content={"error": {"message": str(exc), "type": "unknown_model"}},
            )
        # The daemon alone may call prepare-stop. Exposing it through an
        # arbitrary passthrough would bypass durable accounting and leave a
        # misleading routing lease behind.
        normalized = remaining_path.lstrip("/")
        if normalized == "v1/admin/prepare-stop":
            raise HTTPException(status_code=403, detail="upstream prepare-stop is daemon-managed")
        raw_path = request.scope.get("raw_path")
        escaped_path = (
            _escaped_path_suffix(raw_path, f"/upstream/{source_model}")
            if isinstance(raw_path, bytes) else None
        )
        if escaped_path is None:
            raise HTTPException(status_code=400, detail="invalid escaped upstream path")
        if not escaped_path:
            escaped_path = "/"
        raw_query = request.scope.get("query_string", b"")
        suffix = f"?{raw_query.decode('ascii')}" if raw_query else ""
        return await forward_routed(
            request,
            model,
            path_and_query=escaped_path + suffix,
            body=await request.body(),
            apply_request_filters="application/json" in request.headers.get(
                "content-type", ""
            ).lower(),
        )

    @app.get("/router/status", dependencies=auth)
    async def router_status():
        return {**router.status(), "catalogWatch": catalog_watch_snapshot()}

    @app.get("/router/models", dependencies=auth)
    async def router_models():
        """Configured profiles annotated with the sole engine's live residency."""
        catalog_snapshot, route_state = router.control_plane_snapshot()
        engine = manager.status()
        active = route_state["activeProfile"]
        active_identity_matches = route_state["activeIdentityMatchesEngine"]
        data = []
        for profile in catalog_snapshot.public():
            profile = dict(profile)
            profile["configured"] = True
            profile["resident"] = (
                profile["name"] == active and bool(engine.get("running")) and active_identity_matches
            )
            profile["activeRequests"] = route_state["activeRequests"] if profile["resident"] else 0
            data.append(profile)
        return {
            "data": data,
            "selectors": catalog_snapshot.public_selectors(),
            "routingProfiles": catalog_snapshot.public_routing_profiles(),
            "activeRoutingProfile": route_state["activeRoutingProfile"],
            "capacity": route_state["capacity"],
        }

    @app.get("/router/profiles", dependencies=auth)
    async def router_profiles():
        catalog_snapshot, route_state = router.control_plane_snapshot()
        return {
            "data": catalog_snapshot.public(),
            "selectors": catalog_snapshot.public_selectors(),
            "routingProfiles": catalog_snapshot.public_routing_profiles(),
            "activeRoutingProfile": route_state["activeRoutingProfile"],
            "activeProfile": route_state["activeProfile"],
        }

    @app.put("/router/profiles/active", dependencies=auth)
    async def set_active_routing_profile(body: RoutingProfileSelectionBody):
        try:
            active = router.set_active_routing_profile(body.name)
        except RoutingError as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": {"message": str(exc), "type": exc.code}},
            )
        router_event("routing_profile_changed", routingProfile=active)
        return {"active": active}

    @app.get("/router/hardware", dependencies=auth)
    async def router_hardware():
        """Small, privacy-preserving local memory view for the management UI."""
        engine = manager.status()
        footprint = await run(proxy_pool, footprint_fn, engine.get("pid"))
        return {
            "engine": {
                "running": bool(engine.get("running")),
                "pid": engine.get("pid"),
                "port": engine.get("port"),
            },
            "memory": footprint,
        }

    @app.get("/router/requests", dependencies=auth)
    async def router_requests():
        with inflight_lock:
            data = [{"id": request_id, "profile": item["profile"]}
                    for request_id, item in request_reservations.items()]
        return {"data": data}

    @app.post("/router/requests/{request_id}/cancel", dependencies=auth)
    async def router_cancel(request_id: str):
        with inflight_lock:
            item = inflight.get(request_id)
            reservation = request_reservations.get(request_id)
            if reservation is not None and not reservation["cancelled"]:
                reservation["cancelled"] = True
                cancellation = reservation["cancellation"]
            else:
                cancellation = None
            if item is not None and cancellation is not None:
                item["cancelled"] = True
        if cancellation is None:
            return {"cancelled": False, "reason": "not_found"}
        if item is None:
            router.cancel_acquire(cancellation)
            profile = reservation["profile"]
        else:
            item["upstream"].close()
            profile = item["profile"]
        router.record_cancellation()
        router_event("request_cancelled", profile=profile)
        return {"cancelled": True, "id": request_id}

    @app.get("/router/logs", dependencies=auth)
    async def router_logs(request: Request, since: int = 0):
        """Bounded lifecycle/proxy event stream, separate from engine stdout."""
        return _log_stream(request, router_ring, since)

    @app.get("/metrics", dependencies=auth)
    async def router_metrics():
        return PlainTextResponse(router.prometheus(), media_type="text/plain; version=0.0.4")

    @app.post("/router/unload", dependencies=auth)
    async def router_unload(body: RouterUnloadBody | None = None):
        try:
            unloaded = await run(lifecycle_pool, router.evict_idle, body.name if body else None)
        except (AccountingPrepareError, AccountingOutboxError) as exc:
            return accounting_error(exc)
        return {"unloaded": unloaded, "router": router.status()}

    @app.post("/router/load", dependencies=auth)
    async def router_load(body: RouterLoadBody):
        """Activate one profile without inventing a synthetic inference request.

        The short lease still uses the identical admission, readiness, switch,
        accounting, and rollback transaction as automatic routing. Releasing it
        afterwards permits the configured idle-TTL policy to apply normally.
        """
        try:
            lease = await acquire_route(body.name, apply_routing_profile=False)
        except RoutingError as exc:
            router_event("management_load_failed", profile=body.name, code=exc.code)
            content = {"error": {"message": str(exc), "type": exc.code}}
            if exc.recovery is not None:
                content["recovery"] = exc.recovery
            return JSONResponse(
                status_code=exc.status_code,
                content=content,
                headers={"Retry-After": "1"} if exc.status_code == 429 else None,
            )
        try:
            result = {"profile": lease.profile.name, "port": lease.port, "pid": lease.pid}
        finally:
            lease.release()
        router_event("management_loaded", profile=lease.profile.name)
        return {**result, "router": router.status()}

    @app.post("/router/reload", dependencies=auth)
    async def router_reload():
        if not catalog_path:
            raise HTTPException(status_code=409, detail="catalog reload requires --catalog")
        try:
            replacement = await run(proxy_pool, ModelCatalog.load, catalog_path)
            await run(lifecycle_pool, router.replace_catalog, replacement)
        except CatalogError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RoutingError as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": {"message": str(exc), "type": exc.code}},
            )
        record_watch("reloaded")
        return {"reloaded": True, "models": router.catalog.public()}

    # ---- engine lifecycle ----

    def profile_request(name: str) -> tuple[str, int, list[str]]:
        profile = router.catalog.get(name)
        return profile.model, resolve_port(profile.port), list(profile.args)

    def profile_result(name: str, result: dict, port: int):
        profile = router.catalog.get(name)
        readiness = wait_for_ready(
            manager,
            probe,
            pid=result.get("pid"),
            port=port,
            timeout_s=profile.ready_timeout_s,
            path=profile.check_endpoint,
        )

        content = {**result, "profile": name, "readiness": readiness}
        if not readiness["ready"]:
            return JSONResponse(status_code=503, content=content)
        return content

    @app.exception_handler(SwitchLaunchError)
    async def switch_launch_error(request: Request, exc: SwitchLaunchError):
        return JSONResponse(status_code=503, content={
            "code": "switch_launch_failed", "error": str(exc),
            "rollback": exc.rollback, "accounting": exc.accounting,
        })

    @app.post("/engine/start", dependencies=auth)
    async def engine_start(body: StartBody):
        async def operation():
            try:
                port = resolve_port(body.port)
                return await run(lifecycle_pool, manager.start, body.model, port, list(body.args))
            except Conflict as exc:
                st = manager.status()
                return JSONResponse(
                    status_code=409,
                    content={
                        "error": str(exc),
                        "code": "serve_conflict",
                        "currentModel": st.get("model"),
                        "currentPort": st.get("port"),
                    },
                )
            except Exception as exc:  # noqa: BLE001 — never propagate a 500-as-crash
                raise HTTPException(status_code=500, detail=f"start failed: {exc}")

        return await run_manual_transaction(operation)

    @app.post("/engine/stop", dependencies=auth)
    async def engine_stop(body: StopBody | None = None):
        async def operation():
            try:
                return await run(lifecycle_pool, manager.stop, None, bool(body and body.force))
            except (AccountingPrepareError, AccountingOutboxError) as exc:
                return accounting_error(exc)

        return await run_manual_transaction(operation, preempt_manual=True)

    @app.post("/shutdown", dependencies=auth)
    async def shutdown_daemon(request: Request, body: StopBody | None = None):
        # Tray "Stop daemon" stops everything: stop the engine FIRST so the default detach-on-exit can't
        # leave the ~18GB serve orphaned, THEN bring the daemon down. We reply before uvicorn
        # actually stops (it notices should_exit within ~0.1s) so the client still gets a clean 200.
        try:
            owner = router.begin_shutdown()
        except RoutingError as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": {"message": str(exc), "type": exc.code}},
            )

        async def operation():
            try:
                stopped = await run(
                    lifecycle_pool,
                    router.finish_shutdown,
                    owner,
                    None,
                    bool(body and body.force),
                )
            except (AccountingPrepareError, AccountingOutboxError) as exc:
                return accounting_error(exc)
            req = getattr(request.app.state, "request_shutdown", None)
            if req is not None:
                req()
            return {
                "stopping": True,
                "already": stopped.get("already", False),
                "accounting": stopped.get("accounting"),
            }

        return await run_to_completion(operation)

    @app.post("/engine/switch", dependencies=auth)
    async def engine_switch(body: SwitchBody):
        async def operation():
            try:
                port = resolve_port(body.port)
                return await run(
                    lifecycle_pool,
                    manager.switch,
                    body.model,
                    port,
                    list(body.args),
                    body.force,
                )
            except (AccountingPrepareError, AccountingOutboxError) as exc:
                return accounting_error(exc)
            except Exception as exc:  # noqa: BLE001
                if isinstance(exc, SwitchLaunchError):
                    raise
                raise HTTPException(status_code=500, detail=f"switch failed: {exc}")

        return await run_manual_transaction(operation)

    @app.post("/engine/start-profile", dependencies=auth)
    async def engine_start_profile(body: ProfileBody):
        async def operation():
            try:
                model, port, args = profile_request(body.name)
                result = await run(lifecycle_pool, manager.start, model, port, args)
                return await run(proxy_pool, profile_result, body.name, result, port)
            except CatalogError as exc:
                raise HTTPException(status_code=404, detail=str(exc))
            except Conflict as exc:
                st = manager.status()
                return JSONResponse(
                    status_code=409,
                    content={
                        "error": str(exc),
                        "code": "serve_conflict",
                        "currentModel": st.get("model"),
                        "currentPort": st.get("port"),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=500, detail=f"profile start failed: {exc}")

        return await run_manual_transaction(operation)

    @app.post("/engine/switch-profile", dependencies=auth)
    async def engine_switch_profile(body: ProfileBody):
        async def operation():
            try:
                model, port, args = profile_request(body.name)
                result, ticket = await run(
                    lifecycle_pool, manager.switch_for_readiness, model, port, args, body.force
                )
                response = await run(proxy_pool, profile_result, body.name, result, port)
                if not isinstance(response, JSONResponse):
                    return response
                content = json.loads(response.body)
                rollback = await run(lifecycle_pool, manager.recover_switch, ticket, body.force)
                if rollback.get("launched"):
                    profile = router.catalog.get(body.name)
                    rollback["readiness"] = await run(proxy_pool, functools.partial(
                        wait_for_ready, manager, probe, pid=rollback["pid"],
                        port=rollback["port"], timeout_s=profile.ready_timeout_s,
                    ))
                content["rollback"] = rollback
                return JSONResponse(status_code=503, content=content)
            except CatalogError as exc:
                raise HTTPException(status_code=404, detail=str(exc))
            except (AccountingPrepareError, AccountingOutboxError) as exc:
                return accounting_error(exc)
            except Exception as exc:  # noqa: BLE001
                if isinstance(exc, SwitchLaunchError):
                    raise
                raise HTTPException(status_code=500, detail=f"profile switch failed: {exc}")

        return await run_manual_transaction(operation)

    # ---- durable accounting outbox ----

    @app.get("/accounting/pending", dependencies=auth)
    async def accounting_pending():
        try:
            receipts = await run(lifecycle_pool, manager.pending_accounting)
        except AccountingOutboxError as exc:
            return accounting_error(exc)
        return {"receipts": receipts}

    @app.post("/accounting/ack", dependencies=auth)
    async def accounting_ack(body: AccountingAckBody):
        try:
            return await run(lifecycle_pool, manager.ack_accounting, body.receiptId)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except AccountingOutboxError as exc:
            return accounting_error(exc)

    @app.get("/engine/status", dependencies=auth)
    async def engine_status():
        return manager.status()

    @app.get("/engine/metrics", dependencies=auth)
    async def engine_metrics():
        pid = manager.current_pid()
        return await run(proxy_pool, footprint_fn, pid)

    @app.get("/engine/health", dependencies=auth)
    async def engine_health():
        st = manager.status()
        if not st.get("running"):
            return {"reachable": False, "running": False, "daemon": "up", **_engine_summary(st)}
        port = st.get("port") or default_serve_port
        doc = await run(proxy_pool, probe.health, port)
        # The serve's own health fields (status/model/uptimeS/progress) are authoritative for
        # "how is the model doing?"; the daemon only layers on what only it knows, never clobbering
        # the serve's values.
        doc["running"] = True
        doc["daemon"] = "up"
        doc.setdefault("port", st.get("port"))
        doc.setdefault("pid", st.get("pid"))
        doc.setdefault("lastExitCode", st.get("lastExitCode"))
        return doc

    @app.get("/engine/stats", dependencies=auth)
    async def engine_stats():
        st = manager.status()
        if not st.get("running"):
            return {"reachable": False, "running": False}
        port = st.get("port") or default_serve_port
        doc = await run(proxy_pool, probe.stats, port)
        manager.observe_accounting(doc)
        return doc

    @app.get("/engine/logs", dependencies=auth)
    async def engine_logs(request: Request, since: int = 0):
        return _log_stream(request, ring, since)

    # ---- checkpoint (phase 3; optional) ----

    if checkpoints is not None:

        @app.post("/checkpoint/start", dependencies=auth)
        async def checkpoint_start(body: CheckpointBody):
            # GPU exclusivity: a convert needs the GPU, so stop any serve first.
            await run(lifecycle_pool, manager.stop)
            try:
                return await run(lifecycle_pool, checkpoints.start, body.id, list(body.args))
            except Conflict as exc:
                raise HTTPException(status_code=409, detail=str(exc))
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=500, detail=f"checkpoint start failed: {exc}")

        @app.post("/checkpoint/cancel", dependencies=auth)
        async def checkpoint_cancel(body: CancelBody):
            return await run(lifecycle_pool, checkpoints.cancel, body.id)

        @app.get("/checkpoint/status", dependencies=auth)
        async def checkpoint_status():
            return checkpoints.status()

    # ---- hardware bandwidth bench (hardware-adaptive config) ----

    @app.post("/bench/run", dependencies=auth)
    async def bench_run(body: BenchBody):
        # GPU exclusivity: the bench allocates transient device memory, so stop any serve first
        # (mirrors /checkpoint/start). Runs `ft bench bw` on the engine HOST (so the profile lands
        # where this daemon's serve reads it) and STREAMS progress back as SSE: `progress` events
        # per measured format, then a terminal `result` (the profile) or `error` event. `body.args`
        # is the raw arg list, so any `ft bench bw` flag (--dtype/--model/--threshold/...) passes
        # through. torch stays out of the daemon (child process), which also frees VRAM on exit.
        await run(lifecycle_pool, manager.stop)

        async def gen():
            env = {**os.environ, "FREETOKEN_BENCH_PROGRESS": "1"}
            argv = [sys.executable, "-m", "freetoken.cli", "bench", "bw", *body.args]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, env=env
                )
            except Exception as exc:  # noqa: BLE001
                yield _bench_sse("error", {"message": f"failed to spawn bench: {exc}"})
                return
            tail: collections.deque = collections.deque(maxlen=8)  # last non-progress lines (errors)
            out_path: str | None = None
            assert proc.stdout is not None
            async for raw in proc.stdout:
                line = raw.decode(errors="replace").rstrip()
                prog = _parse_ftbench(line)
                if prog is not None:
                    yield _bench_sse("progress", prog)
                elif line.startswith("FTBENCH_OUT "):
                    out_path = line[len("FTBENCH_OUT "):]
                elif line:
                    tail.append(line)
            rc = await proc.wait()
            if rc != 0:
                yield _bench_sse("error", {"message": "\n".join(tail) or f"bench exited {rc}"})
                return
            # the file this run wrote (an older engine prints no FTBENCH_OUT: newest file, as before)
            prof = _read_bench_profile(out_path or _bench_profile_path(None))
            if prof is None:
                yield _bench_sse("error", {"message": "bench finished but no profile was written"})
            else:
                yield _bench_sse("result", prof)

        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.get("/bench/profile", dependencies=auth)
    async def bench_profile():
        def read() -> dict | None:
            return _read_bench_profile(_bench_profile_path(serve_gpu_uuid()))

        def serve_gpu_uuid() -> str | None:
            # the running serve reports the full UUID of its card (/v1/stats gpus); a --gpu given as
            # a UUID prefix would not match the profile file name
            st = manager.status()
            if st.get("running"):
                try:
                    gpus = probe.stats(st.get("port") or default_serve_port).get("gpus") or []
                    if gpus and gpus[0].get("uuid"):
                        return gpus[0]["uuid"]
                except Exception:  # noqa: BLE001 -- the arg below is the fallback
                    pass
            return _serve_gpu_uuid(manager.serve_args())

        return await run(proxy_pool, read)

    return app


def _engine_summary(st: dict) -> dict:
    return {
        "model": st.get("model"),
        "port": st.get("port"),
        "pid": st.get("pid"),
        "uptimeS": st.get("uptimeS", 0),
        "lastExitCode": st.get("lastExitCode"),
    }


def _sse(rec: dict) -> str:
    return f"id: {rec['seq']}\ndata: {json.dumps(rec)}\n\n"


def _sse_gap(dropped: int, from_seq: Any, to_seq: Any) -> str:
    payload = {"kind": "gap", "dropped": dropped, "fromSeq": from_seq, "toSeq": to_seq}
    return f"data: {json.dumps(payload)}\n\n"


def _log_stream(request: Request, ring, since: int) -> StreamingResponse:
    """SSE log stream with replay + live tail. Correctness points:
      * subscribe BEFORE snapshotting the backlog, then dedupe live records by seq → no gap and
        no duplicate across the replay→live boundary;
      * per-subscriber bounded queue, drop-oldest on overflow via ``call_soon_threadsafe`` (the
        mutation runs on the loop thread, so the reader never blocks) and a client-visible gap
        sentinel so a slow client knows it lost lines;
      * ``id:<seq>`` on every frame + ``Last-Event-ID`` honoured for native EventSource resume;
      * a 15 s heartbeat + ``is_disconnected`` check so an idle client's disconnect is detected
        and the subscriber is always removed in ``finally`` (no leak)."""
    loop = asyncio.get_running_loop()
    lei = request.headers.get("last-event-id")
    if lei and lei.isdigit():
        since = int(lei) + 1  # exclusive next-cursor

    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    drop = {"n": 0, "from": None, "to": None}
    # Records with seq < boundary are already covered by the replayed backlog (they landed in the
    # window between subscribe and the snapshot). Skipping them here keeps the gap counters honest
    # — only genuinely-lost LIVE lines feed drop[]. Safe to set after subscribe: the
    # scheduled _put callbacks only run once this handler yields control, by which point boundary
    # is set.
    boundary = {"v": 0}

    def push(rec: dict) -> None:
        def _put() -> None:
            if rec["seq"] < boundary["v"]:
                return  # already delivered via backlog; don't enqueue or count it as dropped
            if q.full():
                try:
                    old = q.get_nowait()
                    drop["n"] += 1
                    if drop["from"] is None:
                        drop["from"] = old["seq"]
                    drop["to"] = old["seq"]
                except asyncio.QueueEmpty:  # pragma: no cover - race-only
                    pass
            q.put_nowait(rec)

        try:
            loop.call_soon_threadsafe(_put)
        except RuntimeError:  # loop is closing during shutdown
            pass

    ring.subscribe(push)
    backlog, cursor = ring.since(since)
    boundary["v"] = cursor

    async def gen():
        try:
            # If the ring evicted records at/after the client's cursor before it (re)connected,
            # announce that lost prefix so the client knows its history is incomplete.
            oldest = backlog[0]["seq"] if backlog else cursor
            if oldest > since:
                yield _sse_gap(oldest - since, since, oldest - 1)
            for rec in backlog:
                yield _sse(rec)
            last_seq = cursor - 1
            while True:
                if await request.is_disconnected():
                    break
                try:
                    rec = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                if rec["seq"] <= last_seq:
                    continue  # already delivered in backlog
                if drop["n"]:
                    # Snapshot + reset synchronously BEFORE yielding: during the yield the loop
                    # drains more _put callbacks that may mutate drop[], and those must not be
                    # wiped unreported.
                    n, frm, to = drop["n"], drop["from"], drop["to"]
                    drop["n"], drop["from"], drop["to"] = 0, None, None
                    yield _sse_gap(n, frm, to)
                last_seq = rec["seq"]
                yield _sse(rec)
        finally:
            ring.unsubscribe(push)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
