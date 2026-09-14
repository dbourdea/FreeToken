"""Native, transport-independent admission and model activation for freetoken-swap.

The router owns the decision to retain an already ready engine or to make a
safe lifecycle transition before an inference request is forwarded. It does
not implement HTTP itself: keeping this boundary small makes FIFO priority,
leases, readiness, and rollback directly testable without a model runtime.
"""

from __future__ import annotations

import threading
import socket
import time
from dataclasses import dataclass
from typing import Callable

from .catalog import CatalogError, ModelCatalog, ModelProfile
from .readiness import wait_for_ready
from .serve_manager import Conflict, SwitchLaunchError


def allocate_loopback_port() -> int:
    """Ask the kernel for an ephemeral loopback TCP port.

    The listener is intentionally closed before the child starts: FreeToken's
    serve process, not the daemon, must own the listening socket. The manager
    serializes the immediately following launch; a hostile or unrelated local
    process can still win that unavoidable bind race, in which case readiness
    fails closed and the normal rollback path applies.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


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
        port_allocator: Callable[[], int] = allocate_loopback_port,
    ) -> None:
        self._manager = manager
        self._catalog = catalog
        self._probe = probe
        self._default_port = default_port
        self._ready_fn = ready_fn
        self._timer_factory = timer_factory or self._new_timer
        self._port_allocator = port_allocator
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
        self._last_activation_ms: float | None = None
        self._last_queue_wait_ms: float | None = None
        self._last_response_bytes: int | None = None
        self._last_proxy_bytes_per_second: float | None = None
        self._adopt_exact_catalog_resident()

    def _adopt_exact_catalog_resident(self) -> None:
        """Bind one unambiguous catalog profile to a manager-re-adopted engine.

        Dynamic-port profiles match the concrete persisted port. If multiple
        aliases describe the same process identity, fail closed rather than
        inventing which alias owns residency.
        """
        state = self._manager.status()
        port = state.get("port")
        if not state.get("running") or not isinstance(port, int) or port <= 0:
            return
        args = self._manager.serve_args()
        matches = [
            profile for profile in self._catalog.profiles()
            if profile.model == state.get("model")
            and (profile.port == port or profile.port == 0)
            and list(profile.args) == args
        ]
        if len(matches) != 1:
            return
        self._active_name = matches[0].name
        self._schedule_idle_eviction()

    def acquire(self, name: str, cancellation: threading.Event | None = None) -> RouteLease:
        """Return a lease only after *name* has a health-verified engine."""
        try:
            profile = self._catalog.get(name)
        except CatalogError as exc:
            raise RoutingError("unknown_model", str(exc), status_code=404) from exc
        port = self._port_for(profile)
        queued_at = time.monotonic()
        with self._cond:
            if cancellation is not None and cancellation.is_set():
                raise RoutingError(
                    "request_cancelled", "request cancelled before admission", status_code=409
                )
            ticket = (-profile.priority, self._next_sequence, name)
            self._next_sequence += 1
            self._pending.append(ticket)
            while True:
                if cancellation is not None and cancellation.is_set():
                    self._pending.remove(ticket)
                    self._cond.notify_all()
                    raise RoutingError(
                        "request_cancelled", "request cancelled before admission", status_code=409
                    )
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
                    self._last_queue_wait_ms = round((time.monotonic() - queued_at) * 1000, 3)
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

        activated_at = time.monotonic()
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
            self._last_queue_wait_ms = round((activated_at - queued_at) * 1000, 3)
            self._last_activation_ms = round((time.monotonic() - activated_at) * 1000, 3)
            self._cond.notify_all()
        return RouteLease(self, profile, port, pid)

    def cancel_acquire(self, cancellation: threading.Event) -> None:
        """Wake a queued admission so it can observe caller cancellation."""
        with self._cond:
            cancellation.set()
            self._cond.notify_all()

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
            active_identity_matches = self._active_matches_engine_locked()
            return {
                "activeProfile": self._active_name,
                "activeGroup": group.name if group else None,
                "residentProfiles": [self._active_name] if active_identity_matches else [],
                "activeIdentityMatchesEngine": active_identity_matches,
                "persistent": bool(active_identity_matches and group and group.persistent),
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
                "lastActivationMs": self._last_activation_ms,
                "lastQueueWaitMs": self._last_queue_wait_ms,
                "lastResponseBytes": self._last_response_bytes,
                "lastProxyBytesPerSecond": self._last_proxy_bytes_per_second,
                "scheduler": self._catalog.settings.scheduler,
            }

    @property
    def catalog(self) -> ModelCatalog:
        with self._cond:
            return self._catalog

    def active_matches_engine(self) -> bool:
        """Whether the manager still owns the exact resident routed profile.

        A listening child alone is not a readiness signal: an out-of-band or
        stale child must not make the stable router URL appear healthy for the
        alias recorded by the coordinator.
        """
        with self._cond:
            return self._active_matches_engine_locked()

    def is_ready(self, probe=None) -> bool:
        """Atomically verify resident identity and fresh engine readiness.

        Holding the admission condition across the bounded loopback probe keeps
        a conflicting swap from committing between an identity snapshot and a
        stale successful health response.
        """
        with self._cond:
            if self._switching or not self._active_matches_engine_locked():
                return False
            state = self._manager.status()
            port = state.get("port")
            if not isinstance(port, int) or port <= 0:
                return False
            health = (probe or self._probe).fresh_health(port)
            if self._switching or not self._active_matches_engine_locked():
                return False
            return bool(
                health.get("reachable")
                and health.get("status") == "ok"
                and health.get("maintenance", "serving") == "serving"
            )

    @property
    def upstream_timeout_s(self) -> float:
        with self._cond:
            return self._catalog.settings.upstream_timeout_s

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
                current_group = self._catalog.group_for(self._active_name)
                replacement_group = catalog.group_for(self._active_name)
                current_ttl = (
                    current.ttl_s if current.ttl_s is not None else self._catalog.settings.default_ttl_s
                )
                replacement_ttl = (
                    replacement.ttl_s if replacement.ttl_s is not None else catalog.settings.default_ttl_s
                )
                current_unload_timeout = (
                    current.unload_timeout_s
                    if current.unload_timeout_s is not None
                    else self._catalog.settings.unload_timeout_s
                )
                replacement_unload_timeout = (
                    replacement.unload_timeout_s
                    if replacement.unload_timeout_s is not None
                    else catalog.settings.unload_timeout_s
                )
                if (
                    replacement != current
                    or replacement_group != current_group
                    or replacement_ttl != current_ttl
                    or replacement_unload_timeout != current_unload_timeout
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
            "active_identity_matches_engine": int(status["activeIdentityMatchesEngine"]),
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
        for name, value in (
            ("last_ttft_ms", status["lastTtftMs"]),
            ("last_duration_ms", status["lastDurationMs"]),
            ("last_activation_ms", status["lastActivationMs"]),
            ("last_queue_wait_ms", status["lastQueueWaitMs"]),
            ("last_response_bytes", status["lastResponseBytes"]),
            ("last_proxy_bytes_per_second", status["lastProxyBytesPerSecond"]),
        ):
            if value is not None:
                metric = f"freetoken_swap_{name}"
                lines.extend((f"# TYPE {metric} gauge", f"{metric} {value}"))
        return "\n".join(lines) + "\n"

    def record_cancellation(self) -> None:
        with self._cond:
            self._cancellations += 1

    def record_stream(
        self, *, ttft_s: float | None, duration_s: float, response_bytes: int, completed: bool = True
    ) -> None:
        """Record transport timing without crediting a router-cancelled stream as complete."""
        with self._cond:
            if completed:
                self._terminal_streams += 1
            self._last_ttft_ms = round(ttft_s * 1000, 3) if ttft_s is not None else None
            self._last_duration_ms = round(duration_s * 1000, 3)
            self._last_response_bytes = response_bytes
            self._last_proxy_bytes_per_second = round(response_bytes / duration_s, 3) if duration_s > 0 else None

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
            port = self._port_for(profile)
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

    def _active_matches_engine_locked(self) -> bool:
        """Internal exact-identity check; caller holds ``self._cond``."""
        if self._active_name is None:
            return False
        try:
            profile = self._catalog.get(self._active_name)
        except CatalogError:
            return False
        return self._matches_active(profile, self._port_for(profile))

    def _port_for(self, profile: ModelProfile) -> int:
        """Resolve a profile's proxy/readiness target under router ownership."""
        if profile.port is None:
            return self._default_port
        if profile.port != 0:
            return profile.port
        state = self._manager.status()
        # A dynamic profile retains its concrete port for its whole residency;
        # a fresh activation gets a new kernel-selected one.
        if (self._active_name == profile.name and state.get("running")
                and isinstance(state.get("port"), int) and state["port"] > 0):
            return state["port"]
        return self._port_allocator()

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
