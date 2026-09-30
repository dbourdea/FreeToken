"""The daemon's HTTP control plane. camelCase JSON throughout. Loopback by default; an optional
``X-FT-Token`` shared secret gates everything except the daemon's own ``/health`` liveness probe.

Handlers are ``async`` and push every blocking call to an executor so the event loop never
blocks. Two executors: a small **lifecycle** pool for start/stop/switch, kept separate from the
**proxy/metrics** pool, so a storm of health/metrics polls against a loading serve can never
starve an operator's stop."""

from __future__ import annotations

import asyncio
# What: import base64 for extract api key using base64; why: _extract_api_key uses base64 b64decode, making that imported dependency available to its named operation.
import base64
# What: import binascii for extract api key using binascii; why: _extract_api_key uses binascii error, making that imported dependency available to its named operation.
import binascii
import collections
# What: import datetime for router performance using datetime and datetime; why: router_performance uses datetime fromisoformat, making that imported dependency available to its named operation.
from datetime import datetime
import functools
import json
import os
# What: import re for module initialization using re; why: module initialization uses re compile, making that imported dependency available to its named operation.
import re
import sys
# What: import threading for build app using threading; why: build_app uses threading lock, making that imported dependency available to its named operation.
import threading
# What: import time for forward routed using time; why: forward_routed uses time monotonic, making that imported dependency available to its named operation.
import time
# What: import uuid for forward routed using uuid; why: forward_routed uses uuid uuid4, making that imported dependency available to its named operation.
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable
# What: import quote from bytes for escaped path suffix using urllib and parse and quote from bytes; why: _escaped_path_suffix uses quote from bytes, making that imported dependency available to its named operation.
from urllib.parse import quote_from_bytes

# What: import from fastapi import Depends FastAPI Header HTTPException Query Request; why: this module calls or annotates these symbols in the branch-created operations below.
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
# What: import from fastapi responses import HTMLResponse JSONResponse PlainTextResponse Response StreamingResponse; why: this module calls or annotates these symbols in the branch-created operations below.
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response, StreamingResponse
from pydantic import BaseModel

from .accounting import AccountingOutboxError, AccountingPrepareError
# What: import activity store for build app using activity and activity store; why: build_app uses activity store, making that imported dependency available to its named operation.
from .activity import ActivityStore
# What: import from catalog import CatalogError ModelCatalog; why: this module calls or annotates these symbols in the branch-created operations below.
from .catalog import CatalogError, ModelCatalog
# What: import from inference proxy import; why: this module calls or annotates these symbols in the branch-created operations below.
from .inference_proxy import (
    # What: execute RequestModelError; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
    RequestModelError,
    # What: execute filter request body; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
    filter_request_body,
    # What: execute open upstream; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
    open_upstream,
    # What: execute request model; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
    request_model,
    # What: execute response headers; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
    response_headers,
# What: complete the enclosing predicate with from inference proxy import request model error filter request body open upstream request model response headers; why: app groups the supplied clauses as one enclosing predicate expression before its value is consumed.
)
# What: import log ring for build app using logring and log ring; why: build_app uses the log ring annotation in build app, making that imported dependency available to its named operation.
from .logring import LogRing
# What: import performance monitor for build app using performance and performance monitor; why: build_app uses performance monitor, making that imported dependency available to its named operation.
from .performance import PerformanceMonitor
# What: import wait for ready for profile result using readiness and wait for ready; why: profile_result uses wait for ready, making that imported dependency available to its named operation.
from .readiness import wait_for_ready
# What: import from router import RoutingCoordinator RoutingError allocate loopback port; why: this module calls or annotates these symbols in the branch-created operations below.
from .router import RoutingCoordinator, RoutingError, allocate_loopback_port
# What: import from serve manager import Conflict SwitchLaunchError; why: this module calls or annotates these symbols in the branch-created operations below.
from .serve_manager import Conflict, SwitchLaunchError
from .version import DAEMON_VERSION


# What: compute http token from compile and re and value and a za z; why: if part raw strip and http token fullmatch part later reads http token, so app must retain the computed value under that name.
_HTTP_TOKEN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
# What: compute default cors headers from content type and authorization and accept and x requested with; why: return default cors headers later reads default cors headers, so app must retain the computed value under that name.
_DEFAULT_CORS_HEADERS = "Content-Type, Authorization, Accept, X-Requested-With"


# What: define _cors_request_headers around value; why: its direct callers call _cors_request_headers for cors request headers and rely on this exact input and result contract.
def _cors_request_headers(value: str | None) -> str:
    """Echo only syntactically valid HTTP header names in a CORS preflight."""
    # What: document echo only syntactically valid http header in the _cors_request_headers docstring; why: introspection and maintainers read this exact docstring fragment to understand cors request headers behavior without executing it.
    # What: gate on value before default cors headers; why: _cors_request_headers admits default cors headers only for this predicate and excludes the opposite state.
    if value is None:
        # What: return default cors headers from _cors_request_headers; why: _cors_request_headers exposes default cors headers so its caller can continue with the function\'s computed outcome.
        return _DEFAULT_CORS_HEADERS
    # What: return join and part and raw and split from _cors_request_headers; why: _cors_request_headers exposes join and part and raw and split so its caller can continue with the function\'s computed outcome.
    return ", ".join(
        # What: call value.split with value; why: _cors_request_headers invokes value.split while performing if part raw strip and http token fullmatch part; the call advances that operation through its result or side effect.
        part for raw in value.split(",")
        # What: call _HTTP_TOKEN.fullmatch with part; why: _cors_request_headers consumes the _HTTP_TOKEN.fullmatch return value while evaluating if (part := raw.strip()) and _HTTP_TOKEN.fullmatch(part).
        if (part := raw.strip()) and _HTTP_TOKEN.fullmatch(part)
    # What: complete the operation.join call with part; why: _cors_request_headers groups the supplied clauses as one operation.join call before its value is consumed.
    )


# What: define _escaped_path_suffix around raw path and decoded prefix; why: its direct callers call _escaped_path_suffix for escaped path suffix and rely on this exact input and result contract.
def _escaped_path_suffix(raw_path: bytes, decoded_prefix: str) -> str | None:
    """Remove a decoded prefix while retaining the suffix's original escaping."""
    # What: document remove a decoded prefix while retaining in the _escaped_path_suffix docstring; why: introspection and maintainers read this exact docstring fragment to understand escaped path suffix behavior without executing it.
    # What: compute prefix from encode and decoded prefix and utf 8; why: while raw index len raw path and prefix index later reads prefix, so _escaped_path_suffix must retain the computed value under that name.
    prefix = decoded_prefix.encode("utf-8")
    # What: compute raw index from 0; why: while raw index len raw path and prefix index later reads raw index, so _escaped_path_suffix must retain the computed value under that name.
    raw_index = prefix_index = 0
    # What: iterate across raw index and prefix index and len and raw path and prefix to perform end and raw index; why: _escaped_path_suffix repeats the body only while or for the loop header admits an iteration.
    while raw_index < len(raw_path) and prefix_index < len(prefix):
        # What: compute end from raw index and 1; why: end raw index later reads end, so _escaped_path_suffix must retain the computed value under that name.
        end = raw_index + 1
        # What: compute value from raw path and raw index; why: if value ord later reads value, so _escaped_path_suffix must retain the computed value under that name.
        value = raw_path[raw_index]
        # What: gate on value and ord before raw index and len and raw path; why: _escaped_path_suffix admits raw index and len and raw path only for this predicate and excludes the opposite state.
        if value == ord("%"):
            # What: gate on raw index and len and raw path before the computed value; why: _escaped_path_suffix admits the computed value only for this predicate and excludes the opposite state.
            if raw_index + 3 > len(raw_path):
                # What: reject the malformed or mismatched escaped path; why: the upstream proxy returns no suffix so its caller emits HTTP 400 instead of forwarding ambiguous path bytes.
                return None
            # What: establish the handler boundary for the protected operation; why: _escaped_path_suffix routes failures to value error while preserving cleanup and success flow.
            try:
                # What: compute value from int and raw path and raw index and 16 and 1; why: if value prefix prefix index later reads value, so _escaped_path_suffix must retain the computed value under that name.
                value = int(raw_path[raw_index + 1:raw_index + 3], 16)
            # What: handle value error by return; why: _escaped_path_suffix converts that failure into this concrete recovery, response, or cleanup behavior.
            except ValueError:
                # What: reject the malformed or mismatched escaped path; why: the upstream proxy returns no suffix so its caller emits HTTP 400 instead of forwarding ambiguous path bytes.
                return None
            # What: compute end from raw index and 3; why: raw index end later reads end, so _escaped_path_suffix must retain the computed value under that name.
            end = raw_index + 3
        # What: gate on value and prefix and prefix index before the computed value; why: _escaped_path_suffix admits the computed value only for this predicate and excludes the opposite state.
        if value != prefix[prefix_index]:
            # What: reject the malformed or mismatched escaped path; why: the upstream proxy returns no suffix so its caller emits HTTP 400 instead of forwarding ambiguous path bytes.
            return None
        # What: compute raw index from end; why: suffix raw path raw index later reads raw index, so _escaped_path_suffix must retain the computed value under that name.
        raw_index = end
        # What: compute prefix index from 1; why: if prefix index len prefix later reads prefix index, so _escaped_path_suffix must retain the computed value under that name.
        prefix_index += 1
    # What: gate on prefix index and len and prefix before the computed value; why: _escaped_path_suffix admits the computed value only for this predicate and excludes the opposite state.
    if prefix_index != len(prefix):
        # What: reject the malformed or mismatched escaped path; why: the upstream proxy returns no suffix so its caller emits HTTP 400 instead of forwarding ambiguous path bytes.
        return None
    # What: compute suffix from raw path and raw index; why: return suffix decode ascii later reads suffix, so _escaped_path_suffix must retain the computed value under that name.
    suffix = raw_path[raw_index:]
    # What: establish the handler boundary for the protected operation; why: _escaped_path_suffix routes failures to unicode decode error while preserving cleanup and success flow.
    try:
        # What: return decode and suffix and ascii from _escaped_path_suffix; why: _escaped_path_suffix exposes decode and suffix and ascii so its caller can continue with the function\'s computed outcome.
        return suffix.decode("ascii")
    # What: handle unicode decode error by return quote from bytes suffix safe value; why: _escaped_path_suffix converts that failure into this concrete recovery, response, or cleanup behavior.
    except UnicodeDecodeError:
        # What: return quote from bytes and suffix and value from _escaped_path_suffix; why: _escaped_path_suffix exposes quote from bytes and suffix and value so its caller can continue with the function\'s computed outcome.
        return quote_from_bytes(suffix, safe="/%:@!$&'()*+,;=-._~")


# What: define _extract_api_key around authorization and x api key; why: its direct callers call _extract_api_key for extract api key and rely on this exact input and result contract.
def _extract_api_key(authorization: str | None, x_api_key: str | None) -> str | None:
    """Apply the pinned Basic-password, Bearer, then x-api-key contract."""
    # What: document apply the pinned basic password bearer then in the _extract_api_key docstring; why: introspection and maintainers read this exact docstring fragment to understand extract api key behavior without executing it.
    # What: compute bearer key from the named fixture input; why: bearer key credentials or later reads bearer key, so _extract_api_key must retain the computed value under that name.
    bearer_key = None
    # What: compute basic key from the named fixture input; why: basic key decoded split or later reads basic key, so _extract_api_key must retain the computed value under that name.
    basic_key = None
    # What: gate on authorization before scheme and separator and credentials and partition and authorization; why: _extract_api_key admits scheme and separator and credentials and partition and authorization only for this predicate and excludes the opposite state.
    if authorization:
        # What: compute scheme and separator and credentials from partition and authorization and value; why: if separator and scheme lower bearer later reads scheme and separator and credentials, so _extract_api_key must retain the computed value under that name.
        scheme, separator, credentials = authorization.partition(" ")
        # What: gate on separator and lower and scheme before bearer key and credentials; why: _extract_api_key admits bearer key and credentials only for this predicate and excludes the opposite state.
        if separator and scheme.lower() == "bearer":
            # What: compute bearer key from credentials; why: return basic key or bearer key or x api key later reads bearer key, so _extract_api_key must retain the computed value under that name.
            bearer_key = credentials or None
        # What: gate on separator and lower and scheme before decoded and decode and error and value error and basic key; why: _extract_api_key admits decoded and decode and error and value error and basic key only for this predicate and excludes the opposite state.
        elif separator and scheme.lower() == "basic":
            # What: establish the handler boundary for the protected operation; why: _extract_api_key routes failures to error and value error and binascii while preserving cleanup and success flow.
            try:
                # What: compute decoded from decode and b64decode and credentials and base64 and utf 8; why: if in decoded later reads decoded, so _extract_api_key must retain the computed value under that name.
                decoded = base64.b64decode(credentials, validate=True).decode(
                    # What: supply errors to operation.decode; why: _extract_api_key binds this surrogateescape value to operation.decode's errors input.
                    "utf-8", errors="surrogateescape"
                # What: complete the operation.decode call with errors; why: _extract_api_key groups the supplied clauses as one operation.decode call before its value is consumed.
                )
            # What: handle error and value error and binascii by pass; why: _extract_api_key converts that failure into this concrete recovery, response, or cleanup behavior.
            except (binascii.Error, ValueError):
                # What: ignore the anticipated exception handled by this branch; why: _extract_api_key continues its retry or cleanup path instead of re-raising that transient failure.
                pass
            # What: select the remaining branch that performs if in decoded; why: _extract_api_key covers the state excluded by the preceding predicate without conflating the two outcomes.
            else:
                # What: gate on decoded before basic key and split and decoded; why: _extract_api_key admits basic key and split and decoded only for this predicate and excludes the opposite state.
                if ":" in decoded:
                    # What: compute basic key from split and decoded and 1 and value and 1; why: return basic key or bearer key or x api key later reads basic key, so _extract_api_key must retain the computed value under that name.
                    basic_key = decoded.split(":", 1)[1] or None
    # What: return basic key and bearer key and x api key from _extract_api_key; why: _extract_api_key exposes basic key and bearer key and x api key so its caller can continue with the function\'s computed outcome.
    return basic_key or bearer_key or x_api_key


class StartBody(BaseModel):
    model: str
    port: int | None = None
    args: list[str] = []


class StopBody(BaseModel):
    force: bool = False


class SwitchBody(StartBody):
    force: bool = False


# What: define ProfileBody as the owner of its declared state; why: daemon callers use this class boundary so those methods share one profile body state invariant.
class ProfileBody(BaseModel):
    # What: compute name from the named fixture input; why: name str later reads name, so  app must retain the computed value under that name.
    name: str
    # What: compute force from false; why: return await run lifecycle pool manager stop bool later reads force, so app must retain the computed value under that name.
    force: bool = False


# What: define RoutingProfileSelectionBody as the owner of its declared state; why: daemon callers use this class boundary so those methods share one routing profile selection body state invariant.
class RoutingProfileSelectionBody(BaseModel):
    # What: compute name from the named fixture input; why: name str later reads name, so  app must retain the computed value under that name.
    name: str | None


# What: define RouterUnloadBody as the owner of its declared state; why: daemon callers use this class boundary so those methods share one router unload body state invariant.
class RouterUnloadBody(BaseModel):
    # What: compute name from the named fixture input; why: name str later reads name, so  app must retain the computed value under that name.
    name: str | None = None


# What: define RouterLoadBody as the owner of its declared state; why: daemon callers use this class boundary so those methods share one router load body state invariant.
class RouterLoadBody(BaseModel):
    # What: compute name from the named fixture input; why: html lang en head meta charset later reads name, so app must retain the computed value under that name.
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
# What: embed the exact router ui doctype html router-interface fragment; why: the router UI consumer receives this fragment verbatim through router ui, preserving browser markup, style, or script behavior.
# What: embed the exact html lang en head meta charset router-interface fragment; why: the router UI consumer receives this fragment verbatim through router ui, preserving browser markup, style, or script behavior.
# What: embed the exact title free token swap title style router-interface fragment; why: the router UI consumer receives this fragment verbatim through router ui, preserving browser markup, style, or script behavior.
# What: embed the exact body font px system ui sans serif max width router-interface fragment; why: the router UI consumer receives this fragment verbatim through router ui, preserving browser markup, style, or script behavior.
# What: embed the exact style head body h1 free token swap router-interface fragment; why: the router UI consumer receives this fragment verbatim through router ui, preserving browser markup, style, or script behavior.
# What: embed the exact div class row label bearer key router-interface fragment; why: the router UI consumer receives this fragment verbatim through router ui, preserving browser markup, style, or script behavior.
# What: embed the exact h2 status h2 pre id status router-interface fragment; why: the router UI consumer receives this fragment verbatim through router ui, preserving browser markup, style, or script behavior.
# What: embed the exact h2 activity h2 p rows are router-interface fragment; why: the router UI consumer receives this fragment verbatim through router ui, preserving browser markup, style, or script behavior.
# What: embed the exact script router-interface fragment; why: the router UI consumer receives this fragment verbatim through router ui, preserving browser markup, style, or script behavior.
# What: embed the exact const id document get element by id id headers authorization router-interface fragment; why: the router UI consumer receives this fragment verbatim through router ui, preserving browser markup, style, or script behavior.
# What: embed the exact async function api path opt let router-interface fragment; why: the router UI consumer receives this fragment verbatim through router ui, preserving browser markup, style, or script behavior.
# What: embed the exact function show id value id text content router-interface fragment; why: the router UI consumer receives this fragment verbatim through router ui, preserving browser markup, style, or script behavior.
# What: embed the exact async function refresh try let s router-interface fragment; why: the router UI consumer receives this fragment verbatim through router ui, preserving browser markup, style, or script behavior.
# What: embed the exact refresh onclick refresh reload onclick async router-interface fragment; why: the router UI consumer receives this fragment verbatim through router ui, preserving browser markup, style, or script behavior.
# What: embed the exact script body html router-interface fragment; why: the router UI consumer receives this fragment verbatim through router ui, preserving browser markup, style, or script behavior.
_ROUTER_UI = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FreeToken swap</title><style>
body{font:15px system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#18212b}button,input{font:inherit;padding:.4rem;margin:.2rem}pre{background:#f3f5f7;padding:1rem;overflow:auto}.row{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap}
</style></head><body><h1>FreeToken swap</h1><p>Enter a router bearer key to inspect or control this local daemon. The key is kept only in this page's memory.</p>
<div class="row"><label>Bearer key <input id="key" type="password" autocomplete="off"></label><button id="refresh">Refresh</button><button id="reload">Reload catalog</button><button id="unload">Unload resident</button></div>
<h2>Status</h2><pre id="status">Not loaded.</pre><h2>Models</h2><div id="models"></div><h2>Hardware</h2><pre id="hardware">Not loaded.</pre><h2>Performance history</h2><pre id="performance">Not loaded.</pre>
<h2>Activity</h2><p>Rows are body-free. Captures may contain prompts and are fetched only when selected.</p><div id="activity"></div><pre id="capture">No capture selected.</pre>
<script>
const $=id=>document.getElementById(id), headers=()=>({Authorization:'Bearer '+$('key').value});
async function api(path,opt={}){let r=await fetch(path,{...opt,headers:{...headers(),...(opt.headers||{})}});let d=await r.json();if(!r.ok)throw new Error(d.detail||d.error?.message||r.status);return d}
function show(id,value){$(id).textContent=JSON.stringify(value,null,2)}
async function refresh(){try{let [s,m,h,a,p]=await Promise.all([api('/router/status'),api('/router/models'),api('/router/hardware'),api('/router/activity?limit=25'),api('/router/performance').catch(e=>({enabled:false,error:e.message}))]);show('status',s);show('hardware',h);show('performance',p);let box=$('models');box.replaceChildren();for(const p of m.data){let b=document.createElement('button');b.textContent='Load '+p.name;b.onclick=async()=>{await api('/router/load',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:p.name})});refresh()};box.append(b)}let activity=$('activity');activity.replaceChildren();for(const row of a.data){let line=document.createElement('div');line.textContent='#'+row.id+' '+row.method+' '+row.route+' '+row.model+' status='+row.status+' bytes='+row.responseBytes+(row.sessionId?' session='+row.sessionId:'')+' ';if(row.hasCapture){let b=document.createElement('button');b.textContent='View capture';b.onclick=async()=>show('capture',await api('/router/captures/'+row.id));line.append(b)}activity.append(line)}}catch(e){show('status',{error:e.message})}}
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
    # What: declare the catalog input for build_app; why: build_app consumes catalog during catalog catalog or model catalog empty, so callers must bind it with the other signature inputs.
    catalog: ModelCatalog | None = None,
    # What: declare the router input for build_app; why: build_app consumes router during router router or routing coordinator, so callers must bind it with the other signature inputs.
    router: RoutingCoordinator | None = None,
    # What: declare the catalog path input for build_app; why: build_app consumes catalog path during if not catalog path, so callers must bind it with the other signature inputs.
    catalog_path: str | None = None,
    # What: declare the router ring input for build_app; why: build_app consumes router ring during router ring router ring or log ring capacity, so callers must bind it with the other signature inputs.
    router_ring: LogRing | None = None,
    # What: declare the catalog watch interval s input for build_app; why: build_app consumes catalog watch interval s during interval s catalog watch interval s if catalog watch interval s else, so callers must bind it with the other signature inputs.
    catalog_watch_interval_s: float = 0.0,
    # What: declare the activity path input for build_app; why: build_app consumes activity path during activity path, so callers must bind it with the other signature inputs.
    activity_path: str | None = None,
) -> FastAPI:
    import time as _time

    wall_now = wall_now or _time.time
    app = FastAPI(title="FreeToken daemon", version=DAEMON_VERSION)

    # What: register cors_preflight as HTTP middleware; why: every matching request passes through cors_preflight before the route handler so authentication or accounting wraps the request.
    @app.middleware("http")
    # What: define cors_preflight around request and call next; why: the registered API client call cors_preflight for cors preflight and rely on this exact input and result contract.
    async def cors_preflight(request: Request, call_next):
        # Match the pinned compatibility server's side-effect-free global
        # preflight contract. Actual requests still pass through normal route
        # authentication and lifecycle ownership.
        # What: gate on method and request before call next and request; why: cors_preflight admits call next and request only for this predicate and excludes the opposite state.
        if request.method != "OPTIONS":
            # What: return call next and request from cors_preflight; why: cors_preflight exposes call next and request so its caller can continue with the function\'s computed outcome.
            return await call_next(request)
        # What: return response and cors request headers and get and headers from cors_preflight; why: cors_preflight exposes response and cors request headers and get and headers so its caller can continue with the function\'s computed outcome.
        return Response(
            # What: supply status code to Response; why: cors_preflight binds this 204 value to Response's status code input.
            status_code=204,
            # What: supply headers to Response; why: cors_preflight binds this cors request headers and get and headers and request and access control allow origin value to Response's headers input.
            headers={
                # What: map the access control allow origin field as value; why: cors_preflight carries access control allow origin into "Access-Control-Allow-Origin": "*".
                "Access-Control-Allow-Origin": "*",
                # What: map the access control allow methods field as get and post and put and patch; why: cors_preflight carries access control allow methods into "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS".
                "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                # What: map the access control allow headers field as cors request headers and get and headers and request and access control request headers; why: cors_preflight carries access control allow headers into "Access-Control-Allow-Headers": _cors_request_headers(.
                "Access-Control-Allow-Headers": _cors_request_headers(
                    # What: call request.headers.get with access control request headers; why: cors_preflight consumes the request.headers.get return value while evaluating request.headers.get("access-control-request-headers").
                    request.headers.get("access-control-request-headers")
                # What: complete the _cors_request_headers call with get; why: cors_preflight groups the supplied clauses as one _cors_request_headers call before its value is consumed.
                ),
                # What: map the access control max age field as 86400; why: cors_preflight carries access control max age into "Access-Control-Max-Age": "86400".
                "Access-Control-Max-Age": "86400",
            # What: complete the enclosing predicate mapping with access control allow origin and access control allow methods and access control allow headers and access control max age; why: cors_preflight groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
            },
        # What: complete the Response call with status code and headers; why: cors_preflight groups the supplied clauses as one Response call before its value is consumed.
        )
    # What: compute catalog from catalog and empty and model catalog; why: manager catalog probe default port default serve port later reads catalog, so build_app must retain the computed value under that name.
    catalog = catalog or ModelCatalog.empty()
    # What: compute router from router and routing coordinator and manager and catalog; why: app router add event handler startup start performance monitor later reads router, so build_app must retain the computed value under that name.
    router = router or RoutingCoordinator(
        # What: supply default port to RoutingCoordinator; why: build_app binds this default serve port value to RoutingCoordinator's default port input.
        manager, catalog, probe, default_port=default_serve_port
    # What: complete the RoutingCoordinator call with default port; why: build_app groups the supplied clauses as one RoutingCoordinator call before its value is consumed.
    )
    # Keep router events separate from captured engine stdout. Apart from
    # making an operator's engine-log view useful, this prevents a noisy child
    # from evicting the bounded lifecycle/proxy audit trail. The event payload
    # deliberately contains no headers, query strings, request body, or model
    # path: those may carry credentials or prompts.
    # What: compute router ring from router ring and log ring and 1000; why: app state router ring router ring later reads router ring, so build_app must retain the computed value under that name.
    router_ring = router_ring or LogRing(capacity=1000)
    # What: compute router ring from router ring; why: router ring append later reads router ring, so build_app must retain the computed value under that name.
    app.state.router_ring = router_ring
    # What: compute activity store from activity store and activity max entries and activity path and activity session headers; why: app state activity store activity store later reads activity store, so build_app must retain the computed value under that name.
    activity_store = ActivityStore(
        # What: apply the catalog settings activity max entries portion of activity store; why: build_app uses this clause to evaluate activity store as one grouped value.
        catalog.settings.activity_max_entries,
        # What: apply the catalog settings capture buffer mb portion of activity store; why: build_app uses this clause to evaluate activity store as one grouped value.
        catalog.settings.capture_buffer_mb * 1024 * 1024,
        # What: apply the activity path portion of activity store; why: build_app uses this clause to evaluate activity store as one grouped value.
        activity_path,
        # What: apply the catalog settings activity session headers portion of activity store; why: build_app uses this clause to evaluate activity store as one grouped value.
        catalog.settings.activity_session_headers,
    # What: complete the ActivityStore call with activity max entries and capture buffer mb and activity path and activity session headers; why: build_app groups the supplied clauses as one ActivityStore call before its value is consumed.
    )
    # What: compute activity store from activity store; why: activity store reconfigure later reads activity store, so build_app must retain the computed value under that name.
    app.state.activity_store = activity_store
    # What: compute performance monitor from performance monitor and performance every s and performance disabled and wall now; why: app state performance monitor performance monitor later reads performance monitor, so build_app must retain the computed value under that name.
    performance_monitor = PerformanceMonitor(
        # What: call footprint_fn with get and status and manager and pid; why: build_app invokes footprint_fn while performing every s catalog settings performance every s; the call advances that operation through its result or side effect.
        lambda: footprint_fn(manager.status().get("pid")),
        # What: supply every s to PerformanceMonitor; why: build_app binds this performance every s and settings and catalog value to PerformanceMonitor's every s input.
        every_s=catalog.settings.performance_every_s,
        # What: supply disabled to PerformanceMonitor; why: build_app binds this performance disabled and settings and catalog value to PerformanceMonitor's disabled input.
        disabled=catalog.settings.performance_disabled,
        # What: supply wall now to PerformanceMonitor; why: build_app binds this wall now value to PerformanceMonitor's wall now input.
        wall_now=wall_now,
    # What: complete the PerformanceMonitor call with every s and disabled and wall now; why: build_app groups the supplied clauses as one PerformanceMonitor call before its value is consumed.
    )
    # What: compute performance monitor from performance monitor; why: performance monitor start later reads performance monitor, so build_app must retain the computed value under that name.
    app.state.performance_monitor = performance_monitor

    # What: define _start_performance_monitor around the current object state; why: its direct callers call _start_performance_monitor for start performance monitor and rely on this exact input and result contract.
    async def _start_performance_monitor() -> None:
        # What: call performance_monitor.start with the declared inputs; why: _start_performance_monitor invokes performance_monitor.start while performing the enclosing return; the call advances that operation through its result or side effect.
        performance_monitor.start()

    # What: define _stop_performance_monitor around the current object state; why: its direct callers call _stop_performance_monitor for stop performance monitor and rely on this exact input and result contract.
    async def _stop_performance_monitor() -> None:
        # What: call performance_monitor.stop with the declared inputs; why: _stop_performance_monitor invokes performance_monitor.stop while performing the enclosing return; the call advances that operation through its result or side effect.
        performance_monitor.stop()

    # What: preserve the exact app router add event handler startup start performance monitor literal fragment; why: build_app passes this fragment verbatim through app.router.add_event_handler("startup", _start_performance_monitor), because changing it would alter a protocol payload, serialized fixture, or public mes.
    app.router.add_event_handler("startup", _start_performance_monitor)
    # What: preserve the exact app router add event handler shutdown stop performance monitor literal fragment; why: build_app passes this fragment verbatim through app.router.add_event_handler("shutdown", _stop_performance_monitor), because changing it would alter a protocol payload, serialized fixture, or public mes.
    app.router.add_event_handler("shutdown", _stop_performance_monitor)
    # What: compute inflight lock from lock and threading; why: with inflight lock later reads inflight lock, so build_app must retain the computed value under that name.
    inflight_lock = threading.Lock()
    # What: initialize inflight as an empty runtime accumulator; why: build_app appends or maps entries into it during inflight request id before consuming the aggregate.
    inflight: dict[str, dict] = {}
    # What: initialize request reservations as an empty runtime accumulator; why: build_app appends or maps entries into it during if request id in request reservations before consuming the aggregate.
    request_reservations: dict[str, dict] = {}
    # What: compute watch stop from event and threading; why: app state catalog watch stop watch stop later reads watch stop, so build_app must retain the computed value under that name.
    watch_stop = threading.Event()
    # What: compute watch lock from lock and threading; why: with watch lock later reads watch lock, so build_app must retain the computed value under that name.
    watch_lock = threading.Lock()
    # What: compute watch state from bool and catalog watch interval s and catalog path and enabled and interval s; why: watch state last result result later reads watch state, so build_app must retain the computed value under that name.
    watch_state = {
        # What: map the enabled field as bool and catalog path and catalog watch interval s and 0; why: build_app carries enabled through watch state into watch state last result result.
        "enabled": bool(catalog_path and catalog_watch_interval_s > 0),
        # What: map the interval s field as catalog watch interval s and 0; why: build_app carries interval s through watch state into watch state last result result.
        "intervalS": catalog_watch_interval_s if catalog_watch_interval_s > 0 else None,
        # What: map the last result field as the fixture input; why: build_app carries last result through watch state into watch state last result result.
        "lastResult": None,
    # What: complete the watch_state mapping with enabled and interval s and last result; why: build_app groups the supplied clauses as one watch_state mapping before its value is consumed.
    }
    # What: compute catalog watch stop from watch stop; why: the enclosing return or state update later reads catalog watch stop, so build_app must retain the computed value under that name.
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

    # What: define require_token around x ft token and authorization and x api key; why: its direct callers call require_token for require token and rely on this exact input and result contract.
    def require_token(
        # What: declare the x ft token input for require_token; why: require_token consumes x ft token during if x ft token token, so callers must bind it with the other signature inputs.
        x_ft_token: str | None = Header(default=None),
        # What: declare the authorization input for require_token; why: require_token consumes authorization during supplied extract api key authorization x api key, so callers must bind it with the other signature inputs.
        authorization: str | None = Header(default=None),
        # What: declare the x api key input for require_token; why: require_token consumes x api key during supplied extract api key authorization x api key, so callers must bind it with the other signature inputs.
        x_api_key: str | None = Header(default=None),
    # What: complete the enclosing predicate with group delimiter; why: require_token groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ) -> None:
        # What: gate on token before x ft token and token and httpexception; why: require_token admits x ft token and token and httpexception only for this predicate and excludes the opposite state.
        if token is not None:
            # What: gate on x ft token and token before httpexception; why: require_token admits httpexception only for this predicate and excludes the opposite state.
            if x_ft_token != token:
                # What: raise HTTPException for the caller; why:  require_token stops this rejected path before it can mutate state, dispatch work, or report success.
                raise HTTPException(status_code=401, detail="invalid or missing X-FT-Token")
            # What: return no value from require_token; why: require_token returns no value to callers that depend on its completed result.
            return
        # What: compute keys from api keys and settings and catalog and router; why: if keys later reads keys, so require_token must retain the computed value under that name.
        keys = router.catalog.settings.api_keys
        # What: gate on keys before supplied and extract api key and authorization and x api key; why: require_token admits supplied and extract api key and authorization and x api key only for this predicate and excludes the opposite state.
        if keys:
            # What: compute supplied from extract api key and authorization and x api key; why: if supplied not in keys later reads supplied, so require_token must retain the computed value under that name.
            supplied = _extract_api_key(authorization, x_api_key)
            # What: gate on supplied and keys before httpexception; why: require_token admits httpexception only for this predicate and excludes the opposite state.
            if supplied not in keys:
                # What: raise HTTPException for the caller; why:  require_token stops this rejected path before it can mutate state, dispatch work, or report success.
                raise HTTPException(
                    # What: supply status code to HTTPException; why: require_token binds this 401 value to HTTPException's status code input.
                    status_code=401,
                    # What: supply detail to HTTPException; why: require_token binds this invalid and or and missing and api value to HTTPException's detail input.
                    detail="invalid or missing API key",
                    # What: map the www authenticate field as basic and realm and freetoken swap; why: require_token carries www authenticate into headers={"WWW-Authenticate": 'Basic realm="freetoken-swap"'}.
                    headers={"WWW-Authenticate": 'Basic realm="freetoken-swap"'},
                # What: complete the HTTPException call with status code and detail and headers; why: require_token groups the supplied clauses as one HTTPException call before its value is consumed.
                )

    auth = [Depends(require_token)]

    # What: define require_router_key around authorization and x api key; why: its direct callers call require_router_key for require router key and rely on this exact input and result contract.
    def require_router_key(
        # What: declare the authorization input for require_router_key; why: require_router_key consumes authorization during supplied extract api key authorization x api key, so callers must bind it with the other signature inputs.
        authorization: str | None = Header(default=None),
        # What: declare the x api key input for require_router_key; why: require_router_key consumes x api key during supplied extract api key authorization x api key, so callers must bind it with the other signature inputs.
        x_api_key: str | None = Header(default=None),
    # What: complete the enclosing predicate with group delimiter; why: require_router_key groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ) -> None:
        # What: compute keys from api keys and settings and catalog and router; why: if not keys later reads keys, so require_router_key must retain the computed value under that name.
        keys = router.catalog.settings.api_keys
        # What: gate on keys before the computed value; why: require_router_key admits the computed value only for this predicate and excludes the opposite state.
        if not keys:
            # What: return no value from require_router_key; why: require_router_key returns no value to callers that depend on its completed result.
            return
        # What: compute supplied from extract api key and authorization and x api key; why: if supplied not in keys later reads supplied, so require_router_key must retain the computed value under that name.
        supplied = _extract_api_key(authorization, x_api_key)
        # What: gate on supplied and keys before httpexception; why: require_router_key admits httpexception only for this predicate and excludes the opposite state.
        if supplied not in keys:
            # What: raise HTTPException for the caller; why: require_router_key stops this rejected path before it can mutate state, dispatch work, or report success.
            raise HTTPException(
                # What: supply status code to HTTPException; why: require_router_key binds this 401 value to HTTPException's status code input.
                status_code=401,
                # What: supply detail to HTTPException; why: require_router_key binds this invalid and or and missing and api value to HTTPException's detail input.
                detail="invalid or missing API key",
                # What: map the www authenticate field as basic and realm and freetoken swap; why: require_router_key carries www authenticate into headers={"WWW-Authenticate": 'Basic realm="freetoken-swap"'}.
                headers={"WWW-Authenticate": 'Basic realm="freetoken-swap"'},
            # What: complete the HTTPException call with status code and detail and headers; why: require_router_key groups the supplied clauses as one HTTPException call before its value is consumed.
            )

    # What: define run around pool and fn; why: its direct callers call run for run and rely on this exact input and result contract.
    async def run(pool: ThreadPoolExecutor, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        # What: return run in executor and pool and loop and partial from run; why: run exposes run in executor and pool and loop and partial so its caller can continue with the function\'s computed outcome.
        return await loop.run_in_executor(pool, functools.partial(fn, *args, **kwargs))

    # What: define run_to_completion around operation; why: its direct callers call run_to_completion for run to completion and rely on this exact input and result contract.
    async def run_to_completion(operation):
        """Defer caller cancellation until an ownership transaction is terminal."""
        # What: document defer caller cancellation until an ownership in the run_to_completion docstring; why: introspection and maintainers read this exact docstring fragment to understand run to completion behavior without executing it.
        # What: compute task from create task and asyncio and operation; why: return await asyncio shield task later reads task, so run_to_completion must retain the computed value under that name.
        task = asyncio.create_task(operation())
        # What: establish the handler boundary for the protected operation; why: run_to_completion routes failures to cancelled error and asyncio while preserving cleanup and success flow.
        try:
            # What: return shield and task and asyncio from run_to_completion; why: run_to_completion exposes shield and task and asyncio so its caller can continue with the function\'s computed outcome.
            return await asyncio.shield(task)
        # What: handle cancelled error and asyncio by while true; why: run_to_completion converts that failure into this concrete recovery, response, or cleanup behavior.
        except asyncio.CancelledError:
            # What: iterate across the computed value to perform cancelled error and base exception and asyncio and shield and task; why: run_to_completion repeats the body only while or for the loop header admits an iteration.
            while True:
                # What: establish the handler boundary for the protected operation; why: run_to_completion routes failures to cancelled error and asyncio and base exception while preserving cleanup and success flow.
                try:
                    # What: call asyncio.shield with task; why: run_to_completion invokes asyncio.shield while performing except asyncio cancelled error; the call advances that operation through its result or side effect.
                    await asyncio.shield(task)
                # What: handle cancelled error and asyncio by continue; why: run_to_completion converts that failure into this concrete recovery, response, or cleanup behavior.
                except asyncio.CancelledError:
                    # What: apply the continue portion of the enclosing predicate; why: this clause remains in run_to_completion\'s enclosing expression so its grouping and evaluation order stay intact.
                    continue
                # What: handle base exception by break; why: run_to_completion converts that failure into this concrete recovery, response, or cleanup behavior.
                except BaseException:
                    # What: apply the break portion of the enclosing predicate; why: this clause remains in run_to_completion\'s enclosing expression so its grouping and evaluation order stay intact.
                    break
                # What: select the remaining branch that performs break; why: run_to_completion covers the state excluded by the preceding predicate without conflating the two outcomes.
                else:
                    # What: apply the break portion of the enclosing predicate; why: this clause remains in run_to_completion\'s enclosing expression so its grouping and evaluation order stay intact.
                    break
            # What: re-propagate the active failure to the caller; why: run_to_completion stops this rejected path before it can mutate state, dispatch work, or report success.
            raise

    # What: define run_manual_transaction around operation and preempt manual; why: its direct callers call run_manual_transaction for run manual transaction and rely on this exact input and result contract.
    async def run_manual_transaction(operation, *, preempt_manual: bool = False):
        """Keep manual ownership until the complete transaction reaches a terminal state."""
        # What: document keep manual ownership until the complete in the run_manual_transaction docstring; why: introspection and maintainers read this exact docstring fragment to understand run manual transaction behavior without executing it.
        # What: compute owner from begin manual lifecycle and preempt manual; why: router end manual lifecycle owner later reads owner, so run_manual_transaction must retain the computed value under that name.
        owner = begin_manual_lifecycle(preempt_manual=preempt_manual)
        # What: establish the handler boundary for the protected operation; why: run_manual_transaction routes failures to the unconditional cleanup block while preserving cleanup and success flow.
        try:
            # What: return run to completion and operation from run_manual_transaction; why: run_manual_transaction exposes run to completion and operation so its caller can continue with the function\'s computed outcome.
            return await run_to_completion(operation)
        # What: run router end manual lifecycle owner on every exit path; why: run_manual_transaction performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
        finally:
            # What: call router.end_manual_lifecycle with owner; why: run_manual_transaction invokes router.end_manual_lifecycle while performing the enclosing return; the call advances that operation through its result or side effect.
            router.end_manual_lifecycle(owner)

    # What: define acquire_route around name and cancellation and on reserved and apply loading policy and apply routing profile; why: its direct callers call acquire_route for acquire route and rely on this exact input and result contract.
    async def acquire_route(
        # What: declare the name input for acquire_route; why: acquire_route consumes name during name, so callers must bind it with the other signature inputs.
        name: str,
        # What: declare the cancellation input for acquire_route; why: acquire_route consumes cancellation during cancellation cancellation or threading event, so callers must bind it with the other signature inputs.
        cancellation: threading.Event | None = None,
        # What: declare the on reserved input for acquire_route; why: acquire_route consumes on reserved during on reserved, so callers must bind it with the other signature inputs.
        on_reserved: Callable[[bool, int], None] | None = None,
        # What: mark the remaining parameters as keyword-only; why: acquire_route prevents callers from confusing adjacent lifecycle and timing arguments.
        *,
        # What: declare the apply loading policy input for acquire_route; why: acquire_route consumes apply loading policy during apply loading policy apply loading policy, so callers must bind it with the other signature inputs.
        apply_loading_policy: bool = False,
        # What: declare the apply routing profile input for acquire_route; why: acquire_route consumes apply routing profile during apply routing profile apply routing profile, so callers must bind it with the other signature inputs.
        apply_routing_profile: bool = True,
    # What: complete the enclosing predicate with async def acquire route name str cancellation threading event on reserved callable; why: acquire_route groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        """Keep executor-side admission owned if its HTTP task is cancelled."""
        # What: document keep executor side admission owned if its in the acquire_route docstring; why: introspection and maintainers read this exact docstring fragment to understand acquire route behavior without executing it.
        # What: compute loop from get running loop and asyncio; why: future loop run in executor later reads loop, so acquire_route must retain the computed value under that name.
        loop = asyncio.get_running_loop()
        # What: compute cancellation from cancellation and event and threading; why: cancellation later reads cancellation, so acquire_route must retain the computed value under that name.
        cancellation = cancellation or threading.Event()
        # What: compute future from run in executor and lifecycle pool and loop and partial; why: shielded asyncio shield future later reads future, so acquire_route must retain the computed value under that name.
        future = loop.run_in_executor(
            # What: apply the lifecycle pool portion of future; why: acquire_route uses this clause to evaluate future as one grouped value.
            lifecycle_pool,
            # What: call functools.partial with acquire and router and name and cancellation; why: acquire_route invokes functools.partial while performing router acquire; the call advances that operation through its result or side effect.
            functools.partial(
                # What: apply the router acquire portion of future; why: acquire_route uses this clause to evaluate future as one grouped value.
                router.acquire,
                # What: apply the name portion of future; why: acquire_route uses this clause to evaluate future as one grouped value.
                name,
                # What: apply the cancellation portion of future; why: acquire_route uses this clause to evaluate future as one grouped value.
                cancellation,
                # What: apply the on reserved portion of future; why: acquire_route uses this clause to evaluate future as one grouped value.
                on_reserved,
                # What: supply apply loading policy to functools.partial; why: acquire_route binds this apply loading policy value to functools.partial's apply loading policy input.
                apply_loading_policy=apply_loading_policy,
                # What: supply apply routing profile to functools.partial; why: acquire_route binds this apply routing profile value to functools.partial's apply routing profile input.
                apply_routing_profile=apply_routing_profile,
            # What: complete the functools.partial call with apply loading policy and apply routing profile; why: acquire_route groups the supplied clauses as one functools.partial call before its value is consumed.
            ),
        # What: complete the loop.run_in_executor call with lifecycle pool and partial; why: acquire_route groups the supplied clauses as one loop.run_in_executor call before its value is consumed.
        )
        # What: compute shielded from shield and future and asyncio; why: return await shielded later reads shielded, so acquire_route must retain the computed value under that name.
        shielded = asyncio.shield(future)
        # What: establish the handler boundary for the protected operation; why: acquire_route routes failures to cancelled error and asyncio while preserving cleanup and success flow.
        try:
            # What: return shielded from acquire_route; why: acquire_route exposes shielded so its caller can continue with the function\'s computed outcome.
            return await shielded
        # What: handle cancelled error and asyncio by router cancel acquire cancellation; why: acquire_route converts that failure into this concrete recovery, response, or cleanup behavior.
        except asyncio.CancelledError:
            # What: call router.cancel_acquire with cancellation; why: acquire_route invokes router.cancel_acquire while performing try; the call advances that operation through its result or side effect.
            router.cancel_acquire(cancellation)
            # Retain ownership until the executor-side admission is terminal.
            # This retrieves its expected RoutingError before the event loop
            # can close and releases a lease if admission won the race.
            # What: establish the handler boundary for the protected operation; why: acquire_route routes failures to base exception while preserving cleanup and success flow.
            try:
                # What: compute orphaned from shield and future and asyncio; why: orphaned release later reads orphaned, so acquire_route must retain the computed value under that name.
                orphaned = await asyncio.shield(future)
            # What: handle base exception by pass; why: acquire_route converts that failure into this concrete recovery, response, or cleanup behavior.
            except BaseException:
                # What: ignore the anticipated exception handled by this branch; why: acquire_route continues its retry or cleanup path instead of re-raising that transient failure.
                pass
            # What: select the remaining branch that performs orphaned release; why: acquire_route covers the state excluded by the preceding predicate without conflating the two outcomes.
            else:
                # What: call orphaned.release with the declared inputs; why: acquire_route invokes orphaned.release while performing raise; the call advances that operation through its result or side effect.
                orphaned.release()
            # What: re-propagate the active failure to the caller; why: acquire_route stops this rejected path before it can mutate state, dispatch work, or report success.
            raise

    # What: define connect_upstream around the current object state; why: its direct callers call connect_upstream for connect upstream and rely on this exact input and result contract.
    async def connect_upstream(**kwargs):
        """Close a connector result that arrives after its HTTP task disconnects."""
        # What: document close a connector result that arrives in the connect_upstream docstring; why: introspection and maintainers read this exact docstring fragment to understand connect upstream behavior without executing it.
        # What: compute loop from get running loop and asyncio; why: future loop run in executor proxy pool functools partial open upstream kwargs later reads loop, so connect_upstream must retain the computed value under that name.
        loop = asyncio.get_running_loop()
        # What: compute future from run in executor and proxy pool and loop and partial; why: return await asyncio shield future later reads future, so connect_upstream must retain the computed value under that name.
        future = loop.run_in_executor(proxy_pool, functools.partial(open_upstream, **kwargs))
        # What: establish the handler boundary for the protected operation; why: connect_upstream routes failures to cancelled error and asyncio while preserving cleanup and success flow.
        try:
            # What: return shield and future and asyncio from connect_upstream; why: connect_upstream exposes shield and future and asyncio so its caller can continue with the function\'s computed outcome.
            return await asyncio.shield(future)
        # What: handle cancelled error and asyncio by def close orphaned upstream done; why: connect_upstream converts that failure into this concrete recovery, response, or cleanup behavior.
        except asyncio.CancelledError:
            # What: define close_orphaned_upstream around done; why: its direct callers call close_orphaned_upstream for close orphaned upstream and rely on this exact input and result contract.
            def close_orphaned_upstream(done) -> None:
                # What: establish the handler boundary for the protected operation; why: close_orphaned_upstream routes failures to base exception while preserving cleanup and success flow.
                try:
                    # What: compute orphaned from result and done; why: orphaned close later reads orphaned, so close_orphaned_upstream must retain the computed value under that name.
                    orphaned = done.result()
                # What: handle base exception by return; why: close_orphaned_upstream converts that failure into this concrete recovery, response, or cleanup behavior.
                except BaseException:
                    # What: return no value from close_orphaned_upstream; why: close_orphaned_upstream returns no value to callers that depend on its completed result.
                    return
                # What: call orphaned.close with the declared inputs; why: close_orphaned_upstream invokes orphaned.close while performing the enclosing return; the call advances that operation through its result or side effect.
                orphaned.close()

            # What: call future.add_done_callback with close orphaned upstream; why: connect_upstream invokes future.add_done_callback while performing raise; the call advances that operation through its result or side effect.
            future.add_done_callback(close_orphaned_upstream)
            # What: re-propagate the active failure to the caller; why: connect_upstream stops this rejected path before it can mutate state, dispatch work, or report success.
            raise

    def resolve_port(explicit: int | None) -> int:
        # What: gate on explicit before allocate loopback port; why: resolve_port admits allocate loopback port only for this predicate and excludes the opposite state.
        if explicit == 0:
            # What: return allocate loopback port from resolve_port; why: resolve_port exposes allocate loopback port so its caller can continue with the function\'s computed outcome.
            return allocate_loopback_port()
        if explicit is not None:
            return explicit
        st = manager.status()
        return st.get("port") or default_serve_port

    # What: define begin_manual_lifecycle around preempt manual; why: its direct callers call begin_manual_lifecycle for begin manual lifecycle and rely on this exact input and result contract.
    def begin_manual_lifecycle(*, preempt_manual: bool = False) -> object:
        """Atomically keep legacy engine controls outside routed ownership."""
        # What: document atomically keep legacy engine controls outside in the begin_manual_lifecycle docstring; why: introspection and maintainers read this exact docstring fragment to understand begin manual lifecycle behavior without executing it.
        # What: establish the handler boundary for the protected operation; why: begin_manual_lifecycle routes failures to routing error while preserving cleanup and success flow.
        try:
            # What: return begin manual lifecycle and router and preempt manual from begin_manual_lifecycle; why: begin_manual_lifecycle exposes begin manual lifecycle and router and preempt manual so its caller can continue with the function\'s computed outcome.
            return router.begin_manual_lifecycle(preempt_manual=preempt_manual)
        # What: handle routing error by raise httpexception status code exc status code detail str exc; why: begin_manual_lifecycle converts that failure into this concrete recovery, response, or cleanup behavior.
        except RoutingError as exc:
            # What: raise HTTPException for the caller; why: begin_manual_lifecycle stops this rejected path before it can mutate state, dispatch work, or report success.
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

    # What: register GET /ready on the application router; why: clients reach ready's handler only through this method-and-path binding.
    @app.get("/ready")
    # What: define the /ready control-plane handler; why: supervisors call this handler to learn whether the daemon control plane can accept requests, independent of engine stop receipts or token accounting.
    async def ready():
        """Stable router readiness; it never starts a model as a probe side effect."""
        # What: document stable router readiness it never starts in the ready docstring; why: introspection and maintainers read this exact docstring fragment to understand ready behavior without executing it.
        # What: compute accepting from run and proxy pool and is ready and probe; why: return jsonresponse status code if accepting else later reads accepting, so ready must retain the computed value under that name.
        accepting = await run(proxy_pool, router.is_ready, probe)
        # What: return HTTP 200 when accepting and 503 otherwise; why: supervisors use this status and ready boolean to decide whether the daemon control plane may receive traffic.
        return JSONResponse(status_code=200 if accepting else 503, content={"ready": accepting})

    # What: register GET /ui/ on the application router; why: clients reach router_ui's handler only through this method-and-path binding.
    @app.get("/ui/")
    # What: define router_ui around the current object state; why: the registered API client call router_ui for router ui and rely on this exact input and result contract.
    async def router_ui():
        """A static shell; authenticated APIs supply all operational data."""
        # What: document a static shell authenticated apis supply in the router_ui docstring; why: introspection and maintainers read this exact docstring fragment to understand router ui behavior without executing it.
        # What: return htmlresponse and router ui from router_ui; why: router_ui exposes htmlresponse and router ui so its caller can continue with the function\'s computed outcome.
        return HTMLResponse(_ROUTER_UI)

    # What: define router_event around event; why: its direct callers call router_event for router event and rely on this exact input and result contract.
    def router_event(event: str, **fields: Any) -> None:
        # What: call router_ring.append with dumps and json and event and fields and event; why: router_event invokes router_ring.append while performing json dumps event event fields separators sort keys; the call advances that operation through its result or side effect.
        router_ring.append(
            # What: map the event field as event; why: router_event carries event into json.dumps({"event": event, **fields}, separators=(",", ":"), sort_keys=.
            json.dumps({"event": event, **fields}, separators=(",", ":"), sort_keys=True),
            # What: preserve the exact kind event literal fragment; why: router_event passes this fragment verbatim through kind="event", because changing it would alter a protocol payload, serialized fixture, or public message.
            kind="event",
            # What: supply ts to wall_now; why: router_event binds this wall now value to wall_now's ts input.
            ts=wall_now(),
        # What: complete the router_ring.append call with kind and ts; why: router_event groups the supplied clauses as one router_ring.append call before its value is consumed.
        )

    # What: execute if catalog settings startup routing profile is not None; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
    if catalog.settings.startup_routing_profile is not None:
        # What: call router.set_active_routing_profile with startup routing profile and settings and catalog; why: build_app invokes router.set_active_routing_profile while performing if catalog settings preload model is not; the call advances that operation through its result or side effect.
        router.set_active_routing_profile(catalog.settings.startup_routing_profile)

    # What: gate on preload model and settings and catalog before name and preload model and on event and settings and lease; why: build_app admits name and preload model and on event and settings and lease only for this predicate and excludes the opposite state.
    if catalog.settings.preload_model is not None:

        # What: apply app.on_event behavior to _preload_model; why: Python attaches this named decorator's registration or descriptor semantics to _preload_model.
        @app.on_event("startup")
        # What: define _preload_model around the current object state; why: the registered API client call _preload_model for preload model and rely on this exact input and result contract.
        async def _preload_model() -> None:
            # What: compute name from preload model and settings and catalog; why: lease await acquire route name apply routing profile later reads name, so _preload_model must retain the computed value under that name.
            name = catalog.settings.preload_model
            # What: establish the handler boundary for the protected operation; why: _preload_model routes failures to base exception while preserving cleanup and success flow.
            try:
                # What: compute lease from acquire route and name and false; why: lease release later reads lease, so _preload_model must retain the computed value under that name.
                lease = await acquire_route(name, apply_routing_profile=False)
            # What: handle base exception by router event startup preload failed profile name code type exc; why: _preload_model converts that failure into this concrete recovery, response, or cleanup behavior.
            except BaseException as exc:
                # What: preserve the exact router event startup preload failed profile name code type literal fragment; why: _preload_model passes this fragment verbatim through router_event("startup_preload_failed", profile=name, code=type(exc).__na, because changing it would alter a protocol payload, serialized fixt.
                router_event("startup_preload_failed", profile=name, code=type(exc).__name__)
                # What: return no value from _preload_model; why: _preload_model returns no value to callers that depend on its completed result.
                return
            # What: call lease.release with the declared inputs; why: _preload_model invokes lease.release while performing router event startup preloaded profile lease profile name; the call advances that operation through its result or side effect.
            lease.release()
            # What: preserve the exact router event startup preloaded profile lease profile name literal fragment; why: _preload_model passes this fragment verbatim through router_event("startup_preloaded", profile=lease.profile.name), because changing it would alter a protocol payload, serialized fixture, or public m.
            router_event("startup_preloaded", profile=lease.profile.name)

    # What: define record_watch around result; why: its direct callers call record_watch for record watch and rely on this exact input and result contract.
    def record_watch(result: str) -> None:
        # What: enter the watch lock managed context before watch state last result result; why: record_watch releases this resource or lock after watch state last result result on both success and failure paths.
        with watch_lock:
            # What: compute watch state entry from result; why: watch state last changed at wall now later reads watch state entry, so record_watch must retain the computed value under that name.
            watch_state["lastResult"] = result
            # What: compute watch state entry from wall now; why: the enclosing return or state update later reads watch state entry, so record_watch must retain the computed value under that name.
            watch_state["lastChangedAt"] = wall_now()

    # What: define catalog_watch_snapshot around the current object state; why: its direct callers call catalog_watch_snapshot for catalog watch snapshot and rely on this exact input and result contract.
    def catalog_watch_snapshot() -> dict:
        # What: enter the watch lock managed context before return dict watch state; why: catalog_watch_snapshot releases this resource or lock after return dict watch state on both success and failure paths.
        with watch_lock:
            # What: return dict and watch state from catalog_watch_snapshot; why: catalog_watch_snapshot exposes dict and watch state so its caller can continue with the function\'s computed outcome.
            return dict(watch_state)

    # What: define catalog_stamp around the current object state; why: its direct callers call catalog_stamp for catalog stamp and rely on this exact input and result contract.
    def catalog_stamp() -> tuple[int, int] | None:
        # What: gate on catalog path before the computed value; why: catalog_stamp admits the computed value only for this predicate and excludes the opposite state.
        if not catalog_path:
            # What: return no value from catalog_stamp; why: catalog_stamp returns no value to callers that depend on its completed result.
            return None
        # What: establish the handler boundary for the protected operation; why: catalog_stamp routes failures to oserror while preserving cleanup and success flow.
        try:
            # What: compute stat from stat and catalog path and os; why: return stat st mtime ns stat st size later reads stat, so catalog_stamp must retain the computed value under that name.
            stat = os.stat(catalog_path)
        # What: handle oserror by return; why: catalog_stamp converts that failure into this concrete recovery, response, or cleanup behavior.
        except OSError:
            # What: return no value from catalog_stamp; why: catalog_stamp returns no value to callers that depend on its completed result.
            return None
        # What: return st mtime ns and st size and stat from catalog_stamp; why: catalog_stamp exposes st mtime ns and st size and stat so its caller can continue with the function\'s computed outcome.
        return stat.st_mtime_ns, stat.st_size

    # What: define start_catalog_watcher around the current object state; why: its direct callers call start_catalog_watcher for start catalog watcher and rely on this exact input and result contract.
    def start_catalog_watcher() -> None:
        """Poll a local catalog safely; only a fully validated tree is installed.

        Polling keeps the daemon stdlib-only and cross-platform. A changed
        malformed file is remembered until it changes again, avoiding a log
        storm while an editor writes it. Active-profile redefinition is still
        refused by the coordinator, so a watcher cannot steal a live child.
        """
        # What: document poll a local catalog safely only in the start_catalog_watcher docstring; why: introspection and maintainers read this exact docstring fragment to understand start catalog watcher behavior without executing it.
        # What: document polling keeps the daemon stdlib only and in the start_catalog_watcher docstring; why: introspection and maintainers read this exact docstring fragment to understand start catalog watcher behavior without executing it.
        # What: document malformed file is remembered until it in the start_catalog_watcher docstring; why: introspection and maintainers read this exact docstring fragment to understand start catalog watcher behavior without executing it.
        # What: document storm while an editor writes it in the start_catalog_watcher docstring; why: introspection and maintainers read this exact docstring fragment to understand start catalog watcher behavior without executing it.
        # What: document refused by the coordinator so a in the start_catalog_watcher docstring; why: introspection and maintainers read this exact docstring fragment to understand start catalog watcher behavior without executing it.
        # What: preserve the paragraph boundary in the the start_catalog_watcher docstring; why: introspection and maintainers read this paragraph break to understand start catalog watcher behavior without executing it.
        # What: gate on watch state before the computed value; why: start_catalog_watcher admits the computed value only for this predicate and excludes the opposite state.
        if not watch_state["enabled"]:
            # What: return no value from start_catalog_watcher; why: start_catalog_watcher returns no value to callers that depend on its completed result.
            return
        # What: compute interval from float and catalog watch interval s; why: while not watch stop wait interval later reads interval, so start_catalog_watcher must retain the computed value under that name.
        interval = float(catalog_watch_interval_s)

        # What: define watch around the current object state; why: its direct callers call watch for watch and rely on this exact input and result contract.
        def watch() -> None:
            # What: compute previous from catalog stamp; why: if changed previous later reads previous, so watch must retain the computed value under that name.
            previous = catalog_stamp()
            # What: iterate across wait and interval and watch stop to perform changed and catalog stamp; why: watch repeats the body only while or for the loop header admits an iteration.
            while not watch_stop.wait(interval):
                # What: compute changed from catalog stamp; why: if changed previous later reads changed, so watch must retain the computed value under that name.
                changed = catalog_stamp()
                # What: gate on changed and previous before the computed value; why: watch admits the computed value only for this predicate and excludes the opposite state.
                if changed == previous:
                    # What: apply the continue portion of the enclosing predicate; why: this clause remains in watch\'s enclosing expression so its grouping and evaluation order stay intact.
                    continue
                # What: compute previous from changed; why: the enclosing return or state update later reads previous, so watch must retain the computed value under that name.
                previous = changed
                # What: establish the handler boundary for the protected operation; why: watch routes failures to catalog error and routing error while preserving cleanup and success flow.
                try:
                    # What: compute replacement from load and catalog path and model catalog; why: router replace catalog replacement later reads replacement, so watch must retain the computed value under that name.
                    replacement = ModelCatalog.load(catalog_path)
                    # What: call router.replace_catalog with replacement; why: watch invokes router.replace_catalog while performing activity store reconfigure; the call advances that operation through its result or side effect.
                    router.replace_catalog(replacement)
                    # What: execute activity store reconfigure; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
                    activity_store.reconfigure(
                        # What: apply the replacement settings activity max entries portion of the enclosing predicate; why: this clause remains in watch\'s enclosing expression so its grouping and evaluation order stay intact.
                        replacement.settings.activity_max_entries,
                        # What: apply the replacement settings capture buffer mb portion of the enclosing predicate; why: this clause remains in watch\'s enclosing expression so its grouping and evaluation order stay intact.
                        replacement.settings.capture_buffer_mb * 1024 * 1024,
                        # What: apply the replacement settings activity session headers portion of the enclosing predicate; why: this clause remains in watch\'s enclosing expression so its grouping and evaluation order stay intact.
                        replacement.settings.activity_session_headers,
                    # What: complete the activity_store.reconfigure call with activity max entries and capture buffer mb and activity session headers; why: watch groups the supplied clauses as one activity_store.reconfigure call before its value is consumed.
                    )
                    # What: call performance_monitor.reconfigure; why: app needs this line to preserve the surrounding expression or collection structure.
                    performance_monitor.reconfigure(
                        # What: apply the replacement settings performance every s portion of the enclosing predicate; why: this clause remains in watch\'s enclosing expression so its grouping and evaluation order stay intact.
                        replacement.settings.performance_every_s,
                        # What: apply the replacement settings performance disabled portion of the enclosing predicate; why: this clause remains in watch\'s enclosing expression so its grouping and evaluation order stay intact.
                        replacement.settings.performance_disabled,
                    # What: complete the performance_monitor.reconfigure call with performance every s and performance disabled; why: watch groups the supplied clauses as one performance_monitor.reconfigure call before its value is consumed.
                    )
                # What: handle catalog error by record watch invalid catalog; why: watch converts that failure into this concrete recovery, response, or cleanup behavior.
                except CatalogError:
                    # What: preserve the exact record watch invalid catalog literal fragment; why: watch passes this fragment verbatim through record_watch("invalid_catalog"), because changing it would alter a protocol payload, serialized fixture, or public message.
                    record_watch("invalid_catalog")
                    # What: preserve the exact router event catalog watch rejected code invalid catalog literal fragment; why: watch passes this fragment verbatim through router_event("catalog_watch_rejected", code="invalid_catalog"), because changing it would alter a protocol payload, serialized fixture, or public me.
                    router_event("catalog_watch_rejected", code="invalid_catalog")
                # What: handle routing error by record watch exc code; why: watch converts that failure into this concrete recovery, response, or cleanup behavior.
                except RoutingError as exc:
                    # What: call record_watch with code and exc; why: watch invokes record_watch while performing router event catalog watch rejected code exc code; the call advances that operation through its result or side effect.
                    record_watch(exc.code)
                    # What: preserve the exact router event catalog watch rejected code exc code literal fragment; why: watch passes this fragment verbatim through router_event("catalog_watch_rejected", code=exc.code), because changing it would alter a protocol payload, serialized fixture, or public message.
                    router_event("catalog_watch_rejected", code=exc.code)
                # What: select the remaining branch that performs record watch reloaded; why: watch covers the state excluded by the preceding predicate without conflating the two outcomes.
                else:
                    # What: preserve the exact record watch reloaded literal fragment; why: watch passes this fragment verbatim through record_watch("reloaded"), because changing it would alter a protocol payload, serialized fixture, or public message.
                    record_watch("reloaded")
                    # What: preserve the exact router event catalog watch reloaded literal fragment; why: watch passes this fragment verbatim through router_event("catalog_watch_reloaded"), because changing it would alter a protocol payload, serialized fixture, or public message.
                    router_event("catalog_watch_reloaded")

        # What: compute thread from thread and threading and watch and ft daemon catalog watch and true; why: app state catalog watch thread thread later reads thread, so start_catalog_watcher must retain the computed value under that name.
        thread = threading.Thread(target=watch, name="ft-daemon-catalog-watch", daemon=True)
        # What: compute catalog watch thread from thread; why: the enclosing return or state update later reads catalog watch thread, so start_catalog_watcher must retain the computed value under that name.
        app.state.catalog_watch_thread = thread
        # What: call thread.start with the declared inputs; why: start_catalog_watcher invokes thread.start while performing the enclosing return; the call advances that operation through its result or side effect.
        thread.start()

    # What: call start_catalog_watcher with the declared inputs; why: build_app invokes start_catalog_watcher while performing if watch state enabled; the call advances that operation through its result or side effect.
    start_catalog_watcher()

    # What: gate on watch state before on event and set and app and watch stop; why: build_app admits on event and set and app and watch stop only for this predicate and excludes the opposite state.
    if watch_state["enabled"]:

        # What: apply app.on_event behavior to _stop_catalog_watcher; why: Python attaches this named decorator's registration or descriptor semantics to _stop_catalog_watcher.
        @app.on_event("shutdown")
        # What: define _stop_catalog_watcher around the current object state; why: the registered API client call _stop_catalog_watcher for stop catalog watcher and rely on this exact input and result contract.
        async def _stop_catalog_watcher() -> None:
            # What: call watch_stop.set with the declared inputs; why: _stop_catalog_watcher invokes watch_stop.set while performing the enclosing return; the call advances that operation through its result or side effect.
            watch_stop.set()

    # What: define forward_routed around request and model and path and query and body and apply request filters; why: its direct callers call forward_routed for forward routed and rely on this exact input and result contract.
    async def forward_routed(
        # What: declare the request input for forward_routed; why: forward_routed consumes request during safe route getattr request scope get route path request method, so callers must bind it with the other signature inputs.
        request: Request,
        # What: declare the model input for forward_routed; why: forward_routed consumes model during profile model, so callers must bind it with the other signature inputs.
        model: str,
        # What: mark the remaining parameters as keyword-only; why: forward_routed prevents callers from confusing adjacent lifecycle and timing arguments.
        *,
        # What: declare the path and query input for forward_routed; why: forward_routed consumes path and query during path and query path and query, so callers must bind it with the other signature inputs.
        path_and_query: str,
        # What: declare the body input for forward_routed; why: forward_routed consumes body during outbound body body, so callers must bind it with the other signature inputs.
        body: bytes,
        # What: declare the apply request filters input for forward_routed; why: forward_routed consumes apply request filters during if not apply request filters, so callers must bind it with the other signature inputs.
        apply_request_filters: bool = False,
    # What: complete the enclosing predicate with async def forward routed request request model str path and query str; why: forward_routed groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        """Select a configured model, then stream the engine response unchanged.

        The lease spans the full downstream iterator. If a client disconnects,
        Starlette closes that iterator, which closes the upstream socket and
        releases admission for the next model swap.
        """
        # What: document select a configured model then stream in the forward_routed docstring; why: introspection and maintainers read this exact docstring fragment to understand forward routed behavior without executing it.
        # What: document the lease spans the full downstream in the forward_routed docstring; why: introspection and maintainers read this exact docstring fragment to understand forward routed behavior without executing it.
        # What: document starlette closes that iterator which closes in the forward_routed docstring; why: introspection and maintainers read this exact docstring fragment to understand forward routed behavior without executing it.
        # What: document releases admission for the next model in the forward_routed docstring; why: introspection and maintainers read this exact docstring fragment to understand forward routed behavior without executing it.
        # What: preserve the paragraph boundary in the the forward_routed docstring; why: introspection and maintainers read this paragraph break to understand forward routed behavior without executing it.
        # What: compute started from monotonic and time; why: yield observed loading frame f done time monotonic later reads started, so forward_routed must retain the computed value under that name.
        started = time.monotonic()
        # What: compute request id from hex and get and headers and uuid4; why: if not request id isascii or not request id later reads request id, so forward_routed must retain the computed value under that name.
        request_id = request.headers.get("x-ft-request-id") or uuid.uuid4().hex
        # What: gate on request id and isascii and len before httpexception; why: forward_routed admits httpexception only for this predicate and excludes the opposite state.
        if not request_id.isascii() or not request_id or len(request_id) > 128:
            # What: raise HTTPException for the caller; why: forward_routed stops this rejected path before it can mutate state, dispatch work, or report success.
            raise HTTPException(status_code=400, detail="X-FT-Request-ID must be 1 to 128 ASCII characters")
        # Use FastAPI's registered route template, not the concrete path or
        # query. An upstream passthrough tail can itself contain a signed URL,
        # opaque bearer-like value, or tenant identifier.
        # What: compute safe route from getattr and method and get and request; why: router event request conflict profile model route safe route later reads safe route, so forward_routed must retain the computed value under that name.
        safe_route = getattr(request.scope.get("route"), "path", request.method)
        # What: compute admission cancellation from event and threading; why: cancellation admission cancellation later reads admission cancellation, so forward_routed must retain the computed value under that name.
        admission_cancellation = threading.Event()
        # What: compute capture limit from capture item limit and activity store; why: if capture limit and not capture overflow later reads capture limit, so forward_routed must retain the computed value under that name.
        capture_limit = activity_store.capture_item_limit
        # What: enter the inflight lock managed context before if request id in request reservations; why: forward_routed releases this resource or lock after if request id in request reservations on both success and failure paths.
        with inflight_lock:
            # What: gate on request id and request reservations before router event and model and safe route; why: forward_routed admits router event and model and safe route only for this predicate and excludes the opposite state.
            if request_id in request_reservations:
                # What: preserve the exact router event request conflict profile model route safe route literal fragment; why: forward_routed passes this fragment verbatim through router_event("request_conflict", profile=model, route=safe_route), because changing it would alter a protocol payload, serialized fixture.
                router_event("request_conflict", profile=model, route=safe_route)
                # What: return jsonresponse and 409 and error and message and type from forward_routed; why: forward_routed exposes jsonresponse and 409 and error and message and type so its caller can continue with the function\'s computed outcome.
                return JSONResponse(
                    # What: supply status code to JSONResponse; why: forward_routed binds this 409 value to JSONResponse's status code input.
                    status_code=409,
                    # What: map the error field as message and type and request and id and is; why: forward_routed carries error through content={"error": { into except exception as exc the lease must.
                    content={"error": {
                        # What: apply the message request id is already active portion of the enclosing predicate; why: this clause remains in forward_routed\'s enclosing expression so its grouping and evaluation order stay intact.
                        "message": "request id is already active", "type": "request_conflict",
                    # What: complete the enclosing predicate mapping with error; why: forward_routed groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
                    }},
                # What: complete the JSONResponse call with status code and content; why: forward_routed groups the supplied clauses as one JSONResponse call before its value is consumed.
                )
            # What: compute request reservations entry from model and admission cancellation and profile and cancellation and; why: forward_routed consumes request reservations entry during cancelled before connect request reservations request id cancelled, so request reservations entry value receives the computed val.
            request_reservations[request_id] = {
                # What: map the profile field as model; why: forward_routed carries profile through request reservations entry into cancelled before connect request reservations request id cancelled.
                "profile": model,
                # What: map the cancellation field as admission cancellation; why: forward_routed carries cancellation through request reservations entry into cancelled before connect request reservations request id cancelled.
                "cancellation": admission_cancellation,
                # What: map the cancelled field as false; why: forward_routed carries cancelled through request reservations entry into cancelled before connect request reservations request id cancelled.
                "cancelled": False,
            # What: complete the request_reservations entry mapping with profile and cancellation and cancelled; why: forward_routed groups the supplied clauses as one request_reservations entry mapping before its value is consumed.
            }

        # What: define filtered_body around route lease; why: its direct callers call filtered_body for filtered body and rely on this exact input and result contract.
        def filtered_body(route_lease) -> bytes:
            # What: gate on apply request filters before body; why: filtered_body admits body only for this predicate and excludes the opposite state.
            if not apply_request_filters:
                # What: return body from filtered_body; why: filtered_body exposes body so its caller can continue with the function\'s computed outcome.
                return body
            # What: compute profile from profile and route lease; why: profile drop fields later reads profile, so filtered_body must retain the computed value under that name.
            profile = route_lease.profile
            # What: compute target model from model id and model and route lease; why: requested model target model later reads target model, so filtered_body must retain the computed value under that name.
            target_model = route_lease.model_id or model
            # What: return filter request body and body and drop fields and set fields from filtered_body; why: filtered_body exposes filter request body and body and drop fields and set fields so its caller can continue with the function\'s computed outcome.
            return filter_request_body(
                # What: apply the body portion of the enclosing predicate; why: this clause remains in filtered_body\'s enclosing expression so its grouping and evaluation order stay intact.
                body,
                # What: apply the profile drop fields portion of the enclosing predicate; why: this clause remains in filtered_body\'s enclosing expression so its grouping and evaluation order stay intact.
                profile.drop_fields,
                # What: apply the profile set fields portion of the enclosing predicate; why: this clause remains in filtered_body\'s enclosing expression so its grouping and evaluation order stay intact.
                profile.set_fields,
                # What: apply the profile set fields by id portion of the enclosing predicate; why: this clause remains in filtered_body\'s enclosing expression so its grouping and evaluation order stay intact.
                profile.set_fields_by_id,
                # What: supply requested model to filter_request_body; why: filtered_body binds this target model value to filter_request_body's requested model input.
                requested_model=target_model,
                # What: supply rewrite model to filter_request_body; why: filtered_body binds this use model name and profile and target model and selector id value to filter_request_body's rewrite model input.
                rewrite_model=(
                    # What: apply the profile use model name portion of the enclosing predicate; why: this clause remains in filtered_body\'s enclosing expression so its grouping and evaluation order stay intact.
                    profile.use_model_name
                    # What: apply the or portion of the enclosing predicate; why: this clause remains in filtered_body\'s enclosing expression so its grouping and evaluation order stay intact.
                    or (
                        # What: apply the target model portion of the enclosing predicate; why: this clause remains in filtered_body\'s enclosing expression so its grouping and evaluation order stay intact.
                        target_model
                        # What: apply the if route lease selector id is not portion of the enclosing predicate; why: this clause remains in filtered_body\'s enclosing expression so its grouping and evaluation order stay intact.
                        if route_lease.selector_id is not None
                        # What: apply the or route lease routing profile id is not portion of the enclosing predicate; why: this clause remains in filtered_body\'s enclosing expression so its grouping and evaluation order stay intact.
                        or route_lease.routing_profile_id is not None
                        # What: apply the else portion of the enclosing predicate; why: this clause remains in filtered_body\'s enclosing expression so its grouping and evaluation order stay intact.
                        else None
                    # What: complete the filter_request_body call with requested model and rewrite model; why: filtered_body groups the supplied clauses as one filter_request_body call before its value is consumed.
                    )
                # What: complete the filter_request_body call with requested model and rewrite model; why: filtered_body groups the supplied clauses as one filter_request_body call before its value is consumed.
                ),
            # What: complete the filter_request_body call with requested model and rewrite model; why: filtered_body groups the supplied clauses as one filter_request_body call before its value is consumed.
            )

        # What: define lease_event_identity around route lease; why: its direct callers call lease_event_identity for lease event identity and rely on this exact input and result contract.
        def lease_event_identity(route_lease) -> dict[str, str]:
            # What: map the profile field as name and profile and route lease; why: lease_event_identity carries profile through identity into identity selector route lease selector id.
            identity = {"profile": route_lease.profile.name}
            # What: gate on selector id and route lease before selector id and identity and route lease; why: lease_event_identity admits selector id and identity and route lease only for this predicate and excludes the opposite state.
            if route_lease.selector_id is not None:
                # What: compute identity entry from selector id and route lease; why: identity target route lease model id later reads identity entry, so lease_event_identity must retain the computed value under that name.
                identity["selector"] = route_lease.selector_id
                # What: compute identity entry from model id and route lease; why: identity routing profile route lease routing profile id later reads identity entry, so lease_event_identity must retain the computed value under that name.
                identity["target"] = route_lease.model_id
            # What: gate on routing profile id and route lease before routing profile id and identity and route lease; why: lease_event_identity admits routing profile id and identity and route lease only for this predicate and excludes the opposite state.
            if route_lease.routing_profile_id is not None:
                # What: compute identity entry from routing profile id and route lease; why: identity pin route lease pin id later reads identity entry, so lease_event_identity must retain the computed value under that name.
                identity["routingProfile"] = route_lease.routing_profile_id
                # What: compute identity entry from pin id and route lease; why: identity setdefault target route lease model id later reads identity entry, so lease_event_identity must retain the computed value under that name.
                identity["pin"] = route_lease.pin_id
                # What: preserve the exact identity setdefault target route lease model id literal fragment; why: lease_event_identity passes this fragment verbatim through identity.setdefault("target", route_lease.model_id), because changing it would alter a protocol payload, serialized fixture, or public message.
                identity.setdefault("target", route_lease.model_id)
            # What: return identity from lease_event_identity; why: lease_event_identity exposes identity so its caller can continue with the function\'s computed outcome.
            return identity

        # What: define loading_frame around text; why: its direct callers call loading_frame for loading frame and rely on this exact input and result contract.
        def loading_frame(text: str) -> bytes:
            # What: map the choices field as text and delta and reasoning content; why: loading_frame carries choices through payload into payload separators ensure ascii false.
            payload = {"choices": [{"delta": {"reasoning_content": text}}]}
            # What: return encode and dumps and payload and json and utf 8 from loading_frame; why: loading_frame exposes encode and dumps and payload and json and utf 8 so its caller can continue with the function\'s computed outcome.
            return b"data: " + json.dumps(
                # What: supply separators to operation.encode; why: loading_frame binds this value and value value to operation.encode's separators input.
                payload, separators=(",", ":"), ensure_ascii=False
            # What: apply the encode utf 8 b n n portion of the enclosing predicate; why: this clause remains in loading_frame\'s enclosing expression so its grouping and evaluation order stay intact.
            ).encode("utf-8") + b"\n\n"

        # What: define loading_error around exc; why: its direct callers call loading_error for loading error and rely on this exact input and result contract.
        def loading_error(exc: BaseException) -> bytes:
            # What: compute error type from code and isinstance and exc and routing error and upstream unavailable; why: payload dict str any error message later reads error type, so loading_error must retain the computed value under that name.
            error_type = exc.code if isinstance(exc, RoutingError) else "upstream_unavailable"
            # What: map the error field as error type and str and exc and message and type; why: loading_error carries error through payload into payload recovery exc recovery.
            payload: dict[str, Any] = {"error": {"message": str(exc), "type": error_type}}
            # What: gate on isinstance and exc and routing error and recovery before recovery and payload and exc; why: loading_error admits recovery and payload and exc only for this predicate and excludes the opposite state.
            if isinstance(exc, RoutingError) and exc.recovery is not None:
                # What: compute payload entry from recovery and exc; why: json dumps payload separators encode utf 8 later reads payload entry, so loading_error must retain the computed value under that name.
                payload["recovery"] = exc.recovery
            # What: return encode and dumps and payload and json and utf 8 from loading_error; why: loading_error exposes encode and dumps and payload and json and utf 8 so its caller can continue with the function\'s computed outcome.
            return (
                # What: apply the b data portion of the enclosing predicate; why: this clause remains in loading_error\'s enclosing expression so its grouping and evaluation order stay intact.
                b"data: "
                # What: supply separators to operation.encode; why: loading_error binds this value and value value to operation.encode's separators input.
                + json.dumps(payload, separators=(",", ":")).encode("utf-8")
                # What: apply the b n ndata done n n portion of the enclosing predicate; why: this clause remains in loading_error\'s enclosing expression so its grouping and evaluation order stay intact.
                + b"\n\ndata: [DONE]\n\n"
            # What: complete the loading_error signature with exc; why: loading_error groups the supplied clauses as one loading_error signature before its value is consumed.
            )

        # What: map the done field as false; why: forward_routed carries done through abandon state into if abandon state done.
        abandon_state = {"done": False}

        # What: define abandon_loading_acquisition around acquisition and record cancellation; why: its direct callers call abandon_loading_acquisition for abandon loading acquisition and rely on this exact input and result contract.
        def abandon_loading_acquisition(
            # What: declare the acquisition input for abandon_loading_acquisition; why: abandon_loading_acquisition consumes acquisition during acquisition add done callback release if admitted, so callers must bind it with the other signature inputs.
            acquisition: asyncio.Task, *, record_cancellation: bool = True
        # What: complete the enclosing predicate with group delimiter; why: abandon_loading_acquisition groups the supplied clauses as one enclosing predicate expression before its value is consumed.
        ) -> None:
            """Wake an abandoned admission and release any lease it later returns."""
            # What: document wake an abandoned admission and release in the abandon_loading_acquisition docstring; why: introspection and maintainers read this exact docstring fragment to understand abandon loading acquisition behavior without executing it.
            # What: gate on abandon state before the computed value; why: abandon_loading_acquisition admits the computed value only for this predicate and excludes the opposite state.
            if abandon_state["done"]:
                # What: return no value from abandon_loading_acquisition; why: abandon_loading_acquisition returns no value to callers that depend on its completed result.
                return
            # What: compute abandon state entry from true; why: the enclosing return or state update later reads abandon state entry, so abandon_loading_acquisition must retain the computed value under that name.
            abandon_state["done"] = True
            # What: call router.cancel_acquire with admission cancellation; why: abandon_loading_acquisition invokes router.cancel_acquire while performing if record cancellation; the call advances that operation through its result or side effect.
            router.cancel_acquire(admission_cancellation)
            # What: gate on record cancellation before record cancellation and router; why: abandon_loading_acquisition admits record cancellation and router only for this predicate and excludes the opposite state.
            if record_cancellation:
                # What: call router.record_cancellation with the declared inputs; why: abandon_loading_acquisition invokes router.record_cancellation while performing def release if admitted done asyncio task; the call advances that operation through its result or side effect.
                router.record_cancellation()

            # What: define release_if_admitted around done; why: its direct callers call release_if_admitted for release if admitted and rely on this exact input and result contract.
            def release_if_admitted(done: asyncio.Task) -> None:
                # What: establish the handler boundary for the protected operation; why: release_if_admitted routes failures to base exception while preserving cleanup and success flow.
                try:
                    # What: compute admitted from result and done; why: admitted release later reads admitted, so release_if_admitted must retain the computed value under that name.
                    admitted = done.result()
                # What: handle base exception by return; why: release_if_admitted converts that failure into this concrete recovery, response, or cleanup behavior.
                except BaseException:
                    # What: return no value from release_if_admitted; why: release_if_admitted returns no value to callers that depend on its completed result.
                    return
                # What: call admitted.release with the declared inputs; why: release_if_admitted invokes admitted.release while performing the enclosing return; the call advances that operation through its result or side effect.
                admitted.release()

            # What: call acquisition.add_done_callback with release if admitted; why: abandon_loading_acquisition invokes acquisition.add_done_callback while performing the enclosing return; the call advances that operation through its result or side effect.
            acquisition.add_done_callback(release_if_admitted)

        # What: define loading_stream around acquisition; why: its direct callers call loading_stream for loading stream and rely on this exact input and result contract.
        async def loading_stream(acquisition: asyncio.Task):
            """Bridge one admitted cold request into loading SSE, then its real response."""
            # What: document bridge one admitted cold request into in the loading_stream docstring; why: introspection and maintainers read this exact docstring fragment to understand loading stream behavior without executing it.
            # What: compute lease from the named fixture input; why: lease acquisition result later reads lease, so loading_stream must retain the computed value under that name.
            lease = None
            # What: compute upstream from the named fixture input; why: request cancelled before upstream connection later reads upstream, so loading_stream must retain the computed value under that name.
            upstream = None
            # What: compute first byte at from the named fixture input; why: if first byte at is later reads first byte at, so loading_stream must retain the computed value under that name.
            first_byte_at = None
            # What: compute byte count from 0; why: byte count len chunk later reads byte count, so loading_stream must retain the computed value under that name.
            byte_count = 0
            # What: compute cancelled from false; why: cancelled before connect request reservations request id cancelled later reads cancelled, so loading_stream must retain the computed value under that name.
            cancelled = False
            # What: compute cancellation recorded from false; why: cancellation recorded later reads cancellation recorded, so loading_stream must retain the computed value under that name.
            cancellation_recorded = False
            # What: compute last position from the named fixture input; why: last position initial position later reads last position, so loading_stream must retain the computed value under that name.
            last_position = None
            # What: compute outbound body from body; why: outbound body filtered body lease later reads outbound body, so loading_stream must retain the computed value under that name.
            outbound_body = body
            # What: compute captured response from bytearray; why: if len captured response len chunk capture limit later reads captured response, so loading_stream must retain the computed value under that name.
            captured_response = bytearray()
            # What: compute capture overflow from false; why: nonlocal capture overflow later reads capture overflow, so loading_stream must retain the computed value under that name.
            capture_overflow = False

            # What: define observed around chunk; why: its direct callers call observed for observed and rely on this exact input and result contract.
            def observed(chunk: bytes) -> bytes:
                # What: apply the nonlocal capture overflow portion of the enclosing predicate; why: this clause remains in observed\'s enclosing expression so its grouping and evaluation order stay intact.
                nonlocal capture_overflow
                # What: gate on capture limit and capture overflow before capture limit and capture overflow and extend and chunk and clear; why: observed admits capture limit and capture overflow and extend and chunk and clear only for this predicate and excludes the opposite state.
                if capture_limit and not capture_overflow:
                    # What: gate on capture limit and len and captured response and chunk before extend and chunk and captured response; why: observed admits extend and chunk and captured response only for this predicate and excludes the opposite state.
                    if len(captured_response) + len(chunk) <= capture_limit:
                        # What: call captured_response.extend with chunk; why: observed invokes captured_response.extend while performing else; the call advances that operation through its result or side effect.
                        captured_response.extend(chunk)
                    # What: select the remaining branch that performs capture overflow; why: observed covers the state excluded by the preceding predicate without conflating the two outcomes.
                    else:
                        # What: compute capture overflow from true; why: the enclosing return or state update later reads capture overflow, so observed must retain the computed value under that name.
                        capture_overflow = True
                        # What: call captured_response.clear with the declared inputs; why: observed invokes captured_response.clear while performing return chunk; the call advances that operation through its result or side effect.
                        captured_response.clear()
                # What: return chunk from observed; why: observed exposes chunk so its caller can continue with the function\'s computed outcome.
                return chunk
            # What: establish the handler boundary for the protected operation; why: loading_stream routes failures to cancelled error and asyncio and exception while preserving cleanup and success flow.
            try:
                # What: preserve the exact yield observed loading frame n literal fragment; why: loading_stream passes this fragment verbatim through yield observed(loading_frame("━━━━━\n")), because changing it would alter a protocol payload, serialized fixture, or public message.
                yield observed(loading_frame("━━━━━\n"))
                # What: embed the exact yield observed loading frame f freetoken swap loading router-interface fragment; why: the router UI consumer receives this fragment verbatim through yield observed(loading_frame(f"freetoken-swap loading model: {model}\n"), preserving browser markup, style, or script behavior.
                yield observed(loading_frame(f"freetoken-swap loading model: {model}\n"))
                # What: compute initial position from get and reservation state and queue position; why: if isinstance initial position int later reads initial position, so loading_stream must retain the computed value under that name.
                initial_position = reservation_state.get("queuePosition")
                # What: gate on isinstance and initial position and int before last position and initial position; why: loading_stream admits last position and initial position only for this predicate and excludes the opposite state.
                if isinstance(initial_position, int):
                    # What: compute last position from initial position; why: if position is not and position later reads last position, so loading_stream must retain the computed value under that name.
                    last_position = initial_position
                    # What: execute yield observed loading frame f nQueue position initial position; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
                    yield observed(loading_frame(f"\nQueue position: #{initial_position} "))
                # What: iterate across done and acquisition to perform position and queue position and admission cancellation and router; why: loading_stream repeats the body only while or for the loop header admits an iteration.
                while not acquisition.done():
                    # What: compute position from queue position and admission cancellation and router; why: if position is not and position later reads position, so loading_stream must retain the computed value under that name.
                    position = router.queue_position(admission_cancellation)
                    # What: gate on position and last position before last position and position; why: loading_stream admits last position and position only for this predicate and excludes the opposite state.
                    if position is not None and position != last_position:
                        # What: compute last position from position; why: the enclosing return or state update later reads last position, so loading_stream must retain the computed value under that name.
                        last_position = position
                        # What: execute yield observed loading frame f nQueue position position; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
                        yield observed(loading_frame(f"\nQueue position: #{position} "))
                    # What: compute done and from wait and asyncio and acquisition and 0 75; why: if acquisition in done later reads done and, so loading_stream must retain the computed value under that name.
                    done, _ = await asyncio.wait({acquisition}, timeout=0.75)
                    # What: gate on acquisition and done before lease and result and acquisition; why: loading_stream admits lease and result and acquisition only for this predicate and excludes the opposite state.
                    if acquisition in done:
                        # What: compute lease from result and acquisition; why: if lease is later reads lease, so loading_stream must retain the computed value under that name.
                        lease = acquisition.result()
                    # What: select the remaining branch that performs yield observed loading frame; why: loading_stream covers the state excluded by the preceding predicate without conflating the two outcomes.
                    else:
                        # What: preserve the exact yield observed loading frame literal fragment; why: loading_stream passes this fragment verbatim through yield observed(loading_frame(".")), because changing it would alter a protocol payload, serialized fixture, or public message.
                        yield observed(loading_frame("."))
                # What: gate on lease before lease and result and acquisition; why: loading_stream admits lease and result and acquisition only for this predicate and excludes the opposite state.
                if lease is None:
                    # What: compute lease from result and acquisition; why: outbound body filtered body lease later reads lease, so loading_stream must retain the computed value under that name.
                    lease = acquisition.result()

                # What: preserve the exact yield observed loading frame n literal fragment; why: loading_stream passes this fragment verbatim through yield observed(loading_frame("\n")), because changing it would alter a protocol payload, serialized fixture, or public message.
                yield observed(loading_frame("\n"))
                # What: embed the exact yield observed loading frame f done time monotonic router-interface fragment; why: the router UI consumer receives this fragment verbatim through yield observed(loading_frame(f"Done! ({time.monotonic() - started:.2f}s), preserving browser markup, style, or script behavior.
                yield observed(loading_frame(f"Done! ({time.monotonic() - started:.2f}s)\n"))
                # What: preserve the exact yield observed loading frame n literal fragment; why: loading_stream passes this fragment verbatim through yield observed(loading_frame("━━━━━\n")), because changing it would alter a protocol payload, serialized fixture, or public message.
                yield observed(loading_frame("━━━━━\n"))
                # What: preserve the exact yield observed loading frame n literal fragment; why: loading_stream passes this fragment verbatim through yield observed(loading_frame(" \n")), because changing it would alter a protocol payload, serialized fixture, or public message.
                yield observed(loading_frame(" \n"))

                # What: enter the inflight lock managed context before cancelled before connect request reservations request id cancelled; why: loading_stream releases this resource or lock after cancelled before connect request reservations request id cancelled on both success and failure paths.
                with inflight_lock:
                    # What: compute cancelled before connect from request reservations and request id and cancelled; why: if cancelled before connect later reads cancelled before connect, so loading_stream must retain the computed value under that name.
                    cancelled_before_connect = request_reservations[request_id]["cancelled"]
                # What: gate on cancelled before connect before routing error; why: loading_stream admits routing error only for this predicate and excludes the opposite state.
                if cancelled_before_connect:
                    # What: raise RoutingError for the caller; why: loading_stream stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise RoutingError(
                        # What: apply the request cancelled portion of the enclosing predicate; why: this clause remains in loading_stream\'s enclosing expression so its grouping and evaluation order stay intact.
                        "request_cancelled",
                        # What: apply the request cancelled before upstream connection portion of the enclosing predicate; why: this clause remains in loading_stream\'s enclosing expression so its grouping and evaluation order stay intact.
                        "request cancelled before upstream connection",
                        # What: supply status code to RoutingError; why: loading_stream binds this 409 value to RoutingError's status code input.
                        status_code=409,
                    # What: complete the RoutingError call with status code; why: loading_stream groups the supplied clauses as one RoutingError call before its value is consumed.
                    )

                # What: compute outbound body from filtered body and lease; why: body outbound body later reads outbound body, so loading_stream must retain the computed value under that name.
                outbound_body = filtered_body(lease)

                # What: compute upstream from connect upstream and port and proxy base url and path and query; why: upstream upstream later reads upstream, so loading_stream must retain the computed value under that name.
                upstream = await connect_upstream(
                    # What: supply port to connect_upstream; why: loading_stream binds this port and lease value to connect_upstream's port input.
                    port=lease.port,
                    # What: supply base url to connect_upstream; why: loading_stream binds this proxy base url and lease value to connect_upstream's base url input.
                    base_url=lease.proxy_base_url,
                    # What: supply path and query to connect_upstream; why: loading_stream binds this path and query value to connect_upstream's path and query input.
                    path_and_query=path_and_query,
                    # What: supply headers to dict; why: loading_stream binds this dict and headers and request value to dict's headers input.
                    headers=dict(request.headers),
                    # What: supply body to connect_upstream; why: loading_stream binds this outbound body value to connect_upstream's body input.
                    body=outbound_body,
                    # What: supply method to connect_upstream; why: loading_stream binds this method and request value to connect_upstream's method input.
                    method=request.method,
                    # What: supply timeout s to connect_upstream; why: loading_stream binds this upstream timeout s and profile and router and lease value to connect_upstream's timeout s input.
                    timeout_s=lease.profile.upstream_timeout_s or router.upstream_timeout_s,
                # What: complete the connect_upstream call with port and base url and path and query and headers and body; why: loading_stream groups the supplied clauses as one connect_upstream call before its value is consumed.
                )
                # What: enter the inflight lock managed context before cancelled while connecting request reservations request id cancelled; why: loading_stream releases this resource or lock after cancelled while connecting request reservations request id cancelled on both success and failure paths.
                with inflight_lock:
                    # What: compute cancelled while connecting from request reservations and request id and cancelled; why: if not cancelled while connecting later reads cancelled while connecting, so loading_stream must retain the computed value under that name.
                    cancelled_while_connecting = request_reservations[request_id]["cancelled"]
                    # What: gate on cancelled while connecting before inflight and request id and name and upstream and profile; why: loading_stream admits inflight and request id and name and upstream and profile only for this predicate and excludes the opposite state.
                    if not cancelled_while_connecting:
                        # What: compute inflight entry from name and upstream and profile and lease and profile; why: item inflight get request id later reads inflight entry, so loading_stream must retain the computed value under that name.
                        inflight[request_id] = {
                            # What: map the profile field as name and profile and lease; why: loading_stream carries profile through inflight entry into item inflight get request id.
                            "profile": lease.profile.name,
                            # What: map the upstream field as upstream; why: loading_stream carries upstream through inflight entry into item inflight get request id.
                            "upstream": upstream,
                            # What: map the cancelled field as false; why: loading_stream carries cancelled through inflight entry into item inflight get request id.
                            "cancelled": False,
                        # What: complete the inflight entry mapping with profile and upstream and cancelled; why: loading_stream groups the supplied clauses as one inflight entry mapping before its value is consumed.
                        }
                # What: gate on cancelled while connecting before routing error; why: loading_stream admits routing error only for this predicate and excludes the opposite state.
                if cancelled_while_connecting:
                    # What: raise RoutingError for the caller; why: loading_stream stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise RoutingError(
                        # What: apply the request cancelled portion of the enclosing predicate; why: this clause remains in loading_stream\'s enclosing expression so its grouping and evaluation order stay intact.
                        "request_cancelled",
                        # What: apply the request cancelled while opening upstream connection portion of the enclosing predicate; why: this clause remains in loading_stream\'s enclosing expression so its grouping and evaluation order stay intact.
                        "request cancelled while opening upstream connection",
                        # What: supply status code to RoutingError; why: loading_stream binds this 409 value to RoutingError's status code input.
                        status_code=409,
                    # What: complete the RoutingError call with status code; why: loading_stream groups the supplied clauses as one RoutingError call before its value is consumed.
                    )

                # What: call router_event with admitted; why: loading_stream invokes router_event while performing admitted lease event identity lease route safe route; the call advances that operation through its result or side effect.
                router_event(
                    # What: preserve the exact admitted lease event identity lease route safe route literal fragment; why: loading_stream passes this fragment verbatim through "admitted", **lease_event_identity(lease), route=safe_route, because changing it would alter a protocol payload, serialized fixture, or public.
                    "admitted", **lease_event_identity(lease), route=safe_route
                # What: complete the router_event call with route; why: loading_stream groups the supplied clauses as one router_event call before its value is consumed.
                )
                # What: compute iterator from iter and chunks and upstream; why: return next iterator later reads iterator, so loading_stream must retain the computed value under that name.
                iterator = iter(upstream.chunks())

                # What: define next_chunk around the current object state; why: its direct callers call next_chunk for next chunk and rely on this exact input and result contract.
                def next_chunk():
                    # What: establish the handler boundary for the protected operation; why: next_chunk routes failures to stop iteration while preserving cleanup and success flow.
                    try:
                        # What: return next and iterator and true from next_chunk; why: next_chunk exposes next and iterator and true so its caller can continue with the function\'s computed outcome.
                        return True, next(iterator)
                    # What: handle stop iteration by return false b; why: next_chunk converts that failure into this concrete recovery, response, or cleanup behavior.
                    except StopIteration:
                        # What: return false from next_chunk; why: next_chunk exposes false so its caller can continue with the function\'s computed outcome.
                        return False, b""

                # What: compute loop from get running loop and asyncio; why: has chunk chunk await loop run in executor proxy pool next chunk later reads loop, so loading_stream must retain the computed value under that name.
                loop = asyncio.get_running_loop()
                # What: iterate across the computed value to perform has chunk and chunk and run in executor and proxy pool and next chunk; why: loading_stream repeats the body only while or for the loop header admits an iteration.
                while True:
                    # What: compute has chunk and chunk from run in executor and proxy pool and next chunk and loop; why: if not has chunk later reads has chunk and chunk, so loading_stream must retain the computed value under that name.
                    has_chunk, chunk = await loop.run_in_executor(proxy_pool, next_chunk)
                    # What: gate on has chunk before the computed value; why: loading_stream admits the computed value only for this predicate and excludes the opposite state.
                    if not has_chunk:
                        # What: apply the break portion of the enclosing predicate; why: this clause remains in loading_stream\'s enclosing expression so its grouping and evaluation order stay intact.
                        break
                    # What: gate on first byte at before first byte at and monotonic and time; why: loading_stream admits first byte at and monotonic and time only for this predicate and excludes the opposite state.
                    if first_byte_at is None:
                        # What: compute first byte at from monotonic and time; why: ttft s first byte at started if first byte at is later reads first byte at, so loading_stream must retain the computed value under that name.
                        first_byte_at = time.monotonic()
                    # What: compute byte count from len and chunk; why: response bytes byte count later reads byte count, so loading_stream must retain the computed value under that name.
                    byte_count += len(chunk)
                    # What: call observed with chunk; why: loading_stream invokes observed while performing except asyncio cancelled error; the call advances that operation through its result or side effect.
                    yield observed(chunk)
            # What: handle cancelled error and asyncio by cancelled true; why: loading_stream converts that failure into this concrete recovery, response, or cleanup behavior.
            except asyncio.CancelledError:
                # What: compute cancelled from true; why: cancelled later reads cancelled, so loading_stream must retain the computed value under that name.
                cancelled = True
                # What: call abandon_loading_acquisition with acquisition; why: loading_stream invokes abandon_loading_acquisition while performing cancellation recorded; the call advances that operation through its result or side effect.
                abandon_loading_acquisition(acquisition)
                # What: compute cancellation recorded from true; why: acquisition record cancellation not cancellation recorded later reads cancellation recorded, so loading_stream must retain the computed value under that name.
                cancellation_recorded = True
                # What: preserve the exact router event request cancelled profile model route safe route literal fragment; why: loading_stream passes this fragment verbatim through router_event("request_cancelled", profile=model, route=safe_route), because changing it would alter a protocol payload, serialized fixture.
                router_event("request_cancelled", profile=model, route=safe_route)
                # What: re-propagate the active failure to the caller; why: loading_stream stops this rejected path before it can mutate state, dispatch work, or report success.
                raise
            # What: handle exception by if isinstance exc routing error; why: loading_stream converts that failure into this concrete recovery, response, or cleanup behavior.
            except Exception as exc:
                # What: gate on isinstance and exc and routing error before router event and model and safe route and code and exc; why: loading_stream admits router event and model and safe route and code and exc only for this predicate and excludes the opposite state.
                if isinstance(exc, RoutingError):
                    # What: preserve the exact router event admission failed profile model route safe route literal fragment; why: loading_stream passes this fragment verbatim through router_event("admission_failed", profile=model, route=safe_route, code=e, because changing it would alter a protocol payload, serialize.
                    router_event("admission_failed", profile=model, route=safe_route, code=exc.code)
                # What: select the remaining branch that performs router event upstream connect failed profile model route safe route; why: loading_stream covers the state excluded by the preceding predicate without conflating the two outcomes.
                else:
                    # What: preserve the exact router event upstream connect failed profile model route safe route literal fragment; why: loading_stream passes this fragment verbatim through router_event("upstream_connect_failed", profile=model, route=safe_route), because changing it would alter a protocol payload, se.
                    router_event("upstream_connect_failed", profile=model, route=safe_route)
                # What: call observed with loading error and exc; why: loading_stream invokes observed while performing finally; the call advances that operation through its result or side effect.
                yield observed(loading_error(exc))
            # What: run ended time monotonic on every exit path; why: loading_stream performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
            finally:
                # What: compute ended from monotonic and time; why: duration s ended started later reads ended, so loading_stream must retain the computed value under that name.
                ended = time.monotonic()
                # Starlette may finalize an async response iterator with
                # ``GeneratorExit`` rather than injecting ``CancelledError``.
                # A downstream that disappears must still synchronously wake
                # and cancel any queued ownership.
                # What: gate on done and acquisition before cancelled; why: loading_stream admits cancelled only for this predicate and excludes the opposite state.
                if not acquisition.done():
                    # What: compute cancelled from true; why: cancelled later reads cancelled, so loading_stream must retain the computed value under that name.
                    cancelled = True
                    # What: call abandon_loading_acquisition with acquisition; why: loading_stream invokes abandon_loading_acquisition while performing acquisition record cancellation not cancellation recorded; the call advances that operation through its result or side effect.
                    abandon_loading_acquisition(
                        # What: supply record cancellation to abandon_loading_acquisition; why: loading_stream binds this cancellation recorded value to abandon_loading_acquisition's record cancellation input.
                        acquisition, record_cancellation=not cancellation_recorded
                    # What: complete the abandon_loading_acquisition call with record cancellation; why: loading_stream groups the supplied clauses as one abandon_loading_acquisition call before its value is consumed.
                    )
                # What: gate on lease before lease and base exception and cancelled and result and cancellation recorded; why: loading_stream admits lease and base exception and cancelled and result and cancellation recorded only for this predicate and excludes the opposite state.
                elif lease is None:
                    # What: establish the handler boundary for the protected operation; why: loading_stream routes failures to base exception while preserving cleanup and success flow.
                    try:
                        # What: compute lease from result and acquisition; why: if lease is not later reads lease, so loading_stream must retain the computed value under that name.
                        lease = acquisition.result()
                    # What: handle base exception by pass; why: loading_stream converts that failure into this concrete recovery, response, or cleanup behavior.
                    except BaseException:
                        # What: ignore the anticipated exception handled by this branch; why: next_chunk continues its retry or cleanup path instead of re-raising that transient failure.
                        pass
                    # What: select the remaining branch that performs cancelled; why: loading_stream covers the state excluded by the preceding predicate without conflating the two outcomes.
                    else:
                        # What: compute cancelled from true; why: cancelled later reads cancelled, so loading_stream must retain the computed value under that name.
                        cancelled = True
                        # What: gate on cancellation recorded before record cancellation and router; why: loading_stream admits record cancellation and router only for this predicate and excludes the opposite state.
                        if not cancellation_recorded:
                            # What: call router.record_cancellation with the declared inputs; why: loading_stream invokes router.record_cancellation while performing if upstream is not; the call advances that operation through its result or side effect.
                            router.record_cancellation()
                # What: gate on upstream before close and upstream; why: loading_stream admits close and upstream only for this predicate and excludes the opposite state.
                if upstream is not None:
                    # What: call upstream.close with the declared inputs; why: loading_stream invokes upstream.close while performing with inflight lock; the call advances that operation through its result or side effect.
                    upstream.close()
                # What: enter the inflight lock managed context before reservation request reservations get request id; why: loading_stream releases this resource or lock after reservation request reservations get request id on both success and failure paths.
                with inflight_lock:
                    # What: compute reservation from get and request id and request reservations; why: or bool reservation get cancelled later reads reservation, so loading_stream must retain the computed value under that name.
                    reservation = request_reservations.get(request_id, {})
                    # What: compute item from get and request id and inflight; why: or bool item get cancelled later reads item, so loading_stream must retain the computed value under that name.
                    item = inflight.get(request_id, {})
                    # What: compute cancelled from cancelled and bool and get and reservation; why: cancelled later reads cancelled, so loading_stream must retain the computed value under that name.
                    cancelled = (
                        # What: apply the cancelled portion of cancelled; why: loading_stream uses this clause to evaluate cancelled as one grouped value.
                        cancelled
                        # What: call bool with get and reservation and cancelled; why: loading_stream invokes bool while performing or bool item get cancelled; the call advances that operation through its result or side effect.
                        or bool(reservation.get("cancelled"))
                        # What: call bool with get and item and cancelled; why: loading_stream consumes the bool return value while evaluating or bool(item.get("cancelled")).
                        or bool(item.get("cancelled"))
                    # What: complete the cancelled expression with cancelled cancelled or bool reservation get cancelled or bool item get; why: loading_stream groups the supplied clauses as one cancelled expression before its value is consumed.
                    )
                    # What: gate on upstream and get and item before pop and request id and inflight; why: loading_stream admits pop and request id and inflight only for this predicate and excludes the opposite state.
                    if upstream is not None and item.get("upstream") is upstream:
                        # What: call inflight.pop with request id and the named fixture input; why: loading_stream invokes inflight.pop while performing request reservations pop request id; the call advances that operation through its result or side effect.
                        inflight.pop(request_id, None)
                    # What: call request_reservations.pop with request id and the named fixture input; why: loading_stream invokes request_reservations.pop while performing if lease is not; the call advances that operation through its result or side effect.
                    request_reservations.pop(request_id, None)
                # What: gate on lease before ttft s and first byte at and started; why: loading_stream admits ttft s and first byte at and started only for this predicate and excludes the opposite state.
                if lease is not None:
                    # What: compute ttft s from first byte at and started; why: ttft s ttft s later reads ttft s, so loading_stream must retain the computed value under that name.
                    ttft_s = (first_byte_at - started) if first_byte_at is not None else None
                    # What: call router.record_stream with the declared inputs; why: loading_stream invokes router.record_stream while performing ttft s ttft s; the call advances that operation through its result or side effect.
                    router.record_stream(
                        # What: supply ttft s to router.record_stream; why: loading_stream binds this ttft s value to router.record_stream's ttft s input.
                        ttft_s=ttft_s,
                        # What: supply duration s to router.record_stream; why: loading_stream binds this ended and started value to router.record_stream's duration s input.
                        duration_s=ended - started,
                        # What: supply response bytes to router.record_stream; why: loading_stream binds this byte count value to router.record_stream's response bytes input.
                        response_bytes=byte_count,
                        # What: supply completed to router.record_stream; why: loading_stream binds this cancelled value to router.record_stream's completed input.
                        completed=not cancelled,
                    # What: complete the router.record_stream call with ttft s and duration s and response bytes and completed; why: loading_stream groups the supplied clauses as one router.record_stream call before its value is consumed.
                    )
                    # What: call lease.release with the declared inputs; why: loading_stream invokes lease.release while performing router event; the call advances that operation through its result or side effect.
                    lease.release()
                    # What: call router_event with request finished; why: loading_stream invokes router_event while performing request finished; the call advances that operation through its result or side effect.
                    router_event(
                        # What: preserve the exact request finished literal fragment; why: loading_stream passes this fragment verbatim through "request_finished", because changing it would alter a protocol payload, serialized fixture, or public message.
                        "request_finished",
                        # What: supply expanded arguments to lease_event_identity; why: loading_stream binds this lease event identity and lease value to lease_event_identity's expanded input.
                        **lease_event_identity(lease),
                        # What: supply route to router_event; why: loading_stream binds this safe route value to router_event's route input.
                        route=safe_route,
                        # What: supply status to router_event; why: loading_stream binds this status and upstream and 200 value to router_event's status input.
                        status=upstream.status if upstream is not None else 200,
                        # What: supply cancelled to router_event; why: loading_stream binds this cancelled value to router_event's cancelled input.
                        cancelled=cancelled,
                        # What: supply response bytes to router_event; why: loading_stream binds this byte count value to router_event's response bytes input.
                        responseBytes=byte_count,
                    # What: complete the router_event call with route and status and cancelled and response bytes; why: loading_stream groups the supplied clauses as one router_event call before its value is consumed.
                    )
                    # What: call asyncio.get_running_loop with the declared inputs; why: loading_stream invokes asyncio.get_running_loop while performing proxy pool; the call advances that operation through its result or side effect.
                    await asyncio.get_running_loop().run_in_executor(
                        # What: apply the proxy pool portion of the enclosing predicate; why: this clause remains in loading_stream\'s enclosing expression so its grouping and evaluation order stay intact.
                        proxy_pool,
                        # What: call functools.partial with record and activity store; why: loading_stream invokes functools.partial while performing activity store record; the call advances that operation through its result or side effect.
                        functools.partial(
                            # What: apply the activity store record portion of the enclosing predicate; why: this clause remains in loading_stream\'s enclosing expression so its grouping and evaluation order stay intact.
                            activity_store.record,
                            # What: supply model to functools.partial; why: loading_stream binds this name and profile and lease value to functools.partial's model input.
                            model=lease.profile.name,
                            # What: supply route to functools.partial; why: loading_stream binds this safe route value to functools.partial's route input.
                            route=safe_route,
                            # What: supply method to functools.partial; why: loading_stream binds this method and request value to functools.partial's method input.
                            method=request.method,
                            # What: supply status to functools.partial; why: loading_stream binds this status and upstream and 200 value to functools.partial's status input.
                            status=upstream.status if upstream is not None else 200,
                            # What: supply started to functools.partial; why: loading_stream binds this started value to functools.partial's started input.
                            started=started,
                            # What: supply ttft s to functools.partial; why: loading_stream binds this ttft s value to functools.partial's ttft s input.
                            ttft_s=ttft_s,
                            # What: supply response bytes to functools.partial; why: loading_stream binds this byte count value to functools.partial's response bytes input.
                            response_bytes=byte_count,
                            # What: supply cancelled to functools.partial; why: loading_stream binds this cancelled value to functools.partial's cancelled input.
                            cancelled=cancelled,
                            # What: supply request headers to dict; why: loading_stream binds this dict and headers and request value to dict's request headers input.
                            request_headers=dict(request.headers),
                            # What: supply request body to functools.partial; why: loading_stream binds this outbound body value to functools.partial's request body input.
                            request_body=outbound_body,
                            # What: supply response headers to functools.partial; why: loading_stream binds this headers and upstream value to functools.partial's response headers input.
                            response_headers=upstream.headers if upstream is not None else {},
                            # What: supply response body to functools.partial; why: loading_stream binds this capture overflow and bytes and captured response and upstream value to functools.partial's response body input.
                            response_body=(
                                # What: apply the if upstream is or capture overflow portion of the enclosing predicate; why: this clause remains in loading_stream\'s enclosing expression so its grouping and evaluation order stay intact.
                                None if upstream is None or capture_overflow
                                # What: call bytes with captured response; why: loading_stream consumes the bytes return value while evaluating else bytes(captured_response).
                                else bytes(captured_response)
                            # What: complete the functools.partial call with model and route and method and status and started; why: loading_stream groups the supplied clauses as one functools.partial call before its value is consumed.
                            ),
                        # What: complete the functools.partial call with model and route and method and status and started; why: loading_stream groups the supplied clauses as one functools.partial call before its value is consumed.
                        ),
                    # What: complete the operation.run_in_executor call with proxy pool and partial; why: loading_stream groups the supplied clauses as one operation.run_in_executor call before its value is consumed.
                    )

        # What: compute loading eligible from false; why: loading eligible isinstance request doc dict and request doc get later reads loading eligible, so forward_routed must retain the computed value under that name.
        loading_eligible = False
        # What: gate on path and url and request before request doc and loads and body and unicode decode error and jsondecode error; why: forward_routed admits request doc and loads and body and unicode decode error and jsondecode error only for this predicate and excludes the opposite state.
        if request.url.path == "/v1/chat/completions":
            # What: establish the handler boundary for the protected operation; why: forward_routed routes failures to unicode decode error and jsondecode error and json while preserving cleanup and success flow.
            try:
                # What: compute request doc from loads and body and json; why: request doc later reads request doc, so forward_routed must retain the computed value under that name.
                request_doc = json.loads(body)
            # What: handle unicode decode error and jsondecode error and json by request doc; why: forward_routed converts that failure into this concrete recovery, response, or cleanup behavior.
            except (UnicodeDecodeError, json.JSONDecodeError):
                # What: compute request doc from the named fixture input; why: loading eligible isinstance request doc dict and request doc get later reads request doc, so forward_routed must retain the computed value under that name.
                request_doc = None
            # What: compute loading eligible from isinstance and request doc and dict and get and true; why: if loading eligible later reads loading eligible, so forward_routed must retain the computed value under that name.
            loading_eligible = isinstance(request_doc, dict) and request_doc.get("stream") is True

        # What: gate on loading eligible before loop and get running loop and asyncio; why: forward_routed admits loop and get running loop and asyncio only for this predicate and excludes the opposite state.
        if loading_eligible:
            # What: compute loop from get running loop and asyncio; why: loop call soon threadsafe reserved set later reads loop, so forward_routed must retain the computed value under that name.
            loop = asyncio.get_running_loop()
            # What: compute reserved from event and asyncio; why: loop call soon threadsafe reserved set later reads reserved, so forward_routed must retain the computed value under that name.
            reserved = asyncio.Event()
            # What: initialize reservation state as an empty runtime accumulator; why: forward_routed appends or maps entries into it during reservation state loading required loading required before consuming the aggregate.
            reservation_state: dict[str, Any] = {}

            # What: define on_reserved around loading required and queue position; why: its direct callers call on_reserved for on reserved and rely on this exact input and result contract.
            def on_reserved(loading_required: bool, queue_position: int) -> None:
                # What: compute reservation state entry from loading required; why: reservation state queue position queue position later reads reservation state entry, so on_reserved must retain the computed value under that name.
                reservation_state["loadingRequired"] = loading_required
                # What: compute reservation state entry from queue position; why: the enclosing return or state update later reads reservation state entry, so on_reserved must retain the computed value under that name.
                reservation_state["queuePosition"] = queue_position
                # What: call loop.call_soon_threadsafe with set and reserved; why: on_reserved invokes loop.call_soon_threadsafe while performing the enclosing return; the call advances that operation through its result or side effect.
                loop.call_soon_threadsafe(reserved.set)

            # What: compute acquisition from create task and asyncio and acquire route and model; why: acquisition reservation wait return when asyncio first completed later reads acquisition, so forward_routed must retain the computed value under that name.
            acquisition = asyncio.create_task(
                # What: call acquire_route with model and admission cancellation and on reserved; why: forward_routed invokes acquire_route while performing model; the call advances that operation through its result or side effect.
                acquire_route(
                    # What: apply the model portion of acquisition; why: forward_routed uses this clause to evaluate acquisition as one grouped value.
                    model,
                    # What: apply the admission cancellation portion of acquisition; why: forward_routed uses this clause to evaluate acquisition as one grouped value.
                    admission_cancellation,
                    # What: apply the on reserved portion of acquisition; why: forward_routed uses this clause to evaluate acquisition as one grouped value.
                    on_reserved,
                    # What: supply apply loading policy to acquire_route; why: forward_routed binds this true value to acquire_route's apply loading policy input.
                    apply_loading_policy=True,
                # What: complete the acquire_route call with apply loading policy; why: forward_routed groups the supplied clauses as one acquire_route call before its value is consumed.
                )
            # What: complete the asyncio.create_task call with acquire route; why: forward_routed groups the supplied clauses as one asyncio.create_task call before its value is consumed.
            )
            # What: compute reservation wait from create task and asyncio and wait and reserved; why: acquisition reservation wait return when asyncio first completed later reads reservation wait, so forward_routed must retain the computed value under that name.
            reservation_wait = asyncio.create_task(reserved.wait())
            # What: establish the handler boundary for the protected operation; why: forward_routed routes failures to routing error and cancelled error and asyncio and base exception while preserving cleanup and success flow.
            try:
                # What: compute done and from wait and asyncio and acquisition and reservation wait; why: if acquisition in done later reads done and, so forward_routed must retain the computed value under that name.
                done, _ = await asyncio.wait(
                    # What: supply return when to asyncio.wait; why: forward_routed binds this first completed and asyncio value to asyncio.wait's return when input.
                    {acquisition, reservation_wait}, return_when=asyncio.FIRST_COMPLETED
                # What: complete the asyncio.wait call with return when; why: forward_routed groups the supplied clauses as one asyncio.wait call before its value is consumed.
                )
                # What: gate on acquisition and done before cancel and reservation wait; why: forward_routed admits cancel and reservation wait only for this predicate and excludes the opposite state.
                if acquisition in done:
                    # What: call reservation_wait.cancel with the declared inputs; why: forward_routed invokes reservation_wait.cancel while performing lease acquisition result; the call advances that operation through its result or side effect.
                    reservation_wait.cancel()
                    # What: compute lease from result and acquisition; why: lease await acquisition later reads lease, so forward_routed must retain the computed value under that name.
                    lease = acquisition.result()
                # What: select the remaining branch that performs if reservation state loading required; why: forward_routed covers the state excluded by the preceding predicate without conflating the two outcomes.
                else:
                    # What: gate on reservation state before streaming response and owned and inflight lock and call and scope; why: forward_routed admits streaming response and owned and inflight lock and call and scope only for this predicate and excludes the opposite state.
                    if reservation_state["loadingRequired"]:
                        # What: define AdmissionOwnedStreamingResponse as the owner of __call__; why: daemon callers use this class boundary so those methods share one admission owned streaming response state invariant.
                        class AdmissionOwnedStreamingResponse(StreamingResponse):
                            # What: define __call__ around scope and receive and send; why: its direct callers call __call__ for call and rely on this exact input and result contract.
                            async def __call__(self, scope, receive, send) -> None:
                                # What: establish the handler boundary for the protected operation; why: AdmissionOwnedStreamingResponse.__call__ routes failures to the unconditional cleanup block while preserving cleanup and success flow.
                                try:
                                    # What: call operation.__call__ with scope and receive and send; why: __call__ invokes operation.__call__ while performing finally; the call advances that operation through its result or side effect.
                                    await super().__call__(scope, receive, send)
                                # What: run async generator finalization can be deferred on every exit path; why: __call__ performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
                                finally:
                                    # Async-generator finalization can be deferred
                                    # beyond response termination. The response is
                                    # the ownership barrier for both unstarted and
                                    # suspended loading iterators.
                                    # What: enter the inflight lock managed context before owned request id in request reservations; why: __call__ releases this resource or lock after owned request id in request reservations on both success and failure paths.
                                    with inflight_lock:
                                        # What: compute owned from request id and request reservations; why: if owned later reads owned, so __call__ must retain the computed value under that name.
                                        owned = request_id in request_reservations
                                        # What: call request_reservations.pop with request id and the named fixture input; why: __call__ invokes request_reservations.pop while performing if owned; the call advances that operation through its result or side effect.
                                        request_reservations.pop(request_id, None)
                                    # What: gate on owned before abandon loading acquisition and acquisition; why: __call__ admits abandon loading acquisition and acquisition only for this predicate and excludes the opposite state.
                                    if owned:
                                        # What: call abandon_loading_acquisition with acquisition; why: __call__ invokes abandon_loading_acquisition while performing the enclosing return; the call advances that operation through its result or side effect.
                                        abandon_loading_acquisition(acquisition)

                        # What: return admission owned streaming response and loading stream and acquisition and request id and 200 from; why: forward_routed exposes admission owned streaming response and loading stream and acquisition and request id and 200 so its caller can continue with the function\'s computed outcome.
                        return AdmissionOwnedStreamingResponse(
                            # What: call loading_stream with acquisition; why: forward_routed invokes loading_stream while performing status code; the call advances that operation through its result or side effect.
                            loading_stream(acquisition),
                            # What: supply status code to AdmissionOwnedStreamingResponse; why: forward_routed binds this 200 value to AdmissionOwnedStreamingResponse's status code input.
                            status_code=200,
                            # What: supply headers to AdmissionOwnedStreamingResponse; why: forward_routed binds this request id and cache control and connection and x ft request id and no cache value to AdmissionOwnedStreamingResponse's headers input.
                            headers={
                                # What: map the cache control field as no cache; why: forward_routed carries cache control through "Cache-Control": "no-cache" into except exception as exc the lease must.
                                "Cache-Control": "no-cache",
                                # What: map the connection field as keep alive; why: forward_routed carries connection through "Connection": "keep-alive" into except exception as exc the lease must.
                                "Connection": "keep-alive",
                                # What: map the x ft request id field as request id; why: forward_routed carries x ft request id through "X-FT-Request-ID": request_id into except exception as exc the lease must.
                                "X-FT-Request-ID": request_id,
                            # What: complete the enclosing predicate mapping with cache control and connection and x ft request id; why: forward_routed groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
                            },
                            # What: supply media type to AdmissionOwnedStreamingResponse; why: forward_routed binds this text and event stream value to AdmissionOwnedStreamingResponse's media type input.
                            media_type="text/event-stream",
                        # What: complete the AdmissionOwnedStreamingResponse call with status code and headers and media type; why: forward_routed groups the supplied clauses as one AdmissionOwnedStreamingResponse call before its value is consumed.
                        )
                    # What: compute lease from acquisition; why: lease later reads lease, so forward_routed must retain the computed value under that name.
                    lease = await acquisition
            # What: handle routing error by reservation wait cancel; why: forward_routed converts that failure into this concrete recovery, response, or cleanup behavior.
            except RoutingError as exc:
                # What: call reservation_wait.cancel with the declared inputs; why: forward_routed invokes reservation_wait.cancel while performing with inflight lock; the call advances that operation through its result or side effect.
                reservation_wait.cancel()
                # What: enter the inflight lock managed context before request reservations pop request id; why: forward_routed releases this resource or lock after request reservations pop request id on both success and failure paths.
                with inflight_lock:
                    # What: call request_reservations.pop with request id and the named fixture input; why: forward_routed invokes request_reservations.pop while performing router event admission failed profile model route safe route; the call advances that operation through its result or side effect.
                    request_reservations.pop(request_id, None)
                # What: preserve the exact router event admission failed profile model route safe route literal fragment; why: forward_routed passes this fragment verbatim through router_event("admission_failed", profile=model, route=safe_route, code=e, because changing it would alter a protocol payload, serialized fi.
                router_event("admission_failed", profile=model, route=safe_route, code=exc.code)
                # What: map the error field as code and str and exc and message and type; why: forward_routed carries error through content into content recovery exc recovery.
                content = {"error": {"message": str(exc), "type": exc.code}}
                # What: gate on recovery and exc before recovery and content and exc; why: forward_routed admits recovery and content and exc only for this predicate and excludes the opposite state.
                if exc.recovery is not None:
                    # What: compute content entry from recovery and exc; why: content content later reads content entry, so forward_routed must retain the computed value under that name.
                    content["recovery"] = exc.recovery
                # What: return jsonresponse and status code and content and exc and 429 from forward_routed; why: forward_routed exposes jsonresponse and status code and content and exc and 429 so its caller can continue with the function\'s computed outcome.
                return JSONResponse(
                    # What: supply status code to JSONResponse; why: forward_routed binds this status code and exc value to JSONResponse's status code input.
                    status_code=exc.status_code,
                    # What: supply content to JSONResponse; why: forward_routed binds this content value to JSONResponse's content input.
                    content=content,
                    # What: map the retry after field as 1; why: forward_routed carries retry after through headers={"Retry-After": "1"} if exc.status_code == 429 else None into except exception as exc the lease must.
                    headers={"Retry-After": "1"} if exc.status_code == 429 else None,
                # What: complete the JSONResponse call with status code and content and headers; why: forward_routed groups the supplied clauses as one JSONResponse call before its value is consumed.
                )
            # What: handle cancelled error and asyncio by reservation wait cancel; why: forward_routed converts that failure into this concrete recovery, response, or cleanup behavior.
            except asyncio.CancelledError:
                # What: call reservation_wait.cancel with the declared inputs; why: forward_routed invokes reservation_wait.cancel while performing with inflight lock; the call advances that operation through its result or side effect.
                reservation_wait.cancel()
                # What: enter the inflight lock managed context before request reservations pop request id; why: forward_routed releases this resource or lock after request reservations pop request id on both success and failure paths.
                with inflight_lock:
                    # What: call request_reservations.pop with request id and the named fixture input; why: forward_routed invokes request_reservations.pop while performing abandon loading acquisition acquisition; the call advances that operation through its result or side effect.
                    request_reservations.pop(request_id, None)
                # What: call abandon_loading_acquisition with acquisition; why: forward_routed invokes abandon_loading_acquisition while performing raise; the call advances that operation through its result or side effect.
                abandon_loading_acquisition(acquisition)
                # What: re-propagate the active failure to the caller; why: forward_routed stops this rejected path before it can mutate state, dispatch work, or report success.
                raise
            # What: handle base exception by reservation wait cancel; why: forward_routed converts that failure into this concrete recovery, response, or cleanup behavior.
            except BaseException:
                # What: call reservation_wait.cancel with the declared inputs; why: forward_routed invokes reservation_wait.cancel while performing with inflight lock; the call advances that operation through its result or side effect.
                reservation_wait.cancel()
                # What: enter the inflight lock managed context before request reservations pop request id; why: forward_routed releases this resource or lock after request reservations pop request id on both success and failure paths.
                with inflight_lock:
                    # What: call request_reservations.pop with request id and the named fixture input; why: forward_routed invokes request_reservations.pop while performing if not acquisition done; the call advances that operation through its result or side effect.
                    request_reservations.pop(request_id, None)
                # What: gate on done and acquisition before abandon loading acquisition and acquisition; why: forward_routed admits abandon loading acquisition and acquisition only for this predicate and excludes the opposite state.
                if not acquisition.done():
                    # What: supply record cancellation to abandon_loading_acquisition; why: forward_routed binds this false value to abandon_loading_acquisition's record cancellation input.
                    abandon_loading_acquisition(acquisition, record_cancellation=False)
                # What: re-propagate the active failure to the caller; why: forward_routed stops this rejected path before it can mutate state, dispatch work, or report success.
                raise
            # What: run if not reservation wait done on every exit path; why: forward_routed performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
            finally:
                # What: gate on done and reservation wait before cancel and reservation wait; why: forward_routed admits cancel and reservation wait only for this predicate and excludes the opposite state.
                if not reservation_wait.done():
                    # What: call reservation_wait.cancel with the declared inputs; why: forward_routed invokes reservation_wait.cancel while performing else; the call advances that operation through its result or side effect.
                    reservation_wait.cancel()
        # What: select the remaining branch that performs lease; why: forward_routed covers the state excluded by the preceding predicate without conflating the two outcomes.
        else:
            # What: compute lease from the named fixture input; why: if lease is later reads lease, so forward_routed must retain the computed value under that name.
            lease = None
        # What: establish the handler boundary for the protected operation; why: forward_routed routes failures to routing error and cancelled error and asyncio and base exception while preserving cleanup and success flow.
        try:
            # What: gate on lease before lease and acquire route and model and admission cancellation; why: forward_routed admits lease and acquire route and model and admission cancellation only for this predicate and excludes the opposite state.
            if lease is None:
                # What: compute lease from acquire route and model and admission cancellation; why: lease release later reads lease, so forward_routed must retain the computed value under that name.
                lease = await acquire_route(model, admission_cancellation)
        # What: handle routing error by with inflight lock; why: forward_routed converts that failure into this concrete recovery, response, or cleanup behavior.
        except RoutingError as exc:
            # What: enter the inflight lock managed context before request reservations pop request id; why: forward_routed releases this resource or lock after request reservations pop request id on both success and failure paths.
            with inflight_lock:
                # What: call request_reservations.pop with request id and the named fixture input; why: forward_routed invokes request_reservations.pop while performing router event admission failed profile model route safe route; the call advances that operation through its result or side effect.
                request_reservations.pop(request_id, None)
            # What: preserve the exact router event admission failed profile model route safe route literal fragment; why: forward_routed passes this fragment verbatim through router_event("admission_failed", profile=model, route=safe_route, code=e, because changing it would alter a protocol payload, serialized fixtur.
            router_event("admission_failed", profile=model, route=safe_route, code=exc.code)
            # What: map the error field as code and str and exc and message and type; why: forward_routed carries error through content into content recovery exc recovery.
            content = {"error": {"message": str(exc), "type": exc.code}}
            # What: gate on recovery and exc before recovery and content and exc; why: forward_routed admits recovery and content and exc only for this predicate and excludes the opposite state.
            if exc.recovery is not None:
                # What: compute content entry from recovery and exc; why: content content later reads content entry, so forward_routed must retain the computed value under that name.
                content["recovery"] = exc.recovery
            # What: return jsonresponse and status code and content and exc and 429 from forward_routed; why: forward_routed exposes jsonresponse and status code and content and exc and 429 so its caller can continue with the function\'s computed outcome.
            return JSONResponse(
                # What: supply status code to JSONResponse; why: forward_routed binds this status code and exc value to JSONResponse's status code input.
                status_code=exc.status_code,
                # What: supply content to JSONResponse; why: forward_routed binds this content value to JSONResponse's content input.
                content=content,
                # What: map the retry after field as 1; why: forward_routed carries retry after through headers={"Retry-After": "1"} if exc.status_code == 429 else None into except exception as exc the lease must.
                headers={"Retry-After": "1"} if exc.status_code == 429 else None,
            # What: complete the JSONResponse call with status code and content and headers; why: forward_routed groups the supplied clauses as one JSONResponse call before its value is consumed.
            )
        # What: handle cancelled error and asyncio by with inflight lock; why: forward_routed converts that failure into this concrete recovery, response, or cleanup behavior.
        except asyncio.CancelledError:
            # What: enter the inflight lock managed context before request reservations pop request id; why: forward_routed releases this resource or lock after request reservations pop request id on both success and failure paths.
            with inflight_lock:
                # What: call request_reservations.pop with request id and the named fixture input; why: forward_routed invokes request_reservations.pop while performing router cancel acquire admission cancellation; the call advances that operation through its result or side effect.
                request_reservations.pop(request_id, None)
            # What: call router.cancel_acquire with admission cancellation; why: forward_routed invokes router.cancel_acquire while performing router record cancellation; the call advances that operation through its result or side effect.
            router.cancel_acquire(admission_cancellation)
            # What: call router.record_cancellation with the declared inputs; why: forward_routed invokes router.record_cancellation while performing router event request cancelled profile model route safe route; the call advances that operation through its result or side effect.
            router.record_cancellation()
            # What: preserve the exact router event request cancelled profile model route safe route literal fragment; why: forward_routed passes this fragment verbatim through router_event("request_cancelled", profile=model, route=safe_route), because changing it would alter a protocol payload, serialized fixture, or.
            router_event("request_cancelled", profile=model, route=safe_route)
            # What: re-propagate the active failure to the caller; why: forward_routed stops this rejected path before it can mutate state, dispatch work, or report success.
            raise
        # What: handle base exception by with inflight lock; why: forward_routed converts that failure into this concrete recovery, response, or cleanup behavior.
        except BaseException:
            # What: enter the inflight lock managed context before request reservations pop request id; why: forward_routed releases this resource or lock after request reservations pop request id on both success and failure paths.
            with inflight_lock:
                # What: call request_reservations.pop with request id and the named fixture input; why: forward_routed invokes request_reservations.pop while performing raise; the call advances that operation through its result or side effect.
                request_reservations.pop(request_id, None)
            # What: re-propagate the active failure to the caller; why: forward_routed stops this rejected path before it can mutate state, dispatch work, or report success.
            raise
        # What: enter the inflight lock managed context before cancelled before connect request reservations request id cancelled; why: forward_routed releases this resource or lock after cancelled before connect request reservations request id cancelled on both success and failure paths.
        with inflight_lock:
            # What: compute cancelled before connect from request reservations and request id and cancelled; why: if cancelled before connect later reads cancelled before connect, so forward_routed must retain the computed value under that name.
            cancelled_before_connect = request_reservations[request_id]["cancelled"]
            # What: gate on cancelled before connect before pop and request id and request reservations; why: forward_routed admits pop and request id and request reservations only for this predicate and excludes the opposite state.
            if cancelled_before_connect:
                # What: call request_reservations.pop with request id and the named fixture input; why: forward_routed invokes request_reservations.pop while performing if cancelled before connect; the call advances that operation through its result or side effect.
                request_reservations.pop(request_id, None)
        # What: gate on cancelled before connect before release and lease; why: forward_routed admits release and lease only for this predicate and excludes the opposite state.
        if cancelled_before_connect:
            # What: call lease.release with the declared inputs; why: forward_routed invokes lease.release while performing return jsonresponse; the call advances that operation through its result or side effect.
            lease.release()
            # What: return jsonresponse and 409 and error and message and type from forward_routed; why: forward_routed exposes jsonresponse and 409 and error and message and type so its caller can continue with the function\'s computed outcome.
            return JSONResponse(
                # What: supply status code to JSONResponse; why: forward_routed binds this 409 value to JSONResponse's status code input.
                status_code=409,
                # What: map the error field as message and type and request and cancelled and before; why: forward_routed carries error through content={"error": { into except exception as exc the lease must.
                content={"error": {
                    # What: apply the message request cancelled before upstream connection portion of the enclosing predicate; why: this clause remains in forward_routed\'s enclosing expression so its grouping and evaluation order stay intact.
                    "message": "request cancelled before upstream connection",
                    # What: apply the type request cancelled portion of the enclosing predicate; why: this clause remains in forward_routed\'s enclosing expression so its grouping and evaluation order stay intact.
                    "type": "request_cancelled",
                # What: complete the enclosing predicate mapping with error; why: forward_routed groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
                }},
            # What: complete the JSONResponse call with status code and content; why: forward_routed groups the supplied clauses as one JSONResponse call before its value is consumed.
            )
        # What: establish the handler boundary for the protected operation; why: forward_routed routes failures to request model error while preserving cleanup and success flow.
        try:
            # What: compute outbound body from filtered body and lease; why: body outbound body later reads outbound body, so forward_routed must retain the computed value under that name.
            outbound_body = filtered_body(lease)
        # What: handle request model error by lease release; why: forward_routed converts that failure into this concrete recovery, response, or cleanup behavior.
        except RequestModelError as exc:
            # What: call lease.release with the declared inputs; why: forward_routed invokes lease.release while performing with inflight lock; the call advances that operation through its result or side effect.
            lease.release()
            # What: enter the inflight lock managed context before request reservations pop request id; why: forward_routed releases this resource or lock after request reservations pop request id on both success and failure paths.
            with inflight_lock:
                # What: call request_reservations.pop with request id and the named fixture input; why: forward_routed invokes request_reservations.pop while performing return jsonresponse; the call advances that operation through its result or side effect.
                request_reservations.pop(request_id, None)
            # What: return jsonresponse and str and exc and 400 and error from forward_routed; why: forward_routed exposes jsonresponse and str and exc and 400 and error so its caller can continue with the function\'s computed outcome.
            return JSONResponse(
                # What: supply status code to JSONResponse; why: forward_routed binds this 400 value to JSONResponse's status code input.
                status_code=400,
                # What: map the error field as str and exc and message and type and invalid request; why: forward_routed carries error through content={"error": {"message": str(exc), "type": "invalid_request"}} into except exception as exc the lease must.
                content={"error": {"message": str(exc), "type": "invalid_request"}},
            # What: complete the JSONResponse call with status code and content; why: forward_routed groups the supplied clauses as one JSONResponse call before its value is consumed.
            )
        try:
            # What: compute upstream from connect upstream and port and proxy base url and path and query; why: upstream upstream later reads upstream, so forward_routed must retain the computed value under that name.
            upstream = await connect_upstream(
                # What: supply port to connect_upstream; why: forward_routed binds this port and lease value to connect_upstream's port input.
                port=lease.port,
                # What: supply base url to connect_upstream; why: forward_routed binds this proxy base url and lease value to connect_upstream's base url input.
                base_url=lease.proxy_base_url,
                # What: supply path and query to connect_upstream; why: forward_routed binds this path and query value to connect_upstream's path and query input.
                path_and_query=path_and_query,
                # What: supply headers to dict; why: forward_routed binds this dict and headers and request value to dict's headers input.
                headers=dict(request.headers),
                # What: supply body to connect_upstream; why: forward_routed binds this outbound body value to connect_upstream's body input.
                body=outbound_body,
                # What: supply method to connect_upstream; why: forward_routed binds this method and request value to connect_upstream's method input.
                method=request.method,
                # What: supply timeout s to connect_upstream; why: forward_routed binds this upstream timeout s and profile and router and lease value to connect_upstream's timeout s input.
                timeout_s=lease.profile.upstream_timeout_s or router.upstream_timeout_s,
            # What: complete the connect_upstream call with port and base url and path and query and headers and body; why: forward_routed groups the supplied clauses as one connect_upstream call before its value is consumed.
            )
        # What: handle cancelled error and asyncio by lease release; why: forward_routed converts that failure into this concrete recovery, response, or cleanup behavior.
        except asyncio.CancelledError:
            # What: call lease.release with the declared inputs; why: forward_routed invokes lease.release while performing with inflight lock; the call advances that operation through its result or side effect.
            lease.release()
            # What: enter the inflight lock managed context before request reservations pop request id; why: forward_routed releases this resource or lock after request reservations pop request id on both success and failure paths.
            with inflight_lock:
                # What: call request_reservations.pop with request id and the named fixture input; why: forward_routed invokes request_reservations.pop while performing router record cancellation; the call advances that operation through its result or side effect.
                request_reservations.pop(request_id, None)
            # What: call router.record_cancellation with the declared inputs; why: forward_routed invokes router.record_cancellation while performing router event request cancelled profile model route safe route; the call advances that operation through its result or side effect.
            router.record_cancellation()
            # What: preserve the exact router event request cancelled profile model route safe route literal fragment; why: forward_routed passes this fragment verbatim through router_event("request_cancelled", profile=model, route=safe_route), because changing it would alter a protocol payload, serialized fixture, or.
            router_event("request_cancelled", profile=model, route=safe_route)
            # What: re-propagate the active failure to the caller; why: forward_routed stops this rejected path before it can mutate state, dispatch work, or report success.
            raise
        # What: handle exception by lease release; why: forward_routed converts that failure into this concrete recovery, response, or cleanup behavior.
        except Exception as exc:  # the lease must not strand a pending swap on connect failure
            # What: call lease.release with the declared inputs; why: forward_routed invokes lease.release while performing with inflight lock; the call advances that operation through its result or side effect.
            lease.release()
            # What: enter the inflight lock managed context before request reservations pop request id; why: forward_routed releases this resource or lock after request reservations pop request id on both success and failure paths.
            with inflight_lock:
                # What: call request_reservations.pop with request id and the named fixture input; why: forward_routed invokes request_reservations.pop while performing router event upstream connect failed profile model route safe route; the call advances that operation through its result or side effect.
                request_reservations.pop(request_id, None)
            # What: preserve the exact router event upstream connect failed profile model route safe route literal fragment; why: forward_routed passes this fragment verbatim through router_event("upstream_connect_failed", profile=model, route=safe_route), because changing it would alter a protocol payload, serialized.
            router_event("upstream_connect_failed", profile=model, route=safe_route)
            # What: map the error field as str and exc and message and type and upstream unavailable; why: forward_routed carries error into return JSONResponse(status_code=502, content={"error": {"message": str(e.
            return JSONResponse(status_code=502, content={"error": {"message": str(exc), "type": "upstream_unavailable"}})
        # What: handle base exception by lease release; why: forward_routed converts that failure into this concrete recovery, response, or cleanup behavior.
        except BaseException:
            # What: call lease.release with the declared inputs; why: forward_routed invokes lease.release while performing with inflight lock; the call advances that operation through its result or side effect.
            lease.release()
            # What: enter the inflight lock managed context before request reservations pop request id; why: forward_routed releases this resource or lock after request reservations pop request id on both success and failure paths.
            with inflight_lock:
                # What: call request_reservations.pop with request id and the named fixture input; why: forward_routed invokes request_reservations.pop while performing raise; the call advances that operation through its result or side effect.
                request_reservations.pop(request_id, None)
            # What: re-propagate the active failure to the caller; why: forward_routed stops this rejected path before it can mutate state, dispatch work, or report success.
            raise
        # What: enter the inflight lock managed context before cancelled while connecting request reservations request id cancelled; why: forward_routed releases this resource or lock after cancelled while connecting request reservations request id cancelled on both success and failure paths.
        with inflight_lock:
            # What: compute cancelled while connecting from request reservations and request id and cancelled; why: if cancelled while connecting later reads cancelled while connecting, so forward_routed must retain the computed value under that name.
            cancelled_while_connecting = request_reservations[request_id]["cancelled"]
            # What: gate on cancelled while connecting before pop and request id and request reservations; why: forward_routed admits pop and request id and request reservations only for this predicate and excludes the opposite state.
            if cancelled_while_connecting:
                # What: call request_reservations.pop with request id and the named fixture input; why: forward_routed invokes request_reservations.pop while performing else; the call advances that operation through its result or side effect.
                request_reservations.pop(request_id, None)
            # What: select the remaining branch that performs inflight request id; why: forward_routed covers the state excluded by the preceding predicate without conflating the two outcomes.
            else:
                # What: compute inflight entry from name and upstream and profile and lease and profile; why: item inflight get request id later reads inflight entry, so forward_routed must retain the computed value under that name.
                inflight[request_id] = {
                    # What: map the profile field as name and profile and lease; why: forward_routed carries profile through inflight entry into item inflight get request id.
                    "profile": lease.profile.name,
                    # What: map the upstream field as upstream; why: forward_routed carries upstream through inflight entry into item inflight get request id.
                    "upstream": upstream,
                    # What: map the cancelled field as false; why: forward_routed carries cancelled through inflight entry into item inflight get request id.
                    "cancelled": False,
                # What: complete the inflight entry mapping with profile and upstream and cancelled; why: forward_routed groups the supplied clauses as one inflight entry mapping before its value is consumed.
                }
        # What: gate on cancelled while connecting before close and upstream; why: forward_routed admits close and upstream only for this predicate and excludes the opposite state.
        if cancelled_while_connecting:
            # What: call upstream.close with the declared inputs; why: forward_routed invokes upstream.close while performing lease release; the call advances that operation through its result or side effect.
            upstream.close()
            # What: call lease.release with the declared inputs; why: forward_routed invokes lease.release while performing return jsonresponse; the call advances that operation through its result or side effect.
            lease.release()
            # What: return jsonresponse and 409 and error and message and type from forward_routed; why: forward_routed exposes jsonresponse and 409 and error and message and type so its caller can continue with the function\'s computed outcome.
            return JSONResponse(
                # What: supply status code to JSONResponse; why: forward_routed binds this 409 value to JSONResponse's status code input.
                status_code=409,
                # What: map the error field as message and type and request and cancelled and while; why: forward_routed carries error into content={"error": {.
                content={"error": {
                    # What: apply the message request cancelled while opening upstream portion of the enclosing predicate; why: this clause remains in forward_routed\'s enclosing expression so its grouping and evaluation order stay intact.
                    "message": "request cancelled while opening upstream connection",
                    # What: apply the type request cancelled portion of the enclosing predicate; why: this clause remains in forward_routed\'s enclosing expression so its grouping and evaluation order stay intact.
                    "type": "request_cancelled",
                # What: complete the enclosing predicate mapping with error; why: forward_routed groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
                }},
            # What: complete the JSONResponse call with status code and content; why: forward_routed groups the supplied clauses as one JSONResponse call before its value is consumed.
            )
        # What: preserve the exact router event admitted lease event identity lease route safe route literal fragment; why: forward_routed passes this fragment verbatim through router_event("admitted", **lease_event_identity(lease), route=safe_route, because changing it would alter a protocol payload, serialized fixtu.
        router_event("admitted", **lease_event_identity(lease), route=safe_route)

        # What: define stream_response around the current object state; why: its direct callers call stream_response for stream response and rely on this exact input and result contract.
        def stream_response():
            # What: compute first byte at from the named fixture input; why: if first byte at is later reads first byte at, so stream_response must retain the computed value under that name.
            first_byte_at = None
            # What: compute byte count from 0; why: byte count len chunk later reads byte count, so stream_response must retain the computed value under that name.
            byte_count = 0
            # What: compute captured response from bytearray; why: if len captured response len chunk capture limit later reads captured response, so stream_response must retain the computed value under that name.
            captured_response = bytearray()
            # What: compute capture overflow from false; why: if capture limit and not capture overflow later reads capture overflow, so stream_response must retain the computed value under that name.
            capture_overflow = False
            # What: establish the handler boundary for the protected operation; why: stream_response routes failures to the unconditional cleanup block while preserving cleanup and success flow.
            try:
                # What: iterate across chunks and upstream to perform first byte at and monotonic and time; why: stream_response repeats the body only while or for the loop header admits an iteration.
                for chunk in upstream.chunks():
                    # What: gate on first byte at before first byte at and monotonic and time; why: stream_response admits first byte at and monotonic and time only for this predicate and excludes the opposite state.
                    if first_byte_at is None:
                        # What: compute first byte at from monotonic and time; why: ttft s first byte at started if first byte at is later reads first byte at, so stream_response must retain the computed value under that name.
                        first_byte_at = time.monotonic()
                    # What: compute byte count from len and chunk; why: response bytes byte count later reads byte count, so stream_response must retain the computed value under that name.
                    byte_count += len(chunk)
                    # What: gate on capture limit and capture overflow before capture limit and capture overflow and extend and chunk and clear; why: stream_response admits capture limit and capture overflow and extend and chunk and clear only for this predicate and excludes the opposite state.
                    if capture_limit and not capture_overflow:
                        # What: gate on capture limit and len and captured response and chunk before extend and chunk and captured response; why: stream_response admits extend and chunk and captured response only for this predicate and excludes the opposite state.
                        if len(captured_response) + len(chunk) <= capture_limit:
                            # What: call captured_response.extend with chunk; why: stream_response invokes captured_response.extend while performing else; the call advances that operation through its result or side effect.
                            captured_response.extend(chunk)
                        # What: select the remaining branch that performs capture overflow; why: stream_response covers the state excluded by the preceding predicate without conflating the two outcomes.
                        else:
                            # What: compute capture overflow from true; why: response body if capture overflow else bytes captured response later reads capture overflow, so stream_response must retain the computed value under that name.
                            capture_overflow = True
                            # What: call captured_response.clear with the declared inputs; why: stream_response invokes captured_response.clear while performing yield chunk; the call advances that operation through its result or side effect.
                            captured_response.clear()
                    # What: apply the yield chunk portion of the enclosing predicate; why: this clause remains in stream_response\'s enclosing expression so its grouping and evaluation order stay intact.
                    yield chunk
            # What: run ended time monotonic on every exit path; why: stream_response performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
            finally:
                # What: compute ended from monotonic and time; why: duration s ended started later reads ended, so stream_response must retain the computed value under that name.
                ended = time.monotonic()
                # What: enter the inflight lock managed context before item inflight get request id; why: stream_response releases this resource or lock after item inflight get request id on both success and failure paths.
                with inflight_lock:
                    # What: compute item from get and request id and inflight; why: cancelled bool item get cancelled later reads item, so stream_response must retain the computed value under that name.
                    item = inflight.get(request_id, {})
                    # What: compute cancelled from bool and get and item and cancelled; why: completed not cancelled later reads cancelled, so stream_response must retain the computed value under that name.
                    cancelled = bool(item.get("cancelled"))
                    # What: gate on upstream and get and item before pop and request id and inflight; why: stream_response admits pop and request id and inflight only for this predicate and excludes the opposite state.
                    if item.get("upstream") is upstream:
                        # What: call inflight.pop with request id and the named fixture input; why: stream_response invokes inflight.pop while performing request reservations pop request id; the call advances that operation through its result or side effect.
                        inflight.pop(request_id, None)
                    # What: call request_reservations.pop with request id and the named fixture input; why: stream_response invokes request_reservations.pop while performing ttft s first byte at started if first byte at is; the call advances that operation through its result or side effect.
                    request_reservations.pop(request_id, None)
                # What: compute ttft s from first byte at and started; why: ttft s ttft s later reads ttft s, so stream_response must retain the computed value under that name.
                ttft_s = (first_byte_at - started) if first_byte_at is not None else None
                # What: call router.record_stream with the declared inputs; why: stream_response invokes router.record_stream while performing ttft s ttft s; the call advances that operation through its result or side effect.
                router.record_stream(
                    # What: supply ttft s to router.record_stream; why: stream_response binds this ttft s value to router.record_stream's ttft s input.
                    ttft_s=ttft_s,
                    # What: supply duration s to router.record_stream; why: stream_response binds this ended and started value to router.record_stream's duration s input.
                    duration_s=ended - started,
                    # What: supply response bytes to router.record_stream; why: stream_response binds this byte count value to router.record_stream's response bytes input.
                    response_bytes=byte_count,
                    # What: supply completed to router.record_stream; why: stream_response binds this cancelled value to router.record_stream's completed input.
                    completed=not cancelled,
                # What: complete the router.record_stream call with ttft s and duration s and response bytes and completed; why: stream_response groups the supplied clauses as one router.record_stream call before its value is consumed.
                )
                # What: call lease.release with the declared inputs; why: stream_response invokes lease.release while performing router event; the call advances that operation through its result or side effect.
                lease.release()
                # What: call router_event with request finished; why: stream_response invokes router_event while performing request finished; the call advances that operation through its result or side effect.
                router_event(
                    # What: preserve the exact request finished literal fragment; why: stream_response passes this fragment verbatim through "request_finished", because changing it would alter a protocol payload, serialized fixture, or public message.
                    "request_finished",
                    # What: supply expanded arguments to lease_event_identity; why: stream_response binds this lease event identity and lease value to lease_event_identity's expanded input.
                    **lease_event_identity(lease),
                    # What: supply route to router_event; why: stream_response binds this safe route value to router_event's route input.
                    route=safe_route,
                    # What: supply status to router_event; why: stream_response binds this status and upstream value to router_event's status input.
                    status=upstream.status,
                    # What: supply cancelled to router_event; why: stream_response binds this cancelled value to router_event's cancelled input.
                    cancelled=cancelled,
                    # What: supply response bytes to router_event; why: stream_response binds this byte count value to router_event's response bytes input.
                    responseBytes=byte_count,
                # What: complete the router_event call with route and status and cancelled and response bytes; why: stream_response groups the supplied clauses as one router_event call before its value is consumed.
                )
                # What: call activity_store.record with the declared inputs; why: stream_response invokes activity_store.record while performing model lease profile name; the call advances that operation through its result or side effect.
                activity_store.record(
                    # What: supply model to activity_store.record; why: stream_response binds this name and profile and lease value to activity_store.record's model input.
                    model=lease.profile.name,
                    # What: supply route to activity_store.record; why: stream_response binds this safe route value to activity_store.record's route input.
                    route=safe_route,
                    # What: supply method to activity_store.record; why: stream_response binds this method and request value to activity_store.record's method input.
                    method=request.method,
                    # What: supply status to activity_store.record; why: stream_response binds this status and upstream value to activity_store.record's status input.
                    status=upstream.status,
                    # What: supply started to activity_store.record; why: stream_response binds this started value to activity_store.record's started input.
                    started=started,
                    # What: supply ttft s to activity_store.record; why: stream_response binds this ttft s value to activity_store.record's ttft s input.
                    ttft_s=ttft_s,
                    # What: supply response bytes to activity_store.record; why: stream_response binds this byte count value to activity_store.record's response bytes input.
                    response_bytes=byte_count,
                    # What: supply cancelled to activity_store.record; why: stream_response binds this cancelled value to activity_store.record's cancelled input.
                    cancelled=cancelled,
                    # What: supply request headers to activity_store.record; why: stream_response binds this headers and request value to activity_store.record's request headers input.
                    request_headers=request.headers,
                    # What: supply request body to activity_store.record; why: stream_response binds this outbound body value to activity_store.record's request body input.
                    request_body=outbound_body,
                    # What: supply response headers to activity_store.record; why: stream_response binds this headers and upstream value to activity_store.record's response headers input.
                    response_headers=upstream.headers,
                    # What: supply response body to bytes; why: stream_response binds this capture overflow and bytes and captured response value to bytes's response body input.
                    response_body=None if capture_overflow else bytes(captured_response),
                # What: complete the activity_store.record call with model and route and method and status and started; why: stream_response groups the supplied clauses as one activity_store.record call before its value is consumed.
                )

        # What: compute headers from response headers and headers and upstream; why: headers x ft request id request id later reads headers, so forward_routed must retain the computed value under that name.
        headers = response_headers(upstream.headers)
        # What: compute headers entry from request id; why: headers headers later reads headers entry, so forward_routed must retain the computed value under that name.
        headers["X-FT-Request-ID"] = request_id
        # What: return streaming response and stream response and status and headers from forward_routed; why: forward_routed exposes streaming response and stream response and status and headers so its caller can continue with the function\'s computed outcome.
        return StreamingResponse(
            # What: call stream_response with the declared inputs; why: forward_routed invokes stream_response while performing status code upstream status; the call advances that operation through its result or side effect.
            stream_response(),
            # What: supply status code to StreamingResponse; why: forward_routed binds this status and upstream value to StreamingResponse's status code input.
            status_code=upstream.status,
            # What: supply headers to StreamingResponse; why: forward_routed binds this headers value to StreamingResponse's headers input.
            headers=headers,
            # What: supply media type to upstream.headers.get; why: forward_routed binds this get and headers and upstream and content type value to upstream.headers.get's media type input.
            media_type=upstream.headers.get("Content-Type"),
        # What: complete the StreamingResponse call with status code and headers and media type; why: forward_routed groups the supplied clauses as one StreamingResponse call before its value is consumed.
        )

    # What: define route_inference around request; why: its direct callers call route_inference for route inference and rely on this exact input and result contract.
    async def route_inference(request: Request):
        # What: compute body from body and request; why: model request model body later reads body, so route_inference must retain the computed value under that name.
        body = await request.body()
        # What: establish the handler boundary for the protected operation; why: route_inference routes failures to request model error and catalog error while preserving cleanup and success flow.
        try:
            # What: compute model from request model and body; why: if not router has routable id model later reads model, so route_inference must retain the computed value under that name.
            model = request_model(body)
            # What: gate on has routable id and model and router before catalog error and model; why: route_inference admits catalog error and model only for this predicate and excludes the opposite state.
            if not router.has_routable_id(model):
                # What: raise CatalogError for the caller; why: route_inference stops this rejected path before it can mutate state, dispatch work, or report success.
                raise CatalogError(f"unknown model profile {model!r}")
        # What: handle request model error by raise httpexception status code 400 detail str exc; why: route_inference converts that failure into this concrete recovery, response, or cleanup behavior.
        except RequestModelError as exc:
            # What: raise HTTPException for the caller; why: route_inference stops this rejected path before it can mutate state, dispatch work, or report success.
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        # What: handle catalog error by return jsonresponse; why: route_inference converts that failure into this concrete recovery, response, or cleanup behavior.
        except CatalogError as exc:
            # What: return jsonresponse and str and exc and 404 and error from route_inference; why: route_inference exposes jsonresponse and str and exc and 404 and error so its caller can continue with the function\'s computed outcome.
            return JSONResponse(
                # What: supply status code to JSONResponse; why: route_inference binds this 404 value to JSONResponse's status code input.
                status_code=404,
                # What: map the error field as str and exc and message and type and unknown model; why: route_inference carries error into content={"error": {"message": str(exc), "type": "unknown_model"}}.
                content={"error": {"message": str(exc), "type": "unknown_model"}},
            # What: complete the JSONResponse call with status code and content; why: route_inference groups the supplied clauses as one JSONResponse call before its value is consumed.
            )
        # What: compute suffix from query and url and request and value and value; why: path and query request url path suffix later reads suffix, so route_inference must retain the computed value under that name.
        suffix = f"?{request.url.query}" if request.url.query else ""
        # What: return forward routed and request and model and body from route_inference; why: route_inference exposes forward routed and request and model and body so its caller can continue with the function\'s computed outcome.
        return await forward_routed(
            # What: apply the request portion of the enclosing predicate; why: this clause remains in route_inference\'s enclosing expression so its grouping and evaluation order stay intact.
            request,
            # What: apply the model portion of the enclosing predicate; why: this clause remains in route_inference\'s enclosing expression so its grouping and evaluation order stay intact.
            model,
            # What: supply path and query to forward_routed; why: route_inference binds this path and suffix and url and request value to forward_routed's path and query input.
            path_and_query=request.url.path + suffix,
            # What: supply body to forward_routed; why: route_inference binds this body value to forward_routed's body input.
            body=body,
            # What: supply apply request filters to forward_routed; why: route_inference binds this true value to forward_routed's apply request filters input.
            apply_request_filters=True,
        # What: complete the forward_routed call with path and query and body and apply request filters; why: route_inference groups the supplied clauses as one forward_routed call before its value is consumed.
        )

    # FreeToken's supported inference surface. All routes use the same native
    # admission and proxy path so an OpenAI or Anthropic client cannot bypass
    # lifecycle, accounting, readiness, or cancellation ownership.
    # What: register POST /v1/chat/completions on the application router; why: clients reach inference_proxy's handler only through this method-and-path binding.
    @app.post("/v1/chat/completions", dependencies=[Depends(require_router_key)])
    # What: register POST /v1/completions on the application router; why: clients reach inference_proxy's handler only through this method-and-path binding.
    @app.post("/v1/completions", dependencies=[Depends(require_router_key)])
    # What: register POST /v1/responses on the application router; why: clients reach inference_proxy's handler only through this method-and-path binding.
    @app.post("/v1/responses", dependencies=[Depends(require_router_key)])
    # What: register POST /v1/messages on the application router; why: clients reach inference_proxy's handler only through this method-and-path binding.
    @app.post("/v1/messages", dependencies=[Depends(require_router_key)])
    # What: register POST /v1/messages/count_tokens on the application router; why: clients reach inference_proxy's handler only through this method-and-path binding.
    @app.post("/v1/messages/count_tokens", dependencies=[Depends(require_router_key)])
    # What: define inference_proxy around request; why: the registered API client call inference_proxy for inference proxy and rely on this exact input and result contract.
    async def inference_proxy(request: Request):
        # What: return route inference and request from inference_proxy; why: inference_proxy exposes route inference and request so its caller can continue with the function\'s computed outcome.
        return await route_inference(request)

    # FreeToken's Responses implementation is deliberately stateless. Keep its
    # registered resource routes available at the stable daemon URL, but do not
    # activate an arbitrary model for a request that carries no model identity.
    # The envelope matches the engine contract and remains behind inference auth.
    # What: register GET /v1/responses/{response_id} on the application router; why: clients reach stateless_response_not_found's handler only through this method-and-path binding.
    @app.get("/v1/responses/{response_id}", dependencies=[Depends(require_router_key)])
    # What: register POST the configured path on the application router; why: clients reach stateless_response_not_found's handler only through this method-and-path binding.
    @app.post(
        # What: apply the v1 responses response id cancel portion of the enclosing predicate; why: this clause remains in stateless_response_not_found\'s enclosing expression so its grouping and evaluation order stay intact.
        "/v1/responses/{response_id}/cancel",
        # What: supply dependencies to Depends; why: stateless_response_not_found binds this depends and require router key value to Depends's dependencies input.
        dependencies=[Depends(require_router_key)],
    # What: complete the app.post call with dependencies; why: stateless_response_not_found groups the supplied clauses as one app.post call before its value is consumed.
    )
    # What: define stateless_response_not_found around response id; why: the registered API client call stateless_response_not_found for stateless response not found and rely on this exact input and result contract.
    async def stateless_response_not_found(response_id: str):
        # What: return jsonresponse and response id and 404 and error and message from stateless_response_not_found; why: stateless_response_not_found exposes jsonresponse and response id and 404 and error and message so its caller can continue with the function\'s computed outcome.
        return JSONResponse(
            # What: supply status code to JSONResponse; why: stateless_response_not_found binds this 404 value to JSONResponse's status code input.
            status_code=404,
            # What: supply content to JSONResponse; why: stateless_response_not_found binds this response id and error and message and type and code value to JSONResponse's content input.
            content={
                # What: apply the error portion of the enclosing predicate; why: this clause remains in stateless_response_not_found\'s enclosing expression so its grouping and evaluation order stay intact.
                "error": {
                    # What: map the message field as response id and response and not and found and stateless; why: stateless_response_not_found carries message into "message": f"response {response_id!r} not found (stateless server)".
                    "message": f"response {response_id!r} not found (stateless server)",
                    # What: map the type field as invalid request error; why: stateless_response_not_found carries type into "type": "invalid_request_error".
                    "type": "invalid_request_error",
                    # What: map the code field as the fixture input; why: stateless_response_not_found carries code into "code": None.
                    "code": None,
                # What: complete the enclosing predicate mapping with message and type and code; why: stateless_response_not_found groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
                }
            # What: complete the enclosing predicate mapping with error; why: stateless_response_not_found groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
            },
        # What: complete the JSONResponse call with status code and content; why: stateless_response_not_found groups the supplied clauses as one JSONResponse call before its value is consumed.
        )

    # What: register GET /models on the application router; why: clients reach openai_model_list's handler only through this method-and-path binding.
    @app.get("/models", dependencies=[Depends(require_router_key)])
    # What: register GET /v1/models on the application router; why: clients reach openai_model_list's handler only through this method-and-path binding.
    @app.get("/v1/models", dependencies=[Depends(require_router_key)])
    # What: define openai_model_list around request; why: the registered API client call openai_model_list for openai model list and rely on this exact input and result contract.
    async def openai_model_list(request: Request):
        """OpenAI-compatible public metadata without exposing local model paths."""
        # What: document open ai compatible public metadata without exposing local in the openai_model_list docstring; why: introspection and maintainers read this exact docstring fragment to understand openai model list behavior without executing it.
        # What: evaluate and capture catalog snapshot loaded profiles active routing profile; why: the enclosing qualifier uses the captured result in its next validation or artifact step.
        catalog_snapshot, loaded_profiles, active_routing_profile = (
            # What: call router.public_model_listing_snapshot with the declared inputs; why: openai_model_list consumes the router.public_model_listing_snapshot return value while evaluating router.public_model_listing_snapshot().
            router.public_model_listing_snapshot()
        # What: execute the grouped source fragment; why:  the enclosing symbol requires this operation for its concrete qualification or routing path.
        )
        # What: compute created from int and time; why: created created later reads created, so openai_model_list must retain the computed value under that name.
        created = int(time.time())
        # What: initialize data as an empty runtime accumulator; why: openai_model_list appends or maps entries into it during data append record before consuming the aggregate.
        data = []
        # What: iterate across listed model ids and catalog snapshot to perform selector and model id and catalog snapshot; why: openai_model_list repeats the body only while or for the loop header admits an iteration.
        for model_id in catalog_snapshot.listed_model_ids():
            # What: compute selector from selector and model id and catalog snapshot; why: profile if selector is not else later reads selector, so openai_model_list must retain the computed value under that name.
            selector = catalog_snapshot.selector(model_id)
            # What: compute profile from selector and get and model id and catalog snapshot; why: loaded profile name in loaded profiles later reads profile, so openai_model_list must retain the computed value under that name.
            profile = None if selector is not None else catalog_snapshot.get(model_id)
            # What: gate on selector before loaded and name and loaded profiles and profile; why: openai_model_list admits loaded and name and loaded profiles and profile only for this predicate and excludes the opposite state.
            if selector is None:
                # What: compute loaded from name and loaded profiles and profile; why: loaded any later reads loaded, so openai_model_list must retain the computed value under that name.
                loaded = profile.name in loaded_profiles
            # What: select the remaining branch that performs targets selector targets if selector strategy pin else; why: openai_model_list covers the state excluded by the preceding predicate without conflating the two outcomes.
            else:
                # What: compute targets from targets and strategy and selector and pin and 1; why: catalog snapshot get target name in loaded profiles for later reads targets, so openai_model_list must retain the computed value under that name.
                targets = selector.targets[:1] if selector.strategy == "pin" else selector.targets
                # What: compute loaded from any and name and loaded profiles and target; why: value loaded if loaded else unloaded later reads loaded, so openai_model_list must retain the computed value under that name.
                loaded = any(
                    # What: call catalog_snapshot.get with target; why: openai_model_list consumes the catalog_snapshot.get return value while evaluating catalog_snapshot.get(target).name in loaded_profiles for target in targe.
                    catalog_snapshot.get(target).name in loaded_profiles for target in targets
                # What: complete the any call with name; why: openai_model_list groups the supplied clauses as one any call before its value is consumed.
                )
            # What: compute record from model id and created and loaded and id and object; why: record name selector display name later reads record, so openai_model_list must retain the computed value under that name.
            record = {
                # What: map the id field as model id; why: openai_model_list carries id through record into record name selector display name.
                "id": model_id,
                # What: map the object field as model; why: openai_model_list carries object through record into record name selector display name.
                "object": "model",
                # What: map the created field as created; why: openai_model_list carries created through record into record name selector display name.
                "created": created,
                # What: map the owned by field as freetoken; why: openai_model_list carries owned by through record into record name selector display name.
                "owned_by": "freetoken",
                # What: apply the status portion of record; why: openai_model_list uses this clause to evaluate record as one grouped value.
                "status": {
                    # What: map the value field as loaded and loaded and unloaded; why: openai_model_list carries value through record into record name selector display name.
                    "value": "loaded" if loaded else "unloaded"
                # What: complete the record mapping with value; why: openai_model_list groups the supplied clauses as one record mapping before its value is consumed.
                },
            # What: complete the record mapping with id and object and created and owned by and status; why: openai_model_list groups the supplied clauses as one record mapping before its value is consumed.
            }
            # What: gate on selector before display name and selector and record; why: openai_model_list admits display name and selector and record only for this predicate and excludes the opposite state.
            if selector is not None:
                # What: gate on display name and selector before display name and record and selector; why: openai_model_list admits display name and record and selector only for this predicate and excludes the opposite state.
                if selector.display_name:
                    # What: compute record entry from display name and selector; why: record description selector description later reads record entry, so openai_model_list must retain the computed value under that name.
                    record["name"] = selector.display_name
                # What: gate on description and selector before description and record and selector; why: openai_model_list admits description and record and selector only for this predicate and excludes the opposite state.
                if selector.description:
                    # What: compute record entry from description and selector; why: record meta freetoken selector metadata later reads record entry, so openai_model_list must retain the computed value under that name.
                    record["description"] = selector.description
                # What: compute selector metadata from metadata and selector; why: selector metadata update later reads selector metadata, so openai_model_list must retain the computed value under that name.
                selector_metadata = selector.metadata()
                # What: call selector_metadata.update with strategy and selector and list and targets and type; why: openai_model_list invokes selector_metadata.update while performing type selector; the call advances that operation through its result or side effect.
                selector_metadata.update({
                    # What: map the type field as selector; why: openai_model_list carries type into "type": "selector".
                    "type": "selector",
                    # What: map the strategy field as strategy and selector; why: openai_model_list carries strategy into "strategy": selector.strategy.
                    "strategy": selector.strategy,
                    # What: map the targets field as list and targets and selector; why: openai_model_list carries targets into "targets": list(selector.targets).
                    "targets": list(selector.targets),
                # What: complete the selector_metadata.update call with strategy; why: openai_model_list groups the supplied clauses as one selector_metadata.update call before its value is consumed.
                })
                # What: map the freetoken field as selector metadata; why: openai_model_list carries freetoken through record entry into record name profile display name strip.
                record["meta"] = {"freetoken": selector_metadata}
            # What: gate on profile before display name and profile and record and strip; why: openai_model_list admits display name and profile and record and strip only for this predicate and excludes the opposite state.
            if profile is not None:
                # What: gate on display name and profile before record and strip and display name and profile; why: openai_model_list admits record and strip and display name and profile only for this predicate and excludes the opposite state.
                if profile.display_name:
                    # What: compute record entry from strip and display name and profile; why: record description profile description strip later reads record entry, so openai_model_list must retain the computed value under that name.
                    record["name"] = profile.display_name.strip()
                # What: gate on description and profile before record and strip and description and profile; why: openai_model_list admits record and strip and description and profile only for this predicate and excludes the opposite state.
                if profile.description:
                    # What: compute record entry from strip and description and profile; why: record update capability fields later reads record entry, so openai_model_list must retain the computed value under that name.
                    record["description"] = profile.description.strip()
                # What: compute capability fields from model listing fields and capabilities and profile; why: record update capability fields later reads capability fields, so openai_model_list must retain the computed value under that name.
                capability_fields = profile.capabilities.model_listing_fields()
                # What: call record.update with capability fields; why: openai_model_list invokes record.update while performing metadata profile metadata; the call advances that operation through its result or side effect.
                record.update(capability_fields)
                # What: compute metadata from metadata and profile; why: metadata pop key later reads metadata, so openai_model_list must retain the computed value under that name.
                metadata = profile.metadata()
                # What: gate on empty and capabilities and profile before key and pop and metadata; why: openai_model_list admits key and pop and metadata only for this predicate and excludes the opposite state.
                if not profile.capabilities.empty():
                    # What: iterate across the computed value to perform pop and key and metadata; why: openai_model_list repeats the body only while or for the loop header admits an iteration.
                    for key in (
                        # What: apply the architecture capabilities supported parameters portion of the enclosing predicate; why: this clause remains in openai_model_list\'s enclosing expression so its grouping and evaluation order stay intact.
                        "architecture", "capabilities", "supported_parameters",
                        # What: apply the context length context window portion of the enclosing predicate; why: this clause remains in openai_model_list\'s enclosing expression so its grouping and evaluation order stay intact.
                        "context_length", "context_window",
                    # What: complete the enclosing predicate collection with architecture and capabilities and supported parameters and context length; why: openai_model_list groups the supplied clauses as one enclosing predicate collection collection before its value is consumed.
                    ):
                        # What: call metadata.pop with key and the named fixture input; why: openai_model_list invokes metadata.pop while performing if model id profile name; the call advances that operation through its result or side effect.
                        metadata.pop(key, None)
                # What: gate on model id and name and profile before internal metadata; why: openai_model_list admits internal metadata only for this predicate and excludes the opposite state.
                if model_id == profile.name:
                    # What: map the type field as model; why: openai_model_list carries type through internal metadata into internal metadata aliases list profile aliases.
                    internal_metadata = {"type": "model"}
                    # What: gate on aliases and profile before internal metadata and list and aliases and profile; why: openai_model_list admits internal metadata and list and aliases and profile only for this predicate and excludes the opposite state.
                    if profile.aliases:
                        # What: compute internal metadata entry from list and aliases and profile; why: internal metadata type alias model id profile name later reads internal metadata entry, so openai_model_list must retain the computed value under that name.
                        internal_metadata["aliases"] = list(profile.aliases)
                # What: select the remaining branch that performs internal metadata type alias model id profile name; why: openai_model_list covers the state excluded by the preceding predicate without conflating the two outcomes.
                else:
                    # What: map the type field as alias; why: openai_model_list carries type through internal metadata into metadata update internal metadata.
                    internal_metadata = {"type": "alias", "modelID": profile.name}
                # What: call metadata.update with internal metadata; why: openai_model_list invokes metadata.update while performing record setdefault meta freetoken metadata; the call advances that operation through its result or side effect.
                metadata.update(internal_metadata)
                # What: compute result entry from metadata; why: the enclosing return or state update later reads result entry, so openai_model_list must retain the computed value under that name.
                record.setdefault("meta", {})["freetoken"] = metadata
            # What: call data.append with record; why: openai_model_list invokes data.append while performing routing profile; the call advances that operation through its result or side effect.
            data.append(record)
        # What: compute routing profile from active routing profile and routing profile and catalog snapshot; why: catalog snapshot routing profile active routing profile later reads routing profile, so openai_model_list must retain the computed value under that name.
        routing_profile = (
            # What: call catalog_snapshot.routing_profile with active routing profile; why: openai_model_list invokes catalog_snapshot.routing_profile while performing if active routing profile is not else; the call advances that operation through its result or side effect.
            catalog_snapshot.routing_profile(active_routing_profile)
            # What: apply the if active routing profile is not else portion of routing profile; why: openai_model_list uses this clause to evaluate routing profile as one grouped value.
            if active_routing_profile is not None else None
        # What: complete the routing_profile expression with routing profile catalog snapshot routing profile active routing profile if active routing profile is not else; why: openai_model_list groups the supplied clauses as one routing_profile expression before its value is consumed.
        )
        # What: gate on routing profile before pins and pin and target and routing profile and append; why: openai_model_list admits pins and pin and target and routing profile and append only for this predicate and excludes the opposite state.
        if routing_profile is not None:
            # What: iterate across pins and routing profile to perform target and has routable id and pin and catalog snapshot; why: openai_model_list repeats the body only while or for the loop header admits an iteration.
            for pin, target in routing_profile.pins:
                # What: gate on target and has routable id and pin and catalog snapshot before the computed value; why: openai_model_list admits the computed value only for this predicate and excludes the opposite state.
                if target is None or catalog_snapshot.has_routable_id(pin):
                    # What: apply the continue portion of the enclosing predicate; why: this clause remains in openai_model_list\'s enclosing expression so its grouping and evaluation order stay intact.
                    continue
                # What: call data.append with pin and created and id and object and created; why: openai_model_list invokes data.append while performing id pin; the call advances that operation through its result or side effect.
                data.append({
                    # What: map the id field as pin; why: openai_model_list carries id into "id": pin.
                    "id": pin,
                    # What: map the object field as model; why: openai_model_list carries object into "object": "model".
                    "object": "model",
                    # What: map the created field as created; why: openai_model_list carries created into "created": created.
                    "created": created,
                    # What: map the owned by field as freetoken; why: openai_model_list carries owned by into "owned_by": "freetoken".
                    "owned_by": "freetoken",
                    # What: map the value field as unloaded; why: openai_model_list carries value into "status": {"value": "unloaded"}.
                    "status": {"value": "unloaded"},
                    # What: map the freetoken field as type and profile; why: openai_model_list carries freetoken into "meta": {"freetoken": {"type": "profile"}}.
                    "meta": {"freetoken": {"type": "profile"}},
                # What: complete the data.append call with pin; why: openai_model_list groups the supplied clauses as one data.append call before its value is consumed.
                })
        # What: compute response from jsonresponse and data and object and data and list; why: response headers access control allow origin origin later reads response, so openai_model_list must retain the computed value under that name.
        response = JSONResponse(content={
            # What: map the object field as list; why: openai_model_list carries object through response into response headers access control allow origin origin.
            "object": "list",
            # What: map the data field as data; why: openai_model_list carries data through response into response headers access control allow origin origin.
            "data": data,
        # What: complete the JSONResponse call with content; why: openai_model_list groups the supplied clauses as one JSONResponse call before its value is consumed.
        })
        # What: gate on origin and get and headers and request before origin and headers and response; why: openai_model_list admits origin and headers and response only for this predicate and excludes the opposite state.
        if origin := request.headers.get("origin"):
            # What: compute headers entry from origin; why: the enclosing return or state update later reads headers entry, so openai_model_list must retain the computed value under that name.
            response.headers["Access-Control-Allow-Origin"] = origin
        # What: return response from openai_model_list; why: openai_model_list exposes response so its caller can continue with the function\'s computed outcome.
        return response

    # What: apply app.api_route behavior to upstream_proxy; why: Python attaches this named decorator's registration or descriptor semantics to upstream_proxy.
    @app.api_route(
        # What: apply the upstream upstream path path portion of the enclosing predicate; why: this clause remains in upstream_proxy\'s enclosing expression so its grouping and evaluation order stay intact.
        "/upstream/{upstream_path:path}",
        # What: supply methods to app.api_route; why: upstream_proxy binds this get and post and put and patch and delete value to app.api_route's methods input.
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        # What: supply dependencies to Depends; why: upstream_proxy binds this depends and require router key value to Depends's dependencies input.
        dependencies=[Depends(require_router_key)],
    # What: complete the app.api_route call with methods and dependencies; why: upstream_proxy groups the supplied clauses as one app.api_route call before its value is consumed.
    )
    # What: define upstream_proxy around request and upstream path; why: the registered API client call upstream_proxy for upstream proxy and rely on this exact input and result contract.
    async def upstream_proxy(request: Request, upstream_path: str):
        # What: establish the handler boundary for the protected operation; why: upstream_proxy routes failures to catalog error while preserving cleanup and success flow.
        try:
            # What: compute source model and model and and remaining path from resolve upstream path and upstream path and ro; why: upstream_proxy consumes source model and model and and remaining path during escaped path suffix raw path f upstream source model, so source model and model and and remaining path value r.
            source_model, model, _, remaining_path = router.resolve_upstream_path(
                # What: apply the upstream path portion of source model and model and and remaining path; why: upstream_proxy uses this clause to evaluate source model and model and and remaining path as one grouped value.
                upstream_path
            # What: complete the router.resolve_upstream_path call with upstream path; why: upstream_proxy groups the supplied clauses as one router.resolve_upstream_path call before its value is consumed.
            )
        # What: handle catalog error by return jsonresponse; why: upstream_proxy converts that failure into this concrete recovery, response, or cleanup behavior.
        except CatalogError as exc:
            # What: return jsonresponse and str and exc and 404 and error from upstream_proxy; why: upstream_proxy exposes jsonresponse and str and exc and 404 and error so its caller can continue with the function\'s computed outcome.
            return JSONResponse(
                # What: supply status code to JSONResponse; why: upstream_proxy binds this 404 value to JSONResponse's status code input.
                status_code=404,
                # What: map the error field as str and exc and message and type and unknown model; why: upstream_proxy carries error into content={"error": {"message": str(exc), "type": "unknown_model"}}.
                content={"error": {"message": str(exc), "type": "unknown_model"}},
            # What: complete the JSONResponse call with status code and content; why: upstream_proxy groups the supplied clauses as one JSONResponse call before its value is consumed.
            )
        # The daemon alone may call prepare-stop. Exposing it through an
        # arbitrary passthrough would bypass durable accounting and leave a
        # misleading routing lease behind.
        # What: compute normalized from lstrip and remaining path and value; why: if normalized v1 admin prepare stop later reads normalized, so upstream_proxy must retain the computed value under that name.
        normalized = remaining_path.lstrip("/")
        # What: gate on normalized before httpexception; why: upstream_proxy admits httpexception only for this predicate and excludes the opposite state.
        if normalized == "v1/admin/prepare-stop":
            # What: raise HTTPException for the caller; why:  upstream_proxy stops this rejected path before it can mutate state, dispatch work, or report success.
            raise HTTPException(status_code=403, detail="upstream prepare-stop is daemon-managed")
        # What: gate on any and profile is resident and model and endswith and suffix before jsonresponse and model; why: upstream_proxy admits jsonresponse and model only for this predicate and excludes the opposite state.
        if (
            # What: call any with endswith and suffix and upstream no activation suffixes and remaining path; why: upstream_proxy invokes any while performing remaining path endswith suffix; the call advances that operation through its result or side effect.
            any(
                # What: call remaining_path.endswith with suffix; why: upstream_proxy invokes remaining_path.endswith while performing for suffix in router catalog settings upstream no activation suffixes; the call advances that operation through its result or side effect.
                remaining_path.endswith(suffix)
                # What: apply the for suffix in router catalog settings upstream no activation suffixes portion of the enclosing predicate; why: this clause remains in upstream_proxy\'s enclosing expression so its grouping and evaluation order stay intact.
                for suffix in router.catalog.settings.upstream_no_activation_suffixes
            # What: complete the any call with endswith; why: upstream_proxy groups the supplied clauses as one any call before its value is consumed.
            )
            # What: call router.profile_is_resident with model; why: upstream_proxy consumes the router.profile_is_resident return value while evaluating and not router.profile_is_resident(model).
            and not router.profile_is_resident(model)
        # What: complete the enclosing predicate with if any remaining path endswith suffix for suffix in router catalog settings upstream no activation suffixes and; why: upstream_proxy groups the supplied clauses as one enclosing predicate expression before its value is consumed.
        ):
            return JSONResponse(
                status_code=409,
                content={
                    # What: apply the error portion of the enclosing predicate; why: this clause remains in upstream_proxy\'s enclosing expression so its grouping and evaluation order stay intact.
                    "error": {
                        # What: map the message field as model and model and is and not and loaded; why: upstream_proxy carries message into "message": (.
                        "message": (
                            # What: embed the exact f model model r is not router-interface fragment; why: the router UI consumer receives this fragment verbatim through f"model {model!r} is not loaded; path matches ", preserving browser markup, style, or script behavior.
                            # What: preserve the exact router upstream no activation suffixes literal fragment; why: upstream_proxy passes this fragment verbatim through f"model {model!r} is not loaded; path matches ", because changing it would alter a protocol payload, serialized fixture, or public message.
                            f"model {model!r} is not loaded; path matches "
                            "router.upstream_no_activation_suffixes"
                        # What: complete the enclosing predicate mapping with message and type; why:  upstream_proxy groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
                        ),
                        # What: map the type field as model not loaded; why: upstream_proxy carries type into "type": "model_not_loaded".
                        "type": "model_not_loaded",
                    # What: complete the enclosing predicate mapping with message and type; why:  upstream_proxy groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
                    }
                },
            )
        # What: compute raw path from get and scope and request and raw path; why: escaped path suffix raw path f upstream source model later reads raw path, so upstream_proxy must retain the computed value under that name.
        raw_path = request.scope.get("raw_path")
        # What: compute escaped path from isinstance and raw path and bytes and escaped path suffix; why: if escaped path is later reads escaped path, so upstream_proxy must retain the computed value under that name.
        escaped_path = (
            # What: call _escaped_path_suffix with raw path and source model and upstream; why: upstream_proxy invokes _escaped_path_suffix while performing if isinstance raw path bytes else; the call advances that operation through its result or side effect.
            _escaped_path_suffix(raw_path, f"/upstream/{source_model}")
            # What: call isinstance with raw path and bytes; why: upstream_proxy consumes the isinstance return value while evaluating if isinstance(raw_path, bytes) else None.
            if isinstance(raw_path, bytes) else None
        # What: complete the escaped_path expression with escaped path escaped path suffix raw path f upstream source model if isinstance raw path; why: upstream_proxy groups the supplied clauses as one escaped_path expression before its value is consumed.
        )
        # What: gate on escaped path before httpexception; why: upstream_proxy admits httpexception only for this predicate and excludes the opposite state.
        if escaped_path is None:
            # What: raise HTTPException for the caller; why:  upstream_proxy stops this rejected path before it can mutate state, dispatch work, or report success.
            raise HTTPException(status_code=400, detail="invalid escaped upstream path")
        # What: gate on escaped path before escaped path; why: upstream_proxy admits escaped path only for this predicate and excludes the opposite state.
        if not escaped_path:
            # What: compute escaped path from value; why: path and query escaped path suffix later reads escaped path, so upstream_proxy must retain the computed value under that name.
            escaped_path = "/"
        # What: compute raw query from get and scope and request and query string; why: suffix f raw query decode ascii if raw query later reads raw query, so upstream_proxy must retain the computed value under that name.
        raw_query = request.scope.get("query_string", b"")
        # What: compute suffix from raw query and decode and value and value and ascii; why: path and query escaped path suffix later reads suffix, so upstream_proxy must retain the computed value under that name.
        suffix = f"?{raw_query.decode('ascii')}" if raw_query else ""
        # What: return forward routed and request and model and escaped path from upstream_proxy; why: upstream_proxy exposes forward routed and request and model and escaped path so its caller can continue with the function\'s computed outcome.
        return await forward_routed(
            # What: apply the request portion of the enclosing predicate; why: this clause remains in upstream_proxy\'s enclosing expression so its grouping and evaluation order stay intact.
            request,
            # What: apply the model portion of the enclosing predicate; why: this clause remains in upstream_proxy\'s enclosing expression so its grouping and evaluation order stay intact.
            model,
            # What: supply path and query to forward_routed; why: upstream_proxy binds this escaped path and suffix value to forward_routed's path and query input.
            path_and_query=escaped_path + suffix,
            # What: supply body to request.body; why: upstream_proxy binds this body and request value to request.body's body input.
            body=await request.body(),
            # What: supply apply request filters to operation.lower; why: upstream_proxy binds this lower and get and headers and request and application value to operation.lower's apply request filters input.
            apply_request_filters="application/json" in request.headers.get(
                # What: apply the content type portion of the enclosing predicate; why: this clause remains in upstream_proxy\'s enclosing expression so its grouping and evaluation order stay intact.
                "content-type", ""
            # What: apply the lower portion of the enclosing predicate; why: this clause remains in upstream_proxy\'s enclosing expression so its grouping and evaluation order stay intact.
            ).lower(),
        # What: complete the forward_routed call with path and query and body and apply request filters; why: upstream_proxy groups the supplied clauses as one forward_routed call before its value is consumed.
        )

    # What: register GET /router/status on the application router; why: clients reach router_status's handler only through this method-and-path binding.
    @app.get("/router/status", dependencies=auth)
    # What: define router_status around the current object state; why: the registered API client call router_status for router status and rely on this exact input and result contract.
    async def router_status():
        # What: map the catalog watch field as catalog watch snapshot; why: router_status carries catalog watch into return {**router.status(), "catalogWatch": catalog_watch_snapshot()}.
        return {**router.status(), "catalogWatch": catalog_watch_snapshot()}

    # What: register GET /router/models on the application router; why: clients reach router_models's handler only through this method-and-path binding.
    @app.get("/router/models", dependencies=auth)
    # What: define router_models around the current object state; why: the registered API client call router_models for router models and rely on this exact input and result contract.
    async def router_models():
        """Configured profiles annotated with the sole engine's live residency."""
        # What: document configured profiles annotated with the sole in the router_models docstring; why: introspection and maintainers read this exact docstring fragment to understand router models behavior without executing it.
        # What: compute catalog snapshot and route state from control plane snapshot and router; why: for profile in catalog snapshot public later reads catalog snapshot and route state, so router_models must retain the computed value under that name.
        catalog_snapshot, route_state = router.control_plane_snapshot()
        # What: compute engine from status and manager; why: profile name active and bool engine get later reads engine, so router_models must retain the computed value under that name.
        engine = manager.status()
        # What: compute active from route state and active profile; why: profile name active and bool engine get later reads active, so router_models must retain the computed value under that name.
        active = route_state["activeProfile"]
        # What: compute active identity matches from route state and active identity matches engine; why: profile name active and bool engine get later reads active identity matches, so router_models must retain the computed value under that name.
        active_identity_matches = route_state["activeIdentityMatchesEngine"]
        # What: initialize data as an empty runtime accumulator; why: router_models appends or maps entries into it during data append profile before consuming the aggregate.
        data = []
        # What: iterate across public and catalog snapshot to perform profile and dict; why: router_models repeats the body only while or for the loop header admits an iteration.
        for profile in catalog_snapshot.public():
            # What: compute profile from dict and profile; why: profile configured later reads profile, so router_models must retain the computed value under that name.
            profile = dict(profile)
            # What: compute profile entry from true; why: profile resident later reads profile entry, so router_models must retain the computed value under that name.
            profile["configured"] = True
            # What: compute profile entry from active identity matches and active and bool and profile; why: profile name active and bool engine get later reads profile entry, so router_models must retain the computed value under that name.
            profile["resident"] = (
                # What: call bool with get and engine and running; why: router_models consumes the bool return value while evaluating profile["name"] == active and bool(engine.get("running")) and active_ide.
                profile["name"] == active and bool(engine.get("running")) and active_identity_matches
            # What: complete the profile entry expression with profile resident profile name equals active and bool engine get; why: router_models groups the supplied clauses as one profile entry expression before its value is consumed.
            )
            # What: compute profile entry from profile and route state and 0 and resident and active requests; why: data append profile later reads profile entry, so router_models must retain the computed value under that name.
            profile["activeRequests"] = route_state["activeRequests"] if profile["resident"] else 0
            # What: call data.append with profile; why: router_models invokes data.append while performing return; the call advances that operation through its result or side effect.
            data.append(profile)
        # What: return data and public selectors and public routing profiles and route state from router_models; why: router_models exposes data and public selectors and public routing profiles and route state so its caller can continue with the function\'s computed outcome.
        return {
            # What: map the data field as data; why: router_models carries data into "data": data.
            "data": data,
            # What: map the selectors field as public selectors and catalog snapshot; why: router_models carries selectors into "selectors": catalog_snapshot.public_selectors().
            "selectors": catalog_snapshot.public_selectors(),
            # What: map the routing profiles field as public routing profiles and catalog snapshot; why: router_models carries routing profiles into "routingProfiles": catalog_snapshot.public_routing_profiles().
            "routingProfiles": catalog_snapshot.public_routing_profiles(),
            # What: map the active routing profile field as route state and active routing profile; why: router_models carries active routing profile into "activeRoutingProfile": route_state["activeRoutingProfile"].
            "activeRoutingProfile": route_state["activeRoutingProfile"],
            # What: map the capacity field as route state and capacity; why: router_models carries capacity into "capacity": route_state["capacity"].
            "capacity": route_state["capacity"],
        # What: complete the enclosing predicate mapping with data and selectors and routing profiles and active routing profile and capacity; why: router_models groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
        }

    # What: register GET /router/profiles on the application router; why: clients reach router_profiles's handler only through this method-and-path binding.
    @app.get("/router/profiles", dependencies=auth)
    # What: define router_profiles around the current object state; why: the registered API client call router_profiles for router profiles and rely on this exact input and result contract.
    async def router_profiles():
        # What: compute catalog snapshot and route state from control plane snapshot and router; why: data catalog snapshot public later reads catalog snapshot and route state, so router_profiles must retain the computed value under that name.
        catalog_snapshot, route_state = router.control_plane_snapshot()
        # What: return public and public selectors and public routing profiles and route state from router_profiles; why: router_profiles exposes public and public selectors and public routing profiles and route state so its caller can continue with the function\'s computed outcome.
        return {
            # What: map the data field as public and catalog snapshot; why: router_profiles carries data into "data": catalog_snapshot.public().
            "data": catalog_snapshot.public(),
            # What: map the selectors field as public selectors and catalog snapshot; why: router_profiles carries selectors into "selectors": catalog_snapshot.public_selectors().
            "selectors": catalog_snapshot.public_selectors(),
            # What: map the routing profiles field as public routing profiles and catalog snapshot; why: router_profiles carries routing profiles into "routingProfiles": catalog_snapshot.public_routing_profiles().
            "routingProfiles": catalog_snapshot.public_routing_profiles(),
            # What: map the active routing profile field as route state and active routing profile; why: router_profiles carries active routing profile into "activeRoutingProfile": route_state["activeRoutingProfile"].
            "activeRoutingProfile": route_state["activeRoutingProfile"],
            # What: map the active profile field as route state and active profile; why: router_profiles carries active profile into "activeProfile": route_state["activeProfile"].
            "activeProfile": route_state["activeProfile"],
        # What: complete the enclosing predicate mapping with data and selectors and routing profiles and active routing profile and active profile; why: router_profiles groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
        }

    # What: register PUT /router/profiles/active on the application router; why: clients reach set_active_routing_profile's handler only through this method-and-path binding.
    @app.put("/router/profiles/active", dependencies=auth)
    # What: define set_active_routing_profile around body; why: the registered API client call set_active_routing_profile for set active routing profile and rely on this exact input and result contract.
    async def set_active_routing_profile(body: RoutingProfileSelectionBody):
        # What: establish the handler boundary for the protected operation; why: set_active_routing_profile routes failures to routing error while preserving cleanup and success flow.
        try:
            # What: compute active from set active routing profile and name and router and body; why: router event routing profile changed routing profile active later reads active, so set_active_routing_profile must retain the computed value under that name.
            active = router.set_active_routing_profile(body.name)
        # What: handle routing error by return jsonresponse; why: set_active_routing_profile converts that failure into this concrete recovery, response, or cleanup behavior.
        except RoutingError as exc:
            # What: return jsonresponse and status code and exc and code from set_active_routing_profile; why: set_active_routing_profile exposes jsonresponse and status code and exc and code so its caller can continue with the function\'s computed outcome.
            return JSONResponse(
                # What: supply status code to JSONResponse; why: set_active_routing_profile binds this status code and exc value to JSONResponse's status code input.
                status_code=exc.status_code,
                # What: map the error field as code and str and exc and message and type; why: set_active_routing_profile carries error into content={"error": {"message": str(exc), "type": exc.code}}.
                content={"error": {"message": str(exc), "type": exc.code}},
            # What: complete the JSONResponse call with status code and content; why: set_active_routing_profile groups the supplied clauses as one JSONResponse call before its value is consumed.
            )
        # What: preserve the exact router event routing profile changed routing profile active literal fragment; why: set_active_routing_profile passes this fragment verbatim through router_event("routing_profile_changed", routingProfile=active), because changing it would alter a protocol payload, serialized fixture.
        router_event("routing_profile_changed", routingProfile=active)
        # What: map the active field as active; why: set_active_routing_profile carries active into return {"active": active}.
        return {"active": active}

    # What: register GET /router/hardware on the application router; why: clients reach router_hardware's handler only through this method-and-path binding.
    @app.get("/router/hardware", dependencies=auth)
    # What: define router_hardware around the current object state; why: the registered API client call router_hardware for router hardware and rely on this exact input and result contract.
    async def router_hardware():
        """Small, privacy-preserving local memory view for the management UI."""
        # What: document small privacy preserving local memory view for in the router_hardware docstring; why: introspection and maintainers read this exact docstring fragment to understand router hardware behavior without executing it.
        # What: compute engine from status and manager; why: footprint await run proxy pool footprint fn engine get later reads engine, so router_hardware must retain the computed value under that name.
        engine = manager.status()
        # What: compute footprint from run and proxy pool and footprint fn and get; why: memory footprint later reads footprint, so router_hardware must retain the computed value under that name.
        footprint = await run(proxy_pool, footprint_fn, engine.get("pid"))
        # What: return footprint and bool and get and engine and engine from router_hardware; why: router_hardware exposes footprint and bool and get and engine and engine so its caller can continue with the function\'s computed outcome.
        return {
            # What: apply the engine portion of the enclosing predicate; why: this clause remains in router_hardware\'s enclosing expression so its grouping and evaluation order stay intact.
            "engine": {
                # What: map the running field as bool and get and engine and running; why: router_hardware carries running into "running": bool(engine.get("running")).
                "running": bool(engine.get("running")),
                # What: map the pid field as get and engine and pid; why: router_hardware carries pid into "pid": engine.get("pid").
                "pid": engine.get("pid"),
                # What: map the port field as get and engine and port; why: router_hardware carries port into "port": engine.get("port").
                "port": engine.get("port"),
            # What: complete the enclosing predicate mapping with running and pid and port; why: router_hardware groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
            },
            # What: map the memory field as footprint; why: router_hardware carries memory into "memory": footprint.
            "memory": footprint,
        # What: complete the enclosing predicate mapping with engine and memory; why: router_hardware groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
        }

    # What: register GET /api/performance on the application router; why: clients reach router_performance's handler only through this method-and-path binding.
    @app.get("/api/performance", dependencies=auth)
    # What: register GET /router/performance on the application router; why: clients reach router_performance's handler only through this method-and-path binding.
    @app.get("/router/performance", dependencies=auth)
    # What: define router_performance around after; why: the registered API client call router_performance for router performance and rely on this exact input and result contract.
    async def router_performance(after: str | None = Query(default=None)):
        # What: compute parsed after from the named fixture input; why: parsed after datetime fromisoformat after replace z later reads parsed after, so router_performance must retain the computed value under that name.
        parsed_after = None
        # What: gate on after before fullmatch and after and httpexception and re; why: router_performance admits fullmatch and after and httpexception and re only for this predicate and excludes the opposite state.
        if after is not None:
            # What: gate on fullmatch and after and re before httpexception; why: router_performance admits httpexception only for this predicate and excludes the opposite state.
            if not re.fullmatch(
                # What: apply the r d d d t d portion of the enclosing predicate; why: this clause remains in router_performance\'s enclosing expression so its grouping and evaluation order stay intact.
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})",
                # What: apply the after portion of the enclosing predicate; why: this clause remains in router_performance\'s enclosing expression so its grouping and evaluation order stay intact.
                after,
            # What: complete the re.fullmatch call with after; why: router_performance groups the supplied clauses as one re.fullmatch call before its value is consumed.
            ):
                # What: raise HTTPException for the caller; why: router_performance stops this rejected path before it can mutate state, dispatch work, or report success.
                raise HTTPException(
                    # What: supply status code to HTTPException; why: router_performance binds this 400 value to HTTPException's status code input.
                    status_code=400, detail="invalid 'after' timestamp, use RFC3339 format"
                # What: complete the HTTPException call with status code and detail; why: router_performance groups the supplied clauses as one HTTPException call before its value is consumed.
                )
            # What: establish the handler boundary for the protected operation; why: router_performance routes failures to value error while preserving cleanup and success flow.
            try:
                # What: compute parsed after from fromisoformat and datetime and replace and after and z; why: result performance monitor current after parsed after later reads parsed after, so router_performance must retain the computed value under that name.
                parsed_after = datetime.fromisoformat(after.replace("Z", "+00:00"))
            # What: handle value error by raise httpexception; why: router_performance converts that failure into this concrete recovery, response, or cleanup behavior.
            except ValueError as exc:
                # What: raise HTTPException for the caller; why: router_performance stops this rejected path before it can mutate state, dispatch work, or report success.
                raise HTTPException(
                    # What: supply status code to HTTPException; why: router_performance binds this 400 value to HTTPException's status code input.
                    status_code=400, detail="invalid 'after' timestamp, use RFC3339 format"
                # What: apply the from exc portion of the enclosing predicate; why: this clause remains in router_performance\'s enclosing expression so its grouping and evaluation order stay intact.
                ) from exc
        # What: compute result from current and performance monitor and parsed after; why: if not result enabled later reads result, so router_performance must retain the computed value under that name.
        result = performance_monitor.current(after=parsed_after)
        # What: gate on result before jsonresponse; why: router_performance admits jsonresponse only for this predicate and excludes the opposite state.
        if not result["enabled"]:
            # What: map the enabled field as false; why: router_performance carries enabled into return JSONResponse(status_code=503, content={"enabled": False}).
            return JSONResponse(status_code=503, content={"enabled": False})
        # What: return result from router_performance; why: router_performance exposes result so its caller can continue with the function\'s computed outcome.
        return result

    # What: register GET /router/requests on the application router; why: clients reach router_requests's handler only through this method-and-path binding.
    @app.get("/router/requests", dependencies=auth)
    # What: define router_requests around the current object state; why: the registered API client call router_requests for router requests and rely on this exact input and result contract.
    async def router_requests():
        # What: enter the inflight lock managed context before data id request id profile item profile; why: router_requests releases this resource or lock after data id request id profile item profile on both success and failure paths.
        with inflight_lock:
            # What: map the id field as request id; why: router_requests carries id through data into return data data.
            data = [{"id": request_id, "profile": item["profile"]}
                    # What: call request_reservations.items with the declared inputs; why: router_requests invokes request_reservations.items while performing return data data; the call advances that operation through its result or side effect.
                    for request_id, item in request_reservations.items()]
        # What: map the data field as data; why: router_requests carries data into return {"data": data}.
        return {"data": data}

    # What: register POST /router/requests/{request_id}/cancel on the application router; why: clients reach router_cancel's handler only through this method-and-path binding.
    @app.post("/router/requests/{request_id}/cancel", dependencies=auth)
    # What: define router_cancel around request id; why: the registered API client call router_cancel for router cancel and rely on this exact input and result contract.
    async def router_cancel(request_id: str):
        # What: enter the inflight lock managed context before item inflight get request id; why: router_cancel releases this resource or lock after item inflight get request id on both success and failure paths.
        with inflight_lock:
            # What: compute item from get and request id and inflight; why: if item is not and cancellation later reads item, so router_cancel must retain the computed value under that name.
            item = inflight.get(request_id)
            # What: compute reservation from get and request id and request reservations; why: if reservation is not and not later reads reservation, so router_cancel must retain the computed value under that name.
            reservation = request_reservations.get(request_id)
            # What: gate on reservation before reservation; why: router_cancel admits reservation only for this predicate and excludes the opposite state.
            if reservation is not None and not reservation["cancelled"]:
                # What: compute reservation entry from true; why: cancellation reservation cancellation later reads reservation entry, so router_cancel must retain the computed value under that name.
                reservation["cancelled"] = True
                # What: compute cancellation from reservation and cancellation; why: cancellation later reads cancellation, so router_cancel must retain the computed value under that name.
                cancellation = reservation["cancellation"]
            # What: select the remaining branch that performs cancellation; why: router_cancel covers the state excluded by the preceding predicate without conflating the two outcomes.
            else:
                # What: compute cancellation from the named fixture input; why: if item is not and cancellation later reads cancellation, so router_cancel must retain the computed value under that name.
                cancellation = None
            # What: gate on item and cancellation before item; why: router_cancel admits item only for this predicate and excludes the opposite state.
            if item is not None and cancellation is not None:
                # What: compute item entry from true; why: if item is later reads item entry, so router_cancel must retain the computed value under that name.
                item["cancelled"] = True
        # What: gate on cancellation before the computed value; why: router_cancel admits the computed value only for this predicate and excludes the opposite state.
        if cancellation is None:
            # What: map the cancelled field as false; why: router_cancel carries cancelled into return {"cancelled": False, "reason": "not_found"}.
            return {"cancelled": False, "reason": "not_found"}
        # What: gate on item before cancel acquire and cancellation and router; why: router_cancel admits cancel acquire and cancellation and router only for this predicate and excludes the opposite state.
        if item is None:
            # What: call router.cancel_acquire with cancellation; why: router_cancel invokes router.cancel_acquire while performing profile reservation profile; the call advances that operation through its result or side effect.
            router.cancel_acquire(cancellation)
            # What: compute profile from reservation and profile; why: profile item profile later reads profile, so router_cancel must retain the computed value under that name.
            profile = reservation["profile"]
        # What: select the remaining branch that performs item upstream close; why: router_cancel covers the state excluded by the preceding predicate without conflating the two outcomes.
        else:
            # What: preserve the exact item upstream close literal fragment; why: router_cancel passes this fragment verbatim through item["upstream"].close(), because changing it would alter a protocol payload, serialized fixture, or public message.
            item["upstream"].close()
            # What: compute profile from item and profile; why: router event request cancelled profile profile later reads profile, so router_cancel must retain the computed value under that name.
            profile = item["profile"]
        # What: call router.record_cancellation with the declared inputs; why: router_cancel invokes router.record_cancellation while performing router event request cancelled profile profile; the call advances that operation through its result or side effect.
        router.record_cancellation()
        # What: preserve the exact router event request cancelled profile profile literal fragment; why: router_cancel passes this fragment verbatim through router_event("request_cancelled", profile=profile), because changing it would alter a protocol payload, serialized fixture, or public message.
        router_event("request_cancelled", profile=profile)
        # What: map the cancelled field as true; why: router_cancel carries cancelled into return {"cancelled": True, "id": request_id}.
        return {"cancelled": True, "id": request_id}

    # What: register GET /router/logs on the application router; why: clients reach router_logs's handler only through this method-and-path binding.
    @app.get("/router/logs", dependencies=auth)
    # What: define router_logs around request and since; why: the registered API client call router_logs for router logs and rely on this exact input and result contract.
    async def router_logs(request: Request, since: int = 0):
        """Bounded lifecycle/proxy event stream, separate from engine stdout."""
        # What: document bounded lifecycle proxy event stream separate in the router_logs docstring; why: introspection and maintainers read this exact docstring fragment to understand router logs behavior without executing it.
        # What: return log stream and request and router ring and since from router_logs; why: router_logs exposes log stream and request and router ring and since so its caller can continue with the function\'s computed outcome.
        return _log_stream(request, router_ring, since)

    # What: register GET /router/activity on the application router; why: clients reach router_activity's handler only through this method-and-path binding.
    @app.get("/router/activity", dependencies=auth)
    # What: define router_activity around limit and before id and model; why: the registered API client call router_activity for router activity and rely on this exact input and result contract.
    async def router_activity(
        # What: declare the limit input for router_activity; why: router_activity consumes limit during return activity store list limit limit before id before id, so callers must bind it with the other signature inputs.
        limit: int = Query(default=100, ge=1, le=999),
        # What: declare the before id input for router_activity; why: router_activity consumes before id during return activity store list limit limit before id before id, so callers must bind it with the other signature inputs.
        before_id: int | None = Query(default=None, ge=1, alias="beforeId"),
        # What: declare the model input for router_activity; why: router_activity consumes model during return activity store list limit limit before id before id, so callers must bind it with the other signature inputs.
        model: str | None = None,
    # What: complete the enclosing predicate with app get router activity dependencies auth async def router activity limit; why: router_activity groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: return list and activity store and limit and before id from router_activity; why: router_activity exposes list and activity store and limit and before id so its caller can continue with the function\'s computed outcome.
        return activity_store.list(limit=limit, before_id=before_id, model=model)

    # What: register GET /router/activity/stats on the application router; why: clients reach router_activity_stats's handler only through this method-and-path binding.
    @app.get("/router/activity/stats", dependencies=auth)
    # What: define router_activity_stats around model; why: the registered API client call router_activity_stats for router activity stats and rely on this exact input and result contract.
    async def router_activity_stats(model: str | None = None):
        # What: return stats and activity store and model from router_activity_stats; why: router_activity_stats exposes stats and activity store and model so its caller can continue with the function\'s computed outcome.
        return activity_store.stats(model=model)

    # What: register GET /router/captures/{capture_id} on the application router; why: clients reach router_capture's handler only through this method-and-path binding.
    @app.get("/router/captures/{capture_id}", dependencies=auth)
    # What: define router_capture around capture id; why: the registered API client call router_capture for router capture and rely on this exact input and result contract.
    async def router_capture(capture_id: int):
        # What: compute capture from capture and capture id and activity store; why: if capture is later reads capture, so router_capture must retain the computed value under that name.
        capture = activity_store.capture(capture_id)
        # What: gate on capture before httpexception; why: router_capture admits httpexception only for this predicate and excludes the opposite state.
        if capture is None:
            # What: raise HTTPException for the caller; why: router_capture stops this rejected path before it can mutate state, dispatch work, or report success.
            raise HTTPException(status_code=404, detail="capture not found")
        # What: return capture from router_capture; why: router_capture exposes capture so its caller can continue with the function\'s computed outcome.
        return capture

    # What: register GET /metrics on the application router; why: clients reach router_metrics's handler only through this method-and-path binding.
    @app.get("/metrics", dependencies=auth)
    # What: define router_metrics around the current object state; why: the registered API client call router_metrics for router metrics and rely on this exact input and result contract.
    async def router_metrics():
        # What: return plain text response and prometheus and router and text and plain from router_metrics; why: router_metrics exposes plain text response and prometheus and router and text and plain so its caller can continue with the function\'s computed outcome.
        return PlainTextResponse(router.prometheus(), media_type="text/plain; version=0.0.4")

    # What: register POST /router/unload on the application router; why: clients reach router_unload's handler only through this method-and-path binding.
    @app.post("/router/unload", dependencies=auth)
    # What: define router_unload around body; why: the registered API client call router_unload for router unload and rely on this exact input and result contract.
    async def router_unload(body: RouterUnloadBody | None = None):
        try:
            # What: compute unloaded from run and lifecycle pool and evict idle and router; why: return unloaded unloaded router router status later reads unloaded, so router_unload must retain the computed value under that name.
            unloaded = await run(lifecycle_pool, router.evict_idle, body.name if body else None)
        except (AccountingPrepareError, AccountingOutboxError) as exc:
            return accounting_error(exc)
        # What: map the unloaded field as unloaded; why: router_unload carries unloaded into return {"unloaded": unloaded, "router": router.status()}.
        return {"unloaded": unloaded, "router": router.status()}

    # What: register POST /router/load on the application router; why: clients reach router_load's handler only through this method-and-path binding.
    @app.post("/router/load", dependencies=auth)
    # What: define router_load around body; why: the registered API client call router_load for router load and rely on this exact input and result contract.
    async def router_load(body: RouterLoadBody):
        """Activate one profile without inventing a synthetic inference request.

        The short lease still uses the identical admission, readiness, switch,
        accounting, and rollback transaction as automatic routing. Releasing it
        afterwards permits the configured idle-TTL policy to apply normally.
        """
        # What: document activate one profile without inventing a in the router_load docstring; why: introspection and maintainers read this exact docstring fragment to understand router load behavior without executing it.
        # What: document the short lease still uses the in the router_load docstring; why: introspection and maintainers read this exact docstring fragment to understand router load behavior without executing it.
        # What: document accounting and rollback transaction as automatic in the router_load docstring; why: introspection and maintainers read this exact docstring fragment to understand router load behavior without executing it.
        # What: document afterwards permits the configured idle ttl policy in the router_load docstring; why: introspection and maintainers read this exact docstring fragment to understand router load behavior without executing it.
        # What: preserve the paragraph boundary in the the router_load docstring; why: introspection and maintainers read this paragraph break to understand router load behavior without executing it.
        # What: establish the handler boundary for the protected operation; why: router_load routes failures to routing error while preserving cleanup and success flow.
        try:
            # What: compute lease from acquire route and name and body and false; why: result profile lease profile name port lease port pid later reads lease, so router_load must retain the computed value under that name.
            lease = await acquire_route(body.name, apply_routing_profile=False)
        # What: handle routing error by router event management load failed profile body name code exc code; why: router_load converts that failure into this concrete recovery, response, or cleanup behavior.
        except RoutingError as exc:
            # What: preserve the exact router event management load failed profile body name code exc code literal fragment; why: router_load passes this fragment verbatim through router_event("management_load_failed", profile=body.name, code=exc.code), because changing it would alter a protocol payload, serialized fi.
            router_event("management_load_failed", profile=body.name, code=exc.code)
            # What: map the error field as code and str and exc and message and type; why: router_load carries error through content into content recovery exc recovery.
            content = {"error": {"message": str(exc), "type": exc.code}}
            # What: gate on recovery and exc before recovery and content and exc; why: router_load admits recovery and content and exc only for this predicate and excludes the opposite state.
            if exc.recovery is not None:
                # What: compute content entry from recovery and exc; why: content content later reads content entry, so router_load must retain the computed value under that name.
                content["recovery"] = exc.recovery
            # What: return jsonresponse and status code and content and exc and 429 from router_load; why: router_load exposes jsonresponse and status code and content and exc and 429 so its caller can continue with the function\'s computed outcome.
            return JSONResponse(
                # What: supply status code to JSONResponse; why: router_load binds this status code and exc value to JSONResponse's status code input.
                status_code=exc.status_code,
                # What: supply content to JSONResponse; why: router_load binds this content value to JSONResponse's content input.
                content=content,
                # What: map the retry after field as 1; why: router_load carries retry after into headers={"Retry-After": "1"} if exc.status_code == 429 else None.
                headers={"Retry-After": "1"} if exc.status_code == 429 else None,
            # What: complete the JSONResponse call with status code and content and headers; why: router_load groups the supplied clauses as one JSONResponse call before its value is consumed.
            )
        # What: establish the handler boundary for the protected operation; why: router_load routes failures to the unconditional cleanup block while preserving cleanup and success flow.
        try:
            # What: map the profile field as name and profile and lease; why: router_load carries profile through result into return result router router status.
            result = {"profile": lease.profile.name, "port": lease.port, "pid": lease.pid}
        # What: run lease release on every exit path; why: router_load performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
        finally:
            # What: call lease.release with the declared inputs; why: router_load invokes lease.release while performing router event management loaded profile lease profile name; the call advances that operation through its result or side effect.
            lease.release()
        # What: preserve the exact router event management loaded profile lease profile name literal fragment; why: router_load passes this fragment verbatim through router_event("management_loaded", profile=lease.profile.name), because changing it would alter a protocol payload, serialized fixture, or public message.
        router_event("management_loaded", profile=lease.profile.name)
        # What: map the router field as status and router; why: router_load carries router into return {**result, "router": router.status()}.
        return {**result, "router": router.status()}

    # What: register POST /router/reload on the application router; why: clients reach router_reload's handler only through this method-and-path binding.
    @app.post("/router/reload", dependencies=auth)
    # What: define router_reload around the current object state; why: the registered API client call router_reload for router reload and rely on this exact input and result contract.
    async def router_reload():
        # What: gate on catalog path before httpexception; why: router_reload admits httpexception only for this predicate and excludes the opposite state.
        if not catalog_path:
            # What: raise HTTPException for the caller; why:  router_reload stops this rejected path before it can mutate state, dispatch work, or report success.
            raise HTTPException(status_code=409, detail="catalog reload requires --catalog")
        # What: establish the handler boundary for the protected operation; why: router_reload routes failures to catalog error and routing error while preserving cleanup and success flow.
        try:
            # What: compute replacement from run and proxy pool and load and catalog path; why: await run lifecycle pool router replace catalog replacement later reads replacement, so router_reload must retain the computed value under that name.
            replacement = await run(proxy_pool, ModelCatalog.load, catalog_path)
            # What: call run with lifecycle pool and replace catalog and router and replacement; why: router_reload invokes run while performing await run; the call advances that operation through its result or side effect.
            await run(lifecycle_pool, router.replace_catalog, replacement)
            # What: call run with proxy pool and reconfigure and activity store and activity max entries and settings and replacement; why: router_reload invokes run while performing proxy pool; the call advances that operation through its result or side effect.
            await run(
                # What: apply the proxy pool portion of the enclosing predicate; why: this clause remains in router_reload\'s enclosing expression so its grouping and evaluation order stay intact.
                proxy_pool,
                # What: apply the activity store reconfigure portion of the enclosing predicate; why: this clause remains in router_reload\'s enclosing expression so its grouping and evaluation order stay intact.
                activity_store.reconfigure,
                # What: apply the replacement settings activity max entries portion of the enclosing predicate; why: this clause remains in router_reload\'s enclosing expression so its grouping and evaluation order stay intact.
                replacement.settings.activity_max_entries,
                # What: apply the replacement settings capture buffer mb portion of the enclosing predicate; why: this clause remains in router_reload\'s enclosing expression so its grouping and evaluation order stay intact.
                replacement.settings.capture_buffer_mb * 1024 * 1024,
                # What: apply the replacement settings activity session headers portion of the enclosing predicate; why: this clause remains in router_reload\'s enclosing expression so its grouping and evaluation order stay intact.
                replacement.settings.activity_session_headers,
            # What: complete the run call with proxy pool and reconfigure and activity max entries and capture buffer mb and activity session headers; why: router_reload groups the supplied clauses as one run call before its value is consumed.
            )
            # What: call run with proxy pool and reconfigure and performance monitor and performance every s and settings and replacement; why: router_reload invokes run while performing proxy pool; the call advances that operation through its result or side effect.
            await run(
                # What: apply the proxy pool portion of the enclosing predicate; why: this clause remains in router_reload\'s enclosing expression so its grouping and evaluation order stay intact.
                proxy_pool,
                # What: apply the performance monitor reconfigure portion of the enclosing predicate; why: this clause remains in router_reload\'s enclosing expression so its grouping and evaluation order stay intact.
                performance_monitor.reconfigure,
                # What: apply the replacement settings performance every s portion of the enclosing predicate; why: this clause remains in router_reload\'s enclosing expression so its grouping and evaluation order stay intact.
                replacement.settings.performance_every_s,
                # What: apply the replacement settings performance disabled portion of the enclosing predicate; why: this clause remains in router_reload\'s enclosing expression so its grouping and evaluation order stay intact.
                replacement.settings.performance_disabled,
            # What: complete the run call with proxy pool and reconfigure and performance every s and performance disabled; why: router_reload groups the supplied clauses as one run call before its value is consumed.
            )
        # What: handle catalog error by raise httpexception status code 400 detail str exc; why: router_reload converts that failure into this concrete recovery, response, or cleanup behavior.
        except CatalogError as exc:
            # What: raise HTTPException for the caller; why:  router_reload stops this rejected path before it can mutate state, dispatch work, or report success.
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        # What: handle routing error by return jsonresponse; why: router_reload converts that failure into this concrete recovery, response, or cleanup behavior.
        except RoutingError as exc:
            # What: return jsonresponse and status code and exc and code from router_reload; why: router_reload exposes jsonresponse and status code and exc and code so its caller can continue with the function\'s computed outcome.
            return JSONResponse(
                # What: supply status code to JSONResponse; why: router_reload binds this status code and exc value to JSONResponse's status code input.
                status_code=exc.status_code,
                # What: map the error field as code and str and exc and message and type; why: router_reload carries error into content={"error": {"message": str(exc), "type": exc.code}}.
                content={"error": {"message": str(exc), "type": exc.code}},
            # What: complete the JSONResponse call with status code and content; why: router_reload groups the supplied clauses as one JSONResponse call before its value is consumed.
            )
        # What: preserve the exact record watch reloaded literal fragment; why: router_reload passes this fragment verbatim through record_watch("reloaded"), because changing it would alter a protocol payload, serialized fixture, or public message.
        record_watch("reloaded")
        # What: map the reloaded field as true; why: router_reload carries reloaded into return {"reloaded": True, "models": router.catalog.public()}.
        return {"reloaded": True, "models": router.catalog.public()}

    # ---- engine lifecycle ----

    # What: define profile_request around name; why: its direct callers call profile_request for profile request and rely on this exact input and result contract.
    def profile_request(name: str) -> tuple[str, int, list[str]]:
        # What: compute profile from get and name and catalog and router; why: return profile model resolve port profile port list profile args later reads profile, so profile_request must retain the computed value under that name.
        profile = router.catalog.get(name)
        # What: return model and profile and resolve port and port from profile_request; why: profile_request exposes model and profile and resolve port and port so its caller can continue with the function\'s computed outcome.
        return profile.model, resolve_port(profile.port), list(profile.args)

    # What: define profile_result around name and result and port; why: its direct callers call profile_result for profile result and rely on this exact input and result contract.
    def profile_result(name: str, result: dict, port: int):
        # What: compute profile from get and name and catalog and router; why: timeout s profile ready timeout s later reads profile, so profile_result must retain the computed value under that name.
        profile = router.catalog.get(name)
        # What: compute readiness from wait for ready and manager and probe and port; why: content result profile name readiness readiness later reads readiness, so profile_result must retain the computed value under that name.
        readiness = wait_for_ready(
            # What: apply the manager portion of readiness; why: profile_result uses this clause to evaluate readiness as one grouped value.
            manager,
            # What: apply the probe portion of readiness; why: profile_result uses this clause to evaluate readiness as one grouped value.
            probe,
            # What: supply pid to result.get; why: profile_result binds this get and result and pid value to result.get's pid input.
            pid=result.get("pid"),
            # What: supply port to wait_for_ready; why: profile_result binds this port value to wait_for_ready's port input.
            port=port,
            # What: supply timeout s to wait_for_ready; why: profile_result binds this ready timeout s and profile value to wait_for_ready's timeout s input.
            timeout_s=profile.ready_timeout_s,
            # What: supply path to wait_for_ready; why: profile_result binds this check endpoint and profile value to wait_for_ready's path input.
            path=profile.check_endpoint,
        # What: complete the wait_for_ready call with pid and port and timeout s and path; why: profile_result groups the supplied clauses as one wait_for_ready call before its value is consumed.
        )

        # What: map the profile field as name; why: profile_result carries profile through content into return jsonresponse status code 503 content content.
        content = {**result, "profile": name, "readiness": readiness}
        # What: gate on readiness before jsonresponse and content; why: profile_result admits jsonresponse and content only for this predicate and excludes the opposite state.
        if not readiness["ready"]:
            # What: return jsonresponse and content and 503 from profile_result; why: profile_result exposes jsonresponse and content and 503 so its caller can continue with the function\'s computed outcome.
            return JSONResponse(status_code=503, content=content)
        # What: return content from profile_result; why: profile_result exposes content so its caller can continue with the function\'s computed outcome.
        return content

    # What: apply app.exception_handler behavior to switch_launch_error; why: Python attaches this named decorator's registration or descriptor semantics to switch_launch_error.
    @app.exception_handler(SwitchLaunchError)
    # What: define switch_launch_error around request and exc; why: the registered API client call switch_launch_error for switch launch error and rely on this exact input and result contract.
    async def switch_launch_error(request: Request, exc: SwitchLaunchError):
        # What: return jsonresponse and rollback and accounting and str from switch_launch_error; why: switch_launch_error exposes jsonresponse and rollback and accounting and str so its caller can continue with the function\'s computed outcome.
        return JSONResponse(status_code=503, content={
            # What: map the code field as switch launch failed; why: switch_launch_error carries code into "code": "switch_launch_failed", "error": str(exc).
            "code": "switch_launch_failed", "error": str(exc),
            # What: map the rollback field as rollback and exc; why: switch_launch_error carries rollback into "rollback": exc.rollback, "accounting": exc.accounting.
            "rollback": exc.rollback, "accounting": exc.accounting,
        # What: complete the JSONResponse call with status code and content; why: switch_launch_error groups the supplied clauses as one JSONResponse call before its value is consumed.
        })

    # What: register POST /engine/start on the application router; why: clients reach engine_start's handler only through this method-and-path binding.
    @app.post("/engine/start", dependencies=auth)
    # What: define engine_start around body; why: the registered API client call engine_start for engine start and rely on this exact input and result contract.
    async def engine_start(body: StartBody):
        # What: define operation around the current object state; why:  its direct callers call operation for operation and rely on this exact input and result contract.
        async def operation():
            # What: establish the handler boundary for the protected operation; why: operation routes failures to conflict and exception while preserving cleanup and success flow.
            try:
                # What: compute port from resolve port and port and body; why: return await run lifecycle pool manager start body model later reads port, so operation must retain the computed value under that name.
                port = resolve_port(body.port)
                # What: return run and lifecycle pool and start and model from operation; why: operation exposes run and lifecycle pool and start and model so its caller can continue with the function\'s computed outcome.
                return await run(lifecycle_pool, manager.start, body.model, port, list(body.args))
            # What: handle conflict by st manager status; why:  operation converts that failure into this concrete recovery, response, or cleanup behavior.
            except Conflict as exc:
                # What: compute st from status and manager; why: current model st get model later reads st, so  operation must retain the computed value under that name.
                st = manager.status()
                # What: return jsonresponse and str and exc and get from operation; why: operation exposes jsonresponse and str and exc and get so its caller can continue with the function\'s computed outcome.
                return JSONResponse(
                    # What: supply status code to JSONResponse; why:  operation binds this 409 value to JSONResponse's status code input.
                    status_code=409,
                    # What: supply content to JSONResponse; why:  operation binds this str and exc and get and st and error value to JSONResponse's content input.
                    content={
                        # What: map the error field as str and exc; why:  operation carries error into "error": str(exc).
                        "error": str(exc),
                        # What: map the code field as serve conflict; why:  operation carries code into "code": "serve_conflict".
                        "code": "serve_conflict",
                        # What: map the current model field as get and st and model; why:  operation carries current model into "currentModel": st.get("model").
                        "currentModel": st.get("model"),
                        # What: map the current port field as get and st and port; why:  operation carries current port into "currentPort": st.get("port").
                        "currentPort": st.get("port"),
                    # What: execute the grouped source fragment; why:  the enclosing symbol requires this operation for its concrete qualification or routing path.
                    },
                # What: complete the JSONResponse call with status code and content; why:  operation groups the supplied clauses as one JSONResponse call before its value is consumed.
                )
            # What: handle exception by raise httpexception status code 500 detail f start; why: operation converts that failure into this concrete recovery, response, or cleanup behavior.
            except Exception as exc:  # noqa: BLE001 — never propagate a 500-as-crash
                # What: raise HTTPException for the caller; why:  operation stops this rejected path before it can mutate state, dispatch work, or report success.
                raise HTTPException(status_code=500, detail=f"start failed: {exc}")

        # What: return run manual transaction and operation from engine_start; why: engine_start exposes run manual transaction and operation so its caller can continue with the function\'s computed outcome.
        return await run_manual_transaction(operation)

    # What: register POST /engine/stop on the application router; why: clients reach engine_stop's handler only through this method-and-path binding.
    @app.post("/engine/stop", dependencies=auth)
    # What: define engine_stop around body; why: the registered API client call engine_stop for engine stop and rely on this exact input and result contract.
    async def engine_stop(body: StopBody | None = None):
        # What: define operation around the current object state; why:  its direct callers call operation for operation and rely on this exact input and result contract.
        async def operation():
            # What: establish the handler boundary for the protected operation; why:  operation routes failures to accounting prepare error and accounting outbox error while preserving cleanup and success flow.
            try:
                # What: return run and lifecycle pool and stop and manager from operation; why: operation exposes run and lifecycle pool and stop and manager so its caller can continue with the function\'s computed outcome.
                return await run(lifecycle_pool, manager.stop, None, bool(body and body.force))
            # What: execute except AccountingPrepareError AccountingOutboxError as exc; why:  the enclosing symbol requires this operation for its concrete qualification or routing path.
            except (AccountingPrepareError, AccountingOutboxError) as exc:
                # What: return accounting error and exc from operation; why: operation exposes accounting error and exc so its caller can continue with the function\'s computed outcome.
                return accounting_error(exc)

        # What: return run manual transaction and operation and true from engine_stop; why: engine_stop exposes run manual transaction and operation and true so its caller can continue with the function\'s computed outcome.
        return await run_manual_transaction(operation, preempt_manual=True)

    @app.post("/shutdown", dependencies=auth)
    async def shutdown_daemon(request: Request, body: StopBody | None = None):
        # Tray "Stop daemon" stops everything: stop the engine FIRST so the default detach-on-exit can't
        # leave the ~18GB serve orphaned, THEN bring the daemon down. We reply before uvicorn
        # actually stops (it notices should_exit within ~0.1s) so the client still gets a clean 200.
        try:
            # What: compute owner from begin shutdown and router; why: owner later reads owner, so shutdown_daemon must retain the computed value under that name.
            owner = router.begin_shutdown()
        # What: handle routing error by return jsonresponse; why: shutdown_daemon converts that failure into this concrete recovery, response, or cleanup behavior.
        except RoutingError as exc:
            # What: return jsonresponse and status code and exc and code from shutdown_daemon; why: shutdown_daemon exposes jsonresponse and status code and exc and code so its caller can continue with the function\'s computed outcome.
            return JSONResponse(
                # What: supply status code to JSONResponse; why: shutdown_daemon binds this status code and exc value to JSONResponse's status code input.
                status_code=exc.status_code,
                # What: map the error field as code and str and exc and message and type; why: shutdown_daemon carries error into content={"error": {"message": str(exc), "type": exc.code}}.
                content={"error": {"message": str(exc), "type": exc.code}},
            # What: complete the JSONResponse call with status code and content; why: shutdown_daemon groups the supplied clauses as one JSONResponse call before its value is consumed.
            )

        # What: define operation around the current object state; why:  its direct callers call operation for operation and rely on this exact input and result contract.
        async def operation():
            # What: establish the handler boundary for the protected operation; why:  operation routes failures to accounting prepare error and accounting outbox error while preserving cleanup and success flow.
            try:
                # What: compute stopped from run and lifecycle pool and finish shutdown and owner; why: already stopped get already later reads stopped, so operation must retain the computed value under that name.
                stopped = await run(
                    # What: apply the lifecycle pool portion of stopped; why: operation uses this clause to evaluate stopped as one grouped value.
                    lifecycle_pool,
                    # What: apply the router finish shutdown portion of stopped; why: operation uses this clause to evaluate stopped as one grouped value.
                    router.finish_shutdown,
                    # What: apply the owner portion of stopped; why: operation uses this clause to evaluate stopped as one grouped value.
                    owner,
                    # What: apply the grouped expression portion of stopped; why: operation uses this clause to evaluate stopped as one grouped value.
                    None,
                    # What: call bool with body and force; why: operation consumes the bool return value while evaluating bool(body and body.force).
                    bool(body and body.force),
                # What: complete the run call with lifecycle pool and finish shutdown and owner and bool; why: operation groups the supplied clauses as one run call before its value is consumed.
                )
            # What: execute except AccountingPrepareError AccountingOutboxError as exc; why:  the enclosing symbol requires this operation for its concrete qualification or routing path.
            except (AccountingPrepareError, AccountingOutboxError) as exc:
                # What: return accounting error and exc from operation; why: operation exposes accounting error and exc so its caller can continue with the function\'s computed outcome.
                return accounting_error(exc)
            # What: compute req from getattr and state and app and request and request shutdown; why: if req is not later reads req, so operation must retain the computed value under that name.
            req = getattr(request.app.state, "request_shutdown", None)
            # What: gate on req before req; why: operation admits req only for this predicate and excludes the opposite state.
            if req is not None:
                # What: call req with the declared inputs; why: operation invokes req while performing return; the call advances that operation through its result or side effect.
                req()
            # What: return get and stopped and stopping and already and accounting from operation; why: operation exposes get and stopped and stopping and already and accounting so its caller can continue with the function\'s computed outcome.
            return {
                # What: map the stopping field as true; why: operation carries stopping into "stopping": True.
                "stopping": True,
                # What: map the already field as get and stopped and already and false; why: operation carries already into "already": stopped.get("already", False).
                "already": stopped.get("already", False),
                # What: map the accounting field as get and stopped and accounting; why: operation carries accounting into "accounting": stopped.get("accounting").
                "accounting": stopped.get("accounting"),
            # What: complete the enclosing predicate mapping with stopping and already and accounting; why: operation groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
            }

        # What: return run to completion and operation from shutdown_daemon; why: shutdown_daemon exposes run to completion and operation so its caller can continue with the function\'s computed outcome.
        return await run_to_completion(operation)

    @app.post("/engine/switch", dependencies=auth)
    async def engine_switch(body: SwitchBody):
        # What: define operation around the current object state; why:  its direct callers call operation for operation and rely on this exact input and result contract.
        async def operation():
            # What: establish the handler boundary for the protected operation; why: operation routes failures to accounting prepare error and accounting outbox error and exception while preserving cleanup and success flow.
            try:
                # What: compute port from resolve port and port and body; why: port later reads port, so operation must retain the computed value under that name.
                port = resolve_port(body.port)
                # What: return run and lifecycle pool and switch and model from operation; why: operation exposes run and lifecycle pool and switch and model so its caller can continue with the function\'s computed outcome.
                return await run(
                    # What: apply the lifecycle pool portion of the enclosing predicate; why: this clause remains in operation\'s enclosing expression so its grouping and evaluation order stay intact.
                    lifecycle_pool,
                    # What: apply the manager switch portion of the enclosing predicate; why: this clause remains in operation\'s enclosing expression so its grouping and evaluation order stay intact.
                    manager.switch,
                    # What: apply the body model portion of the enclosing predicate; why: this clause remains in operation\'s enclosing expression so its grouping and evaluation order stay intact.
                    body.model,
                    # What: apply the port portion of the enclosing predicate; why: this clause remains in operation\'s enclosing expression so its grouping and evaluation order stay intact.
                    port,
                    # What: call list with args and body; why: operation invokes list while performing body force; the call advances that operation through its result or side effect.
                    list(body.args),
                    # What: apply the body force portion of the enclosing predicate; why: this clause remains in operation\'s enclosing expression so its grouping and evaluation order stay intact.
                    body.force,
                # What: complete the run call with lifecycle pool and switch and model and port and list; why: operation groups the supplied clauses as one run call before its value is consumed.
                )
            # What: execute except AccountingPrepareError AccountingOutboxError as exc; why:  the enclosing symbol requires this operation for its concrete qualification or routing path.
            except (AccountingPrepareError, AccountingOutboxError) as exc:
                # What: return accounting error and exc from operation; why: operation exposes accounting error and exc so its caller can continue with the function\'s computed outcome.
                return accounting_error(exc)
            # What: handle exception by if isinstance exc switch launch error; why:  operation converts that failure into this concrete recovery, response, or cleanup behavior.
            except Exception as exc:  # noqa: BLE001
                # What: gate on isinstance and exc and switch launch error before the computed value; why:  operation admits the computed value only for this predicate and excludes the opposite state.
                if isinstance(exc, SwitchLaunchError):
                    # What: re-propagate the active failure to the caller; why:  operation stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise
                # What: raise HTTPException for the caller; why:  operation stops this rejected path before it can mutate state, dispatch work, or report success.
                raise HTTPException(status_code=500, detail=f"switch failed: {exc}")

        # What: return run manual transaction and operation from engine_switch; why: engine_switch exposes run manual transaction and operation so its caller can continue with the function\'s computed outcome.
        return await run_manual_transaction(operation)

    # What: register POST /engine/start-profile on the application router; why: clients reach engine_start_profile's handler only through this method-and-path binding.
    @app.post("/engine/start-profile", dependencies=auth)
    # What: define engine_start_profile around body; why: the registered API client call engine_start_profile for engine start profile and rely on this exact input and result contract.
    async def engine_start_profile(body: ProfileBody):
        # What: define operation around the current object state; why:  its direct callers call operation for operation and rely on this exact input and result contract.
        async def operation():
            # What: establish the handler boundary for the protected operation; why: operation routes failures to catalog error and conflict and exception while preserving cleanup and success flow.
            try:
                # What: compute model and port and args from profile request and name and body; why: result await run lifecycle pool manager start model later reads model and port and args, so operation must retain the computed value under that name.
                model, port, args = profile_request(body.name)
                # What: compute result from run and lifecycle pool and start and model; why: return await run proxy pool profile result body name later reads result, so operation must retain the computed value under that name.
                result = await run(lifecycle_pool, manager.start, model, port, args)
                # What: return run and proxy pool and profile result and name from operation; why: operation exposes run and proxy pool and profile result and name so its caller can continue with the function\'s computed outcome.
                return await run(proxy_pool, profile_result, body.name, result, port)
            # What: handle catalog error by raise httpexception status code 404 detail str exc; why:  operation converts that failure into this concrete recovery, response, or cleanup behavior.
            except CatalogError as exc:
                # What: raise HTTPException for the caller; why:  operation stops this rejected path before it can mutate state, dispatch work, or report success.
                raise HTTPException(status_code=404, detail=str(exc))
            # What: handle conflict by st manager status; why:  operation converts that failure into this concrete recovery, response, or cleanup behavior.
            except Conflict as exc:
                # What: compute st from status and manager; why: current model st get model later reads st, so  operation must retain the computed value under that name.
                st = manager.status()
                # What: return jsonresponse and str and exc and get from operation; why: operation exposes jsonresponse and str and exc and get so its caller can continue with the function\'s computed outcome.
                return JSONResponse(
                    # What: supply status code to JSONResponse; why:  operation binds this 409 value to JSONResponse's status code input.
                    status_code=409,
                    # What: supply content to JSONResponse; why:  operation binds this str and exc and get and st and error value to JSONResponse's content input.
                    content={
                        # What: map the error field as str and exc; why:  operation carries error into "error": str(exc).
                        "error": str(exc),
                        # What: map the code field as serve conflict; why:  operation carries code into "code": "serve_conflict".
                        "code": "serve_conflict",
                        # What: map the current model field as get and st and model; why:  operation carries current model into "currentModel": st.get("model").
                        "currentModel": st.get("model"),
                        # What: map the current port field as get and st and port; why:  operation carries current port into "currentPort": st.get("port").
                        "currentPort": st.get("port"),
                    # What: execute the grouped source fragment; why:  the enclosing symbol requires this operation for its concrete qualification or routing path.
                    },
                # What: complete the JSONResponse call with status code and content; why:  operation groups the supplied clauses as one JSONResponse call before its value is consumed.
                )
            # What: handle exception by raise httpexception status code 500 detail f profile; why: operation converts that failure into this concrete recovery, response, or cleanup behavior.
            except Exception as exc:  # noqa: BLE001
                # What: raise HTTPException for the caller; why:  operation stops this rejected path before it can mutate state, dispatch work, or report success.
                raise HTTPException(status_code=500, detail=f"profile start failed: {exc}")

        # What: return run manual transaction and operation from engine_start_profile; why: engine_start_profile exposes run manual transaction and operation so its caller can continue with the function\'s computed outcome.
        return await run_manual_transaction(operation)

    # What: register POST /engine/switch-profile on the application router; why: clients reach engine_switch_profile's handler only through this method-and-path binding.
    @app.post("/engine/switch-profile", dependencies=auth)
    # What: define engine_switch_profile around body; why: the registered API client call engine_switch_profile for engine switch profile and rely on this exact input and result contract.
    async def engine_switch_profile(body: ProfileBody):
        # What: define operation around the current object state; why:  its direct callers call operation for operation and rely on this exact input and result contract.
        async def operation():
            # What: establish the handler boundary for the protected operation; why: operation routes failures to catalog error and accounting prepare error and accounting outbox error and exception while preserving cleanup and success flow.
            try:
                # What: compute model and port and args from profile request and name and body; why: lifecycle pool manager switch for readiness model port args body force later reads model and port and args, so operation must retain the computed value under that name.
                model, port, args = profile_request(body.name)
                # What: compute result and ticket from run and lifecycle pool and switch for readiness and model; why: response await run proxy pool profile result body name later reads result and ticket, so operation must retain the computed value under that name.
                result, ticket = await run(
                    # What: apply the lifecycle pool manager switch for readiness model port args body force portion of result and ticket; why: operation uses this clause to evaluate result and ticket as one grouped value.
                    lifecycle_pool, manager.switch_for_readiness, model, port, args, body.force
                # What: complete the run call with lifecycle pool and switch for readiness and model and port and args; why: operation groups the supplied clauses as one run call before its value is consumed.
                )
                # What: compute response from run and proxy pool and profile result and name; why: if not isinstance response jsonresponse later reads response, so operation must retain the computed value under that name.
                response = await run(proxy_pool, profile_result, body.name, result, port)
                # What: gate on isinstance and response and jsonresponse before response; why: operation admits response only for this predicate and excludes the opposite state.
                if not isinstance(response, JSONResponse):
                    # What: return response from operation; why: operation exposes response so its caller can continue with the function\'s computed outcome.
                    return response
                # What: compute content from loads and body and json and response; why: content rollback rollback later reads content, so operation must retain the computed value under that name.
                content = json.loads(response.body)
                # What: compute rollback from run and lifecycle pool and recover switch and ticket; why: if rollback get launched later reads rollback, so operation must retain the computed value under that name.
                rollback = await run(lifecycle_pool, manager.recover_switch, ticket, body.force)
                # What: gate on get and rollback before profile and get and name and catalog and body; why: operation admits profile and get and name and catalog and body only for this predicate and excludes the opposite state.
                if rollback.get("launched"):
                    # What: compute profile from get and name and catalog and body; why: port rollback port timeout s profile ready timeout s later reads profile, so operation must retain the computed value under that name.
                    profile = router.catalog.get(body.name)
                    # What: compute rollback entry from run and proxy pool and partial and wait for ready; why: wait for ready manager probe pid rollback pid later reads rollback entry, so operation must retain the computed value under that name.
                    rollback["readiness"] = await run(proxy_pool, functools.partial(
                        # What: supply pid to run; why: operation binds this rollback and pid value to run's pid input.
                        wait_for_ready, manager, probe, pid=rollback["pid"],
                        # What: supply port to run; why: operation binds this rollback and port value to run's port input.
                        port=rollback["port"], timeout_s=profile.ready_timeout_s,
                    # What: complete the run call with proxy pool and partial; why: operation groups the supplied clauses as one run call before its value is consumed.
                    ))
                # What: compute content entry from rollback; why: return jsonresponse status code content content later reads content entry, so operation must retain the computed value under that name.
                content["rollback"] = rollback
                # What: return jsonresponse and content and 503 from operation; why: operation exposes jsonresponse and content and 503 so its caller can continue with the function\'s computed outcome.
                return JSONResponse(status_code=503, content=content)
            # What: handle catalog error by raise httpexception status code 404 detail str exc; why:  operation converts that failure into this concrete recovery, response, or cleanup behavior.
            except CatalogError as exc:
                # What: raise HTTPException for the caller; why:  operation stops this rejected path before it can mutate state, dispatch work, or report success.
                raise HTTPException(status_code=404, detail=str(exc))
            # What: execute except AccountingPrepareError AccountingOutboxError as exc; why:  the enclosing symbol requires this operation for its concrete qualification or routing path.
            except (AccountingPrepareError, AccountingOutboxError) as exc:
                # What: return accounting error and exc from operation; why: operation exposes accounting error and exc so its caller can continue with the function\'s computed outcome.
                return accounting_error(exc)
            # What: handle exception by if isinstance exc switch launch error; why:  operation converts that failure into this concrete recovery, response, or cleanup behavior.
            except Exception as exc:  # noqa: BLE001
                # What: gate on isinstance and exc and switch launch error before the computed value; why:  operation admits the computed value only for this predicate and excludes the opposite state.
                if isinstance(exc, SwitchLaunchError):
                    # What: re-propagate the active failure to the caller; why:  operation stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise
                # What: raise HTTPException for the caller; why:  operation stops this rejected path before it can mutate state, dispatch work, or report success.
                raise HTTPException(status_code=500, detail=f"profile switch failed: {exc}")

        # What: return run manual transaction and operation from engine_switch_profile; why: engine_switch_profile exposes run manual transaction and operation so its caller can continue with the function\'s computed outcome.
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
