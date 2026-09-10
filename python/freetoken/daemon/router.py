"""Native, transport-independent admission and model activation for freetoken-swap.

The router owns the decision to retain an already ready engine or to make a
safe lifecycle transition before an inference request is forwarded. It does
not implement HTTP itself: keeping this boundary small makes FIFO priority,
leases, readiness, and rollback directly testable without a model runtime.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable

from .catalog import CatalogError, ModelCatalog, ModelProfile
from .readiness import wait_for_ready
from .serve_manager import Conflict, SwitchLaunchError


class RoutingError(RuntimeError):
    """A request could not be admitted to a ready native engine."""

    def __init__(self, code: str, detail: str, *, status_code: int = 503, recovery: dict | None = None):
        super().__init__(detail)
        self.code = code
        self.status_code = status_code
        self.recovery = recovery


@dataclass(frozen=True)
class RouteLease:
    """One admitted request. Call :meth:`release` exactly once when it ends."""

    router: "RoutingCoordinator"
    profile: ModelProfile
    port: int
    pid: int | None

    def release(self) -> None:
        self.router.release(self)


class RoutingCoordinator:
    """Serialize unsafe swaps while allowing concurrent requests for one engine.

    A higher profile priority wins over lower priority requests that have not
    begun an activation. Equal priorities use strict FIFO ordering. A swap is
    never started while an admitted lease exists, which preserves streaming
    requests and their cancellation semantics.
    """

    def __init__(
        self,
        manager,
        catalog: ModelCatalog,
        probe,
        *,
        default_port: int = 1919,
        ready_fn: Callable = wait_for_ready,
        timer_factory: Callable[[float, Callable[[], None]], object] | None = None,
    ) -> None:
        self._manager = manager
        self._catalog = catalog
        self._probe = probe
        self._default_port = default_port
        self._ready_fn = ready_fn
        self._timer_factory = timer_factory or self._new_timer
        self._cond = threading.Condition(threading.Lock())
        self._next_sequence = 0
        self._pending: list[tuple[int, int, str]] = []
        self._leases = 0
        self._active_name: str | None = None
        self._switching = False
        self._idle_timer: object | None = None
        self._evictions = 0
        self._admissions = 0
        self._activations = 0
        self._activation_failures = 0
        self._cancellations = 0
        self._terminal_streams = 0
        self._last_ttft_ms: float | None = None
        self._last_duration_ms: float | None = None

    def acquire(self, name: str) -> RouteLease:
        """Return a lease only after *name* has a health-verified engine."""
        try:
            profile = self._catalog.get(name)
        except CatalogError as exc:
            raise RoutingError("unknown_model", str(exc), status_code=404) from exc
        port = profile.port or self._default_port
        with self._cond:
            ticket = (-profile.priority, self._next_sequence, name)
            self._next_sequence += 1
            self._pending.append(ticket)
            while True:
                head = min(self._pending)
                if ticket != head:
                    self._cond.wait()
                    continue
                if self._switching:
                    self._cond.wait()
                    continue
                if self._matches_active(profile, port):
                    self._cancel_idle_timer()
                    self._pending.remove(ticket)
                    self._leases += 1
                    self._admissions += 1
                    state = self._manager.status()
                    self._cond.notify_all()
                    return RouteLease(self, profile, port, state.get("pid"))
                if self._leases:
                    self._cond.wait()
                    continue
                block = self._capacity_block(profile)
                if block is not None:
                    self._pending.remove(ticket)
                    self._cond.notify_all()
                    raise RoutingError("capacity_unavailable", block, status_code=409)
                self._switching = True
                self._pending.remove(ticket)
                break

        try:
            pid = self._activate(profile, port)
        except Exception as exc:
            with self._cond:
                self._switching = False
                self._activation_failures += 1
                self._cond.notify_all()
            if isinstance(exc, RoutingError):
                raise
            if isinstance(exc, SwitchLaunchError):
                raise RoutingError("switch_launch_failed", str(exc), recovery=exc.rollback) from exc
            if isinstance(exc, Conflict):
                raise RoutingError("serve_conflict", str(exc), status_code=409) from exc
            raise RoutingError("activation_failed", str(exc)) from exc
        with self._cond:
            self._active_name = profile.name
            self._switching = False
            self._cancel_idle_timer()
            self._leases += 1
            self._admissions += 1
            self._cond.notify_all()
        return RouteLease(self, profile, port, pid)

    def release(self, lease: RouteLease) -> None:
        with self._cond:
            if lease.router is not self:
                raise ValueError("lease belongs to a different routing coordinator")
            if self._leases <= 0:
                raise ValueError("routing lease was already released")
            self._leases -= 1
            if self._leases == 0:
                self._schedule_idle_eviction()
            self._cond.notify_all()

    def status(self) -> dict:
        with self._cond:
            group = self._catalog.group_for(self._active_name) if self._active_name else None
            return {
                "activeProfile": self._active_name,
                "activeGroup": group.name if group else None,
                "residentProfiles": [self._active_name] if self._active_name else [],
                "persistent": bool(group and group.persistent),
                "capacity": {"maxResidentModels": 1, "availableResidentSlots": 0 if self._active_name else 1},
                "activeRequests": self._leases,
                "switching": self._switching,
                "queuedRequests": len(self._pending),
                "idleEvictionScheduled": self._idle_timer is not None,
                "evictions": self._evictions,
                "admissions": self._admissions,
                "activations": self._activations,
                "activationFailures": self._activation_failures,
                "cancellations": self._cancellations,
                "terminalStreams": self._terminal_streams,
                "lastTtftMs": self._last_ttft_ms,
                "lastDurationMs": self._last_duration_ms,
                "scheduler": self._catalog.settings.scheduler,
            }

    @property
    def catalog(self) -> ModelCatalog:
        with self._cond:
            return self._catalog

    def replace_catalog(self, catalog: ModelCatalog) -> None:
        """Atomically install a validated catalog without changing a live engine.

        Removing or redefining the active profile is refused. The operator can
        explicitly unload first, which keeps configuration reload from silently
        changing the ownership contract of an existing engine.
        """
        with self._cond:
            if self._active_name is not None:
                try:
                    replacement = catalog.get(self._active_name)
                    current = self._catalog.get(self._active_name)
                except CatalogError as exc:
                    raise RoutingError(
                        "reload_conflict",
                        "cannot remove the active profile until it is unloaded",
                        status_code=409,
                    ) from exc
                if (replacement.model, replacement.port, replacement.args) != (
                    current.model, current.port, current.args
                ):
                    raise RoutingError(
                        "reload_conflict",
                        "cannot redefine the active profile until it is unloaded",
                        status_code=409,
                    )
            self._catalog = catalog
            self._cond.notify_all()

    def prometheus(self) -> str:
        """Render bounded router counters without importing a metrics package."""
        status = self.status()
        values = {
            "active_requests": status["activeRequests"],
            "queued_requests": status["queuedRequests"],
            "admissions_total": status["admissions"],
            "activations_total": status["activations"],
            "activation_failures_total": status["activationFailures"],
            "cancellations_total": status["cancellations"],
            "terminal_streams_total": status["terminalStreams"],
            "evictions_total": status["evictions"],
        }
        lines = []
        for name, value in values.items():
            metric = f"freetoken_swap_{name}"
            metric_type = "counter" if name.endswith("_total") else "gauge"
            lines.extend((f"# TYPE {metric} {metric_type}", f"{metric} {value}"))
        for name, value in (("last_ttft_ms", status["lastTtftMs"]),
                            ("last_duration_ms", status["lastDurationMs"])):
            if value is not None:
                metric = f"freetoken_swap_{name}"
                lines.extend((f"# TYPE {metric} gauge", f"{metric} {value}"))
        return "\n".join(lines) + "\n"

    def record_cancellation(self) -> None:
        with self._cond:
            self._cancellations += 1

    def record_stream(self, *, ttft_s: float | None, duration_s: float) -> None:
        with self._cond:
            self._terminal_streams += 1
            self._last_ttft_ms = round(ttft_s * 1000, 3) if ttft_s is not None else None
            self._last_duration_ms = round(duration_s * 1000, 3)

    def evict_idle(self, name: str | None = None) -> bool:
        """Unload a truly idle matching engine, preserving lifecycle accounting.

        The timer calls this method, and tests may call it directly. A stale
        timer cannot unload a newer profile because identity is checked under
        admission before entering the manager lifecycle transaction.
        """
        with self._cond:
            active = self._active_name
            if name is not None and active != name:
                return False
            if active is None or self._leases or self._switching:
                return False
            profile = self._catalog.get(active)
            port = profile.port or self._default_port
            if not self._matches_active(profile, port):
                self._active_name = None
                self._idle_timer = None
                self._cond.notify_all()
                return False
            self._switching = True
            self._idle_timer = None
        try:
            timeout = profile.unload_timeout_s or self._catalog.settings.unload_timeout_s
            self._manager.stop(timeout=timeout)
        except Exception:
            with self._cond:
                self._switching = False
                self._cond.notify_all()
            raise
        with self._cond:
            self._active_name = None
            self._switching = False
            self._evictions += 1
            self._cond.notify_all()
        return True

    @staticmethod
    def _new_timer(delay: float, callback: Callable[[], None]):
        timer = threading.Timer(delay, callback)
        timer.daemon = True
        return timer

    def _cancel_idle_timer(self) -> None:
        if self._idle_timer is not None:
            self._idle_timer.cancel()
            self._idle_timer = None

    def _schedule_idle_eviction(self) -> None:
        if self._active_name is None:
            return
        profile = self._catalog.get(self._active_name)
        ttl = profile.ttl_s if profile.ttl_s is not None else self._catalog.settings.default_ttl_s
        if ttl <= 0:
            return
        self._cancel_idle_timer()
        timer = self._timer_factory(ttl, lambda: self.evict_idle(profile.name))
        self._idle_timer = timer
        timer.start()

    def _capacity_block(self, target: ModelProfile) -> str | None:
        """Return a capacity-policy explanation, if a swap cannot be admitted."""
        if self._active_name is None or self._active_name == target.name:
            return None
        active_group = self._catalog.group_for(self._active_name)
        target_group = self._catalog.group_for(target.name)
        if active_group is not None and active_group.persistent:
            return (
                f"active profile {self._active_name!r} is persistent and consumes the "
                "single resident-model slot; unload it before selecting another profile"
            )
        if target_group is not None and target_group.persistent:
            return (
                f"profile {target.name!r} requires a persistent resident slot; unload the "
                "current profile before selecting it"
            )
        return None

    def _matches_active(self, profile: ModelProfile, port: int) -> bool:
        state = self._manager.status()
        return bool(
            self._active_name == profile.name
            and state.get("running")
            and state.get("model") == profile.model
            and state.get("port") == port
            and self._manager.serve_args() == list(profile.args)
        )

    def _activate(self, profile: ModelProfile, port: int) -> int | None:
        state = self._manager.status()
        exact = (
            state.get("running")
            and state.get("model") == profile.model
            and state.get("port") == port
            and self._manager.serve_args() == list(profile.args)
        )
        ticket = None
        if exact:
            result = {"pid": state.get("pid"), "idempotent": True}
        elif state.get("running"):
            with self._cond:
                self._activations += 1
            result, ticket = self._manager.switch_for_readiness(
                profile.model, port, list(profile.args)
            )
        else:
            with self._cond:
                self._activations += 1
            result = self._manager.start(profile.model, port, list(profile.args))
        readiness = self._ready_fn(
            self._manager,
            self._probe,
            pid=result.get("pid"),
            port=port,
            timeout_s=profile.ready_timeout_s,
        )
        if readiness.get("ready"):
            return result.get("pid")
        recovery = None
        if ticket is not None:
            recovery = self._manager.recover_switch(ticket)
        reason = readiness.get("reason", "not-ready")
        raise RoutingError(
            "engine_not_ready",
            f"profile {profile.name!r} is not ready: {reason}",
            recovery=recovery,
        )
