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
                    state = self._manager.status()
                    self._cond.notify_all()
                    return RouteLease(self, profile, port, state.get("pid"))
                if self._leases:
                    self._cond.wait()
                    continue
                self._switching = True
                self._pending.remove(ticket)
                break

        try:
            pid = self._activate(profile, port)
        except Exception as exc:
            with self._cond:
                self._switching = False
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
            return {
                "activeProfile": self._active_name,
                "activeRequests": self._leases,
                "switching": self._switching,
                "queuedRequests": len(self._pending),
                "idleEvictionScheduled": self._idle_timer is not None,
                "evictions": self._evictions,
                "scheduler": self._catalog.settings.scheduler,
            }

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
            result, ticket = self._manager.switch_for_readiness(
                profile.model, port, list(profile.args)
            )
        else:
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
