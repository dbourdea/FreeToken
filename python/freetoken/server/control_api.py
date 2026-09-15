"""Read-only control-plane endpoints consumed by the desktop app: /health (lifecycle),
/v1/stats (runtime metrics, Task 6), /v1/requests (request log ring, Task 5).

All handlers read a shared FrontendManager snapshot via ``get_state``; nothing here touches
the scheduler or blocks. Registered on the app alongside the OpenAI/Anthropic/Responses routes.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from fastapi import FastAPI


def build_health(state: Any, version: str) -> dict:
    """Full-lifecycle health doc: loading -> ok -> error."""
    instance_id = getattr(state, "instance_id", None)
    fatal = getattr(state, "fatal_error", None)
    if fatal:
        return {"status": "error", "message": fatal, "instance_id": instance_id}

    mstate = getattr(state, "maintenance_state", "serving")
    config = getattr(state, "config", None)
    model = getattr(config, "served_model_name", None)

    if mstate == "loading":
        lp = getattr(state, "load_progress", None)
        return {
            "status": "loading",
            "phase": lp.phase if lp is not None else "other",
            "progress": {
                "done_bytes": lp.done_bytes if lp is not None else 0,
                "total_bytes": lp.total_bytes if lp is not None else 0,
            },
            "model": model,
            "instance_id": instance_id,
        }

    ready_at = getattr(state, "ready_at", None)
    uptime_s = max(0, int(time.monotonic() - ready_at)) if ready_at is not None else 0
    return {
        "status": "ok",
        "model": model,
        "instance_id": instance_id,
        "uptime_s": uptime_s,
        "maintenance": mstate,
        "version": version,
    }


def register_control_routes(
    app: FastAPI,
    get_state: Callable[[], Any],
    get_model_sampling: Callable[[], dict] | None = None,
) -> None:
    @app.get("/health")
    async def health():
        return build_health(get_state(), app.version)

    # What: register GET /ready on the application router; why: clients reach ready's handler only through this method-and-path binding.
    @app.get("/ready")
    # What: define ready around the current object state; why: the registered API client call ready for ready and rely on this exact input and result contract.
    async def ready():
        """HTTP readiness for supervisors that cannot inspect health JSON."""
        # What: document http readiness for supervisors that cannot in the ready docstring; why: introspection and maintainers read this exact docstring fragment to understand ready behavior without executing it.
        # What: import jsonresponse for ready using fastapi and responses and jsonresponse; why: ready uses jsonresponse, making that imported dependency available to its named operation.
        from fastapi.responses import JSONResponse

        # What: compute doc from build health and version and get state and app; why: accepting doc get status ok and doc get later reads doc, so ready must retain the computed value under that name.
        doc = build_health(get_state(), app.version)
        # What: compute accepting from get and doc and ok and serving and status; why: return jsonresponse status code if accepting else later reads accepting, so ready must retain the computed value under that name.
        accepting = doc.get("status") == "ok" and doc.get("maintenance") == "serving"
        # What: return HTTP 200 when accepting and 503 otherwise; why: supervisors use this status and ready boolean to decide whether the daemon control plane may receive traffic.
        return JSONResponse(status_code=200 if accepting else 503, content=doc)

    from . import request_ring

    @app.get("/v1/requests")
    async def list_requests(since: int = 0, limit: int = 100):
        limit = max(1, min(limit, 512))
        entries, next_cursor = request_ring.requests_since(since, limit)
        return {"entries": entries, "next_cursor": next_cursor}

    from .stats import build_stats

    @app.get("/v1/stats")
    async def stats():
        doc = build_stats(
            get_state(), request_ring.requests_p95_ms(), request_ring.requests_ttft_mean_ms()
        )
        # Surface the model's recommended sampling (from its generation_config.json / GGUF
        # metadata) so clients can seed their sampling controls per-model instead of guessing.
        if get_model_sampling is not None:
            doc["model"]["sampling"] = get_model_sampling() or {}
        return doc
