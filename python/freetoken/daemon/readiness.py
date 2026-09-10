"""Wait for a newly launched FreeToken serve to report its own readiness.

The daemon never treats a listening socket as ready.  ``/health`` is the
engine's lifecycle authority and reports ``loading``, ``ok``, or ``error``.
This helper intentionally does not kill an engine on timeout: model loads can
be slow, and the existing manager must keep the still-visible process available
for logs, diagnosis, or an explicit operator stop.
"""

from __future__ import annotations

import time
from typing import Any, Callable


def wait_for_ready(
    manager,
    probe,
    *,
    pid: int | None,
    port: int,
    timeout_s: float,
    now: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    deadline = now() + timeout_s
    last: dict[str, Any] = {"reachable": False, "status": "unreachable"}
    while True:
        state = manager.status()
        if not state.get("running") or (pid is not None and state.get("pid") != pid):
            return {"ready": False, "reason": "superseded", "health": last}
        last = probe.health(port)
        if last.get("reachable") and last.get("status") == "ok":
            return {"ready": True, "health": last}
        if last.get("status") == "error":
            return {"ready": False, "reason": "engine-error", "health": last}
        remaining = deadline - now()
        if remaining <= 0:
            return {"ready": False, "reason": "timeout", "health": last}
        sleep(min(0.25, remaining))
