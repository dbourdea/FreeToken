"""Aggregate the per-serve control API (``server/control_api.py``: ``/health``,
``/v1/stats``, ``/v1/admin/prepare-stop``) up to the daemon. The per-serve ``/health`` answers
"how is the model doing?" and dies with the serve; the daemon re-exposes it under
``/engine/health`` alongside
its own reachability, so a client has one control endpoint that OUTLIVES any single serve.

Blocking ``urllib`` (stdlib — no new dependency) run from the daemon's dedicated proxy executor
(kept off the lifecycle executor so a slow/loading serve can never starve
``/engine/stop``). Single-flight + short TTL cache: N concurrent pollers cost one upstream probe.
Serve docs are snake_case; they are transformed to the daemon's camelCase contract."""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from .accounting import AccountingPrepareError, PrepareStopUnavailable

_SNAKE_RE = re.compile(r"_([a-z0-9])")


def _camel_key(key: str) -> str:
    return _SNAKE_RE.sub(lambda m: m.group(1).upper(), key)


def to_camel(obj: Any) -> Any:
    """Recursively camelCase dict keys (uptime_s→uptimeS, done_bytes→doneBytes, …) so the daemon
    emits one casing convention everywhere."""
    if isinstance(obj, dict):
        return {_camel_key(k): to_camel(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_camel(v) for v in obj]
    return obj


class ServeProbe:
    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        ttl_s: float = 0.25,
        timeout_s: float = 1.5,
        prepare_timeout_s: float = 15.0,
        now: Callable[[], float] = time.monotonic,
        opener: Callable[[str, float], dict] | None = None,
        prepare_opener: Callable[[str, float], dict] | None = None,
    ) -> None:
        self._host = host
        self._ttl = ttl_s
        self._timeout = timeout_s
        self._prepare_timeout = prepare_timeout_s
        self._now = now
        self._opener = opener or self._urlopen
        self._prepare_opener = prepare_opener or self._urlopen_prepare
        self._lock = threading.Lock()
        self._cache: dict[tuple[str, int], tuple[float, dict]] = {}

    def health(self, port: int) -> dict:
        return self._cached("health", "/health", port)

    # What: define an uncached health probe for the active engine port; why: readiness checks must bypass a replaced generation's cached response before accepting the new process.
    def fresh_health(self, port: int) -> dict:
        """Read this generation, never a cached response from a replaced engine."""
        # What: document read this generation never a cached in the fresh_health docstring; why: introspection and maintainers read this exact docstring fragment to understand fresh health behavior without executing it.
        # What: return fetch and port and health from fresh_health; why: fresh_health exposes fetch and port and health so its caller can continue with the function\'s computed outcome.
        return self._fetch("/health", port)

    # What: define fresh_readiness around the active port and probe path; why: callers route health probes through fresh_health and fetch other readiness paths directly, preserving generation-local evidence.
    def fresh_readiness(self, port: int, path: str) -> dict:
        """Probe a validated profile path without reusing prior-generation state."""
        # What: document probe a validated profile path without in the fresh_readiness docstring; why: introspection and maintainers read this exact docstring fragment to understand fresh readiness behavior without executing it.
        # What: gate on path before fresh health and port; why: fresh_readiness admits fresh health and port only for this predicate and excludes the opposite state.
        if path == "/health":
            # What: return fresh health and port from fresh_readiness; why: fresh_readiness exposes fresh health and port so its caller can continue with the function\'s computed outcome.
            return self.fresh_health(port)
        # What: return fetch and path and port from fresh_readiness; why: fresh_readiness exposes fetch and path and port so its caller can continue with the function\'s computed outcome.
        return self._fetch(path, port)

    def stats(self, port: int) -> dict:
        return self._cached("stats", "/v1/stats", port)

    def fresh_stats(self, port: int) -> dict:
        """Fetch uncached stats for a legacy stop receipt."""
        return self._fetch("/v1/stats", port)

    def prepare_stop(self, port: int) -> dict:
        """Quiesce the engine and return its sealed final accounting snapshot."""
        url = f"http://{self._host}:{port}/v1/admin/prepare-stop"
        try:
            doc = self._prepare_opener(url, self._prepare_timeout)
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 405):
                raise PrepareStopUnavailable("legacy-engine") from exc
            raise AccountingPrepareError(f"prepare-stop returned HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise AccountingPrepareError(f"prepare-stop request failed: {exc}") from exc
        if not isinstance(doc, dict):
            raise AccountingPrepareError("prepare-stop returned a non-object response")
        return doc

    def _cached(self, kind: str, path: str, port: int) -> dict:
        key = (kind, port)
        # Hold the lock across the fetch so concurrent pollers collapse to a single upstream call
        # (true single-flight); the short timeout + TTL keep the critical section cheap.
        with self._lock:
            hit = self._cache.get(key)
            if hit is not None and (self._now() - hit[0]) < self._ttl:
                return hit[1]
            val = self._fetch(path, port)
            self._cache[key] = (self._now(), val)
            return val

    def _fetch(self, path: str, port: int) -> dict:
        url = f"http://{self._host}:{port}{path}"
        try:
            doc = self._opener(url, self._timeout)
        except urllib.error.HTTPError as exc:
            return {"reachable": True, "status": "error", "httpStatus": exc.code}
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return {"reachable": False, "status": "unreachable"}
        result = to_camel(doc) if isinstance(doc, dict) else {"value": doc}
        result["reachable"] = True
        return result

    @staticmethod
    def _urlopen(url: str, timeout: float) -> dict:
        req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        # What: establish the handler boundary for the protected operation; why: ServeProbe._urlopen routes failures to unicode decode error and jsondecode error and json while preserving cleanup and success flow.
        try:
            # What: return loads and json and decode and raw and utf 8 from _urlopen; why: _urlopen exposes loads and json and decode and raw and utf 8 so its caller can continue with the function\'s computed outcome.
            return json.loads(raw.decode("utf-8"))
        # What: handle unicode decode error and jsondecode error and json by return; why: ServeProbe._urlopen converts that failure into this concrete recovery, response, or cleanup behavior.
        except (UnicodeDecodeError, json.JSONDecodeError):
            # A custom readiness endpoint follows HTTP-status semantics. Do
            # not retain or surface an arbitrary successful response body.
            # What: return no value from _urlopen; why: _urlopen returns no value to callers that depend on its completed result.
            return {}

    @staticmethod
    def _urlopen_prepare(url: str, timeout: float) -> dict:
        req = urllib.request.Request(
            url,
            data=b"{}",
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return json.loads(raw.decode("utf-8"))
