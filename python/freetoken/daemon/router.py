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
from dataclasses import dataclass, field
from typing import Callable

from .catalog import DEFAULT_CHECK_ENDPOINT, CatalogError, ModelCatalog, ModelProfile
from .readiness import wait_for_ready
from .serve_manager import Conflict, SwitchLaunchError


DEFAULT_PROFILE_CONCURRENCY_LIMIT = 10


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


@dataclass
class RouteLease:
    """One admitted request. Call :meth:`release` exactly once when it ends."""

    router: "RoutingCoordinator"
    profile: ModelProfile
    port: int
    pid: int | None
    model_id: str | None = None
    selector_id: str | None = None
    routing_profile_id: str | None = None
    pin_id: str | None = None
    _released: bool = field(default=False, init=False, repr=False)

    def release(self) -> None:
        self.router.release(self)

    @property
    def proxy_base_url(self) -> str:
        return self.profile.proxy_base_url(self.port)


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
        self._pending_by_cancellation: dict[
            threading.Event, tuple[tuple[int, int, str], ModelProfile]
        ] = {}
        self._leases = 0
        self._reservations = 0
        self._profile_reservations: dict[str, int] = {}
        self._active_name: str | None = None
        self._active_routing_profile: str | None = None
        self._activating_name: str | None = None
        self._activating_port: int | None = None
        self._switching = False
        self._manual_lifecycle_owner: object | None = None
        self._manual_lifecycle_tokens: set[object] = set()
        self._shutdown_requested = False
        self._shutdown_owner: object | None = None
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

        Omitted ports match the configured default and dynamic-port profiles
        match the concrete persisted port. If multiple profiles describe the
        same process identity, fail closed rather than inventing which one owns
        residency.
        """
        state = self._manager.status()
        port = state.get("port")
        if not state.get("running") or not isinstance(port, int) or port <= 0:
            return
        args = self._manager.serve_args()
        matches = [
            profile for profile in self._catalog.profiles()
            if profile.model == state.get("model")
            and (
                profile.port == port
                or profile.port == 0
                or (profile.port is None and port == self._default_port)
            )
            and list(profile.args) == args
        ]
        if len(matches) != 1:
            return
        self._active_name = matches[0].name
        self._schedule_idle_eviction()

    def acquire(
        self,
        name: str,
        cancellation: threading.Event | None = None,
        on_reserved: Callable[[bool, int], None] | None = None,
        *,
        apply_loading_policy: bool = False,
        apply_routing_profile: bool = True,
    ) -> RouteLease:
        """Return a lease only after *name* has a health-verified engine."""
        queued_at = time.monotonic()
        with self._cond:
            if self._shutdown_requested:
                raise RoutingError(
                    "router_shutting_down", "router shutdown is in progress", status_code=503
                )
            try:
                model_id, profile, selector_id, routing_profile_id, pin_id = (
                    self._resolve_request_locked(
                        name, apply_routing_profile=apply_routing_profile
                    )
                )
            except CatalogError as exc:
                raise RoutingError("unknown_model", str(exc), status_code=404) from exc
            if cancellation is not None and cancellation.is_set():
                raise RoutingError(
                    "request_cancelled", "request cancelled before admission", status_code=409
                )
            self._reserve_concurrency_locked(profile)
            ticket = (-profile.priority, self._next_sequence, profile.name)
            self._next_sequence += 1
            self._pending.append(ticket)
            if cancellation is not None:
                self._pending_by_cancellation[cancellation] = (ticket, profile)
            if on_reserved is not None:
                try:
                    position = sorted(self._pending).index(ticket) + 1
                    loading_enabled = (
                        profile.send_loading_state
                        if profile.send_loading_state is not None
                        else self._catalog.settings.send_loading_state
                    )
                    cold = not self._active_profile_ready_locked(profile)
                    on_reserved(loading_enabled and cold if apply_loading_policy else cold, position)
                except BaseException:
                    self._remove_pending_locked(ticket, cancellation)
                    self._drop_concurrency_reservation_locked(profile)
                    self._cond.notify_all()
                    raise
            while True:
                if self._shutdown_requested:
                    if self._remove_pending_locked(ticket, cancellation):
                        self._drop_concurrency_reservation_locked(profile)
                    self._cond.notify_all()
                    raise RoutingError(
                        "router_shutting_down", "router shutdown is in progress", status_code=503
                    )
                if cancellation is not None and cancellation.is_set():
                    if self._remove_pending_locked(ticket, cancellation):
                        self._drop_concurrency_reservation_locked(profile)
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
                try:
                    # Dynamic binding happens only for the head ticket. Other
                    # cold requests then reuse the committed resident target.
                    port = self._port_for(profile)
                except BaseException:
                    self._remove_pending_locked(ticket, cancellation)
                    self._drop_concurrency_reservation_locked(profile)
                    self._cond.notify_all()
                    raise
                if self._matches_active(profile, port):
                    self._cancel_idle_timer()
                    self._remove_pending_locked(ticket, cancellation)
                    self._leases += 1
                    self._admissions += 1
                    self._last_queue_wait_ms = round((time.monotonic() - queued_at) * 1000, 3)
                    state = self._manager.status()
                    self._cond.notify_all()
                    return RouteLease(
                        self,
                        profile,
                        port,
                        state.get("pid"),
                        model_id=model_id,
                        selector_id=selector_id,
                        routing_profile_id=routing_profile_id,
                        pin_id=pin_id,
                    )
                if self._leases:
                    self._cond.wait()
                    continue
                block = self._capacity_block(profile)
                if block is not None:
                    self._remove_pending_locked(ticket, cancellation)
                    self._drop_concurrency_reservation_locked(profile)
                    self._cond.notify_all()
                    raise RoutingError("capacity_unavailable", block, status_code=409)
                self._switching = True
                self._activating_name = profile.name
                self._activating_port = port
                self._remove_pending_locked(ticket, cancellation)
                break

        activated_at = time.monotonic()
        try:
            pid = self._activate(profile, port)
        except Exception as exc:
            with self._cond:
                self._switching = False
                self._activating_name = None
                self._activating_port = None
                self._activation_failures += 1
                self._drop_concurrency_reservation_locked(profile)
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
            self._activating_name = None
            self._activating_port = None
            self._switching = False
            self._cancel_idle_timer()
            self._leases += 1
            self._admissions += 1
            self._last_queue_wait_ms = round((activated_at - queued_at) * 1000, 3)
            self._last_activation_ms = round((time.monotonic() - activated_at) * 1000, 3)
            self._cond.notify_all()
        return RouteLease(
            self,
            profile,
            port,
            pid,
            model_id=model_id,
            selector_id=selector_id,
            routing_profile_id=routing_profile_id,
            pin_id=pin_id,
        )

    def cancel_acquire(self, cancellation: threading.Event) -> None:
        """Atomically retire queued ownership, then wake its admission worker."""
        with self._cond:
            cancellation.set()
            pending = self._pending_by_cancellation.get(cancellation)
            if pending is not None:
                ticket, profile = pending
                if self._remove_pending_locked(ticket, cancellation):
                    self._drop_concurrency_reservation_locked(profile)
            self._cond.notify_all()

    def queue_position(self, cancellation: threading.Event) -> int | None:
        """Return the current one-based scheduler position for a reserved request."""
        with self._cond:
            pending = self._pending_by_cancellation.get(cancellation)
            if pending is None:
                return None
            ticket, _profile = pending
            return sorted(self._pending).index(ticket) + 1

    def loading_feedback_enabled(self, name: str) -> bool:
        """Resolve the per-profile loading setting over the global default atomically."""
        with self._cond:
            try:
                _, profile, _, _, _ = self._resolve_request_locked(name)
            except CatalogError:
                # Admission owns the authoritative unknown-model response. A
                # concurrent catalog replacement must not leak an exception
                # from this optional pre-admission presentation policy.
                return False
            if profile.send_loading_state is not None:
                return profile.send_loading_state
            return self._catalog.settings.send_loading_state

    def _resolve_request_locked(
        self, name: str, *, apply_routing_profile: bool = True
    ) -> tuple[str, ModelProfile, str | None, str | None, str | None]:
        routing_profile_id = None
        pin_id = None
        if apply_routing_profile and self._active_routing_profile is not None:
            routing_profile = self._catalog.routing_profile(self._active_routing_profile)
            if routing_profile is not None:
                pinned, target = routing_profile.replacement(name)
                if pinned:
                    routing_profile_id = routing_profile.name
                    pin_id = name
                    if target is None:
                        raise CatalogError(
                            f"model ID {name!r} is disabled by routing profile {routing_profile.name!r}"
                        )
                    name = target
        selector = self._catalog.selector(name)
        if selector is None:
            return name, self._catalog.get(name), None, routing_profile_id, pin_id
        if selector.strategy == "warm":
            for target in selector.targets:
                profile = self._catalog.get(target)
                if self._active_profile_ready_locked(profile):
                    return target, profile, selector.name, routing_profile_id, pin_id
            for target in selector.targets:
                profile = self._catalog.get(target)
                if self._activating_name == profile.name:
                    return target, profile, selector.name, routing_profile_id, pin_id
        target = selector.targets[0]
        return target, self._catalog.get(target), selector.name, routing_profile_id, pin_id

    def has_routable_id(self, name: str) -> bool:
        """Whether *name* resolves under the current runtime profile snapshot."""
        with self._cond:
            try:
                self._resolve_request_locked(name)
            except CatalogError:
                return False
            return True

    def set_active_routing_profile(self, name: str | None) -> str | None:
        """Atomically activate one pin map, or clear runtime pinning with ``None``."""
        with self._cond:
            if name is not None and self._catalog.routing_profile(name) is None:
                raise RoutingError(
                    "unknown_profile", f"routing profile {name!r} not found", status_code=404
                )
            self._active_routing_profile = name
            self._cond.notify_all()
            return self._active_routing_profile

    def resolve_upstream_path(
        self, path: str
    ) -> tuple[str, str, ModelProfile, str]:
        """Apply the active profile's longest pin before concrete upstream lookup."""
        with self._cond:
            normalized = path.strip("/")
            source_id = None
            rewritten = normalized
            if self._active_routing_profile is not None:
                routing_profile = self._catalog.routing_profile(self._active_routing_profile)
                if routing_profile is not None:
                    for pin, target in routing_profile.pins:
                        if normalized == pin or normalized.startswith(pin + "/"):
                            if source_id is None or len(pin) > len(source_id):
                                source_id = pin
                                if target is None:
                                    rewritten = ""
                                else:
                                    rewritten = target + normalized[len(pin):]
            if source_id is not None and not rewritten:
                raise CatalogError(
                    f"upstream model ID {source_id!r} is disabled by the active routing profile"
                )
            routed_id, profile, remaining = self._catalog.resolve_upstream_path(rewritten)
            return source_id or routed_id, routed_id, profile, remaining

    def begin_manual_lifecycle(self, *, preempt_manual: bool = False) -> object:
        """Reserve the lifecycle barrier for one legacy engine operation."""
        with self._cond:
            if self._shutdown_requested:
                raise RoutingError(
                    "router_shutting_down", "router shutdown is in progress", status_code=503
                )
            manual_owned = self._manual_lifecycle_owner is not None
            routed_owned = bool(
                self._active_name is not None or self._leases
                or (self._pending and not manual_owned)
            )
            if (routed_owned or (self._switching and not (preempt_manual and manual_owned))):
                raise RoutingError(
                    "router_owned",
                    "router owns or is admitting an engine; use router controls or wait",
                    status_code=409,
                )
            owner = object()
            self._manual_lifecycle_tokens.add(owner)
            self._manual_lifecycle_owner = owner
            self._switching = True
            return owner

    def end_manual_lifecycle(self, owner: object) -> None:
        """Release a matching legacy lifecycle reservation."""
        with self._cond:
            if owner not in self._manual_lifecycle_tokens:
                raise ValueError("manual lifecycle reservation is not owned by caller")
            self._manual_lifecycle_tokens.remove(owner)
            if self._manual_lifecycle_owner is owner:
                self._manual_lifecycle_owner = None
                self._switching = False
            self._cond.notify_all()

    def release(self, lease: RouteLease) -> None:
        with self._cond:
            if lease.router is not self:
                raise ValueError("lease belongs to a different routing coordinator")
            if lease._released or self._leases <= 0:
                raise ValueError("routing lease was already released")
            lease._released = True
            self._leases -= 1
            self._drop_concurrency_reservation_locked(lease.profile)
            if self._leases == 0:
                self._schedule_idle_eviction()
            self._cond.notify_all()

    def status(self) -> dict:
        with self._cond:
            return self._status_locked()

    def _status_locked(self) -> dict:
        group = self._catalog.group_for(self._active_name) if self._active_name else None
        active_identity_matches = self._active_matches_engine_locked()
        return {
            "activeProfile": self._active_name,
            "activeRoutingProfile": self._active_routing_profile,
            "activatingProfile": self._activating_name,
            "activeGroup": group.name if group else None,
            "residentProfiles": [self._active_name] if active_identity_matches else [],
            "activeIdentityMatchesEngine": active_identity_matches,
            "persistent": bool(active_identity_matches and group and group.persistent),
            "capacity": {"maxResidentModels": 1, "availableResidentSlots": 0 if self._active_name else 1},
            "activeRequests": self._leases,
            "reservedRequests": self._reservations,
            "shuttingDown": self._shutdown_requested,
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
            "globalConcurrencyLimit": self._catalog.settings.global_concurrency_limit,
            "defaultProfileConcurrencyLimit": DEFAULT_PROFILE_CONCURRENCY_LIMIT,
        }

    @property
    def catalog(self) -> ModelCatalog:
        with self._cond:
            return self._catalog

    def control_plane_snapshot(self) -> tuple[ModelCatalog, dict]:
        """Return one catalog and routing-state snapshot for control responses."""
        with self._cond:
            return self._catalog, self._status_locked()

    def model_listing_snapshot(self) -> tuple[ModelCatalog, frozenset[str]]:
        """Return one atomic public-catalog and loaded/starting identity snapshot."""
        with self._cond:
            loaded: set[str] = set()
            if self._active_name is not None and self._active_matches_engine_locked():
                loaded.add(self._active_name)
            if self._activating_name is not None and self._activating_port is not None:
                profile = self._catalog.get(self._activating_name)
                if self._engine_matches(profile, self._activating_port):
                    loaded.add(self._activating_name)
            return self._catalog, frozenset(loaded)

    def public_model_listing_snapshot(
        self,
    ) -> tuple[ModelCatalog, frozenset[str], str | None]:
        """Include the active runtime pin map in the same catalog/residency snapshot."""
        with self._cond:
            loaded: set[str] = set()
            if self._active_name is not None and self._active_matches_engine_locked():
                loaded.add(self._active_name)
            if self._activating_name is not None and self._activating_port is not None:
                profile = self._catalog.get(self._activating_name)
                if self._engine_matches(profile, self._activating_port):
                    loaded.add(self._activating_name)
            return self._catalog, frozenset(loaded), self._active_routing_profile

    def active_matches_engine(self) -> bool:
        """Whether the manager still owns the exact resident routed profile.

        A listening child alone is not a readiness signal: an out-of-band or
        stale child must not make the stable router URL appear healthy for the
        alias recorded by the coordinator.
        """
        with self._cond:
            return self._active_matches_engine_locked()

    def profile_is_resident(self, model_id: str) -> bool:
        """Whether *model_id* resolves to the exact readiness-gated resident.

        This lifecycle-state query intentionally does not perform network I/O.
        It lets direct static-asset requests refuse a cold activation while
        using the same exact identity check as ordinary warm admission.
        """
        with self._cond:
            try:
                profile = self._catalog.get(model_id)
            except CatalogError:
                return False
            return (
                not self._shutdown_requested
                and not self._switching
                and self._active_profile_ready_locked(profile)
            )

    def is_ready(self, probe=None) -> bool:
        """Atomically verify resident identity and fresh engine readiness.

        Holding the admission condition across the bounded loopback probe keeps
        a conflicting swap from committing between an identity snapshot and a
        stale successful health response.
        """
        with self._cond:
            if self._shutdown_requested or self._switching or not self._active_matches_engine_locked():
                return False
            state = self._manager.status()
            port = state.get("port")
            if not isinstance(port, int) or port <= 0:
                return False
            profile = self._catalog.get(self._active_name)
            active_probe = probe or self._probe
            health = (
                active_probe.fresh_health(port)
                if profile.check_endpoint == DEFAULT_CHECK_ENDPOINT
                else active_probe.fresh_readiness(port, profile.check_endpoint)
            )
            if self._shutdown_requested or self._switching or not self._active_matches_engine_locked():
                return False
            return bool(
                health.get("reachable")
                and (
                    profile.check_endpoint != DEFAULT_CHECK_ENDPOINT
                    or (
                        health.get("status") == "ok"
                        and health.get("maintenance", "serving") == "serving"
                    )
                )
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
            if (
                self._shutdown_requested
                or self._switching
                or self._pending
                or self._manual_lifecycle_tokens
            ):
                raise RoutingError(
                    "reload_conflict",
                    "cannot reload while admission or lifecycle work is in progress",
                    status_code=409,
                )
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
            # Match the pinned runtime contract: config reload starts with no
            # active routing profile rather than silently carrying pin state
            # into a potentially different profile definition.
            self._active_routing_profile = None
            self._cond.notify_all()

    def prometheus(self) -> str:
        """Render bounded router counters without importing a metrics package."""
        status = self.status()
        values = {
            "active_requests": status["activeRequests"],
            "reserved_requests": status["reservedRequests"],
            "queued_requests": status["queuedRequests"],
            "shutting_down": int(status["shuttingDown"]),
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
            if self._shutdown_requested:
                return False
            if name is not None:
                try:
                    name = self._catalog.get(name).name
                except CatalogError:
                    return False
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

    def begin_shutdown(self) -> object:
        """Close admission immediately, before executor-side lifecycle work can queue."""
        with self._cond:
            if self._shutdown_requested:
                raise RoutingError(
                    "router_shutting_down", "router shutdown is already in progress", status_code=409
                )
            owner = object()
            self._shutdown_requested = True
            self._shutdown_owner = owner
            self._cancel_idle_timer()
            self._cond.notify_all()
            return owner

    def finish_shutdown(
        self, owner: object, timeout: float | None = None, force: bool = False
    ) -> dict:
        """Drain existing ownership and permanently stop the sole managed child."""
        return self._finish_exit(owner, lambda: self._manager.shutdown(timeout, force))

    def finish_detach(self, owner: object) -> None:
        """Drain existing ownership, then leave the child persisted for re-adoption."""
        self._finish_exit(owner, self._manager.detach)

    def _finish_exit(self, owner: object, action: Callable[[], object]):
        with self._cond:
            if self._shutdown_owner is not owner:
                raise ValueError("shutdown reservation is not owned by caller")
            while self._leases or self._switching or self._manual_lifecycle_tokens:
                self._cond.wait()
            self._switching = True
        try:
            result = action()
        except Exception:
            with self._cond:
                self._shutdown_requested = False
                self._shutdown_owner = None
                self._switching = False
                self._schedule_idle_eviction()
                self._cond.notify_all()
            raise
        with self._cond:
            self._active_name = None
            self._shutdown_owner = None
            self._switching = False
            self._cond.notify_all()
        return result

    def shutdown(self, timeout: float | None = None, force: bool = False) -> dict:
        """Synchronous convenience wrapper for a complete shutdown transaction."""
        return self.finish_shutdown(self.begin_shutdown(), timeout, force)

    def coordinated_exit(self, *, stop_child: bool) -> object | None:
        """Idempotently quiesce for an OS/lifespan exit using the configured child policy."""
        while True:
            try:
                owner = self.begin_shutdown()
                break
            except RoutingError:
                with self._cond:
                    while self._shutdown_owner is not None:
                        self._cond.wait()
                    if self._shutdown_requested:
                        return None
        if stop_child:
            return self.finish_shutdown(owner)
        return self.finish_detach(owner)

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

    def _remove_pending_locked(
        self,
        ticket: tuple[int, int, str],
        cancellation: threading.Event | None,
    ) -> bool:
        """Idempotently remove one ticket and its optional progress lookup."""
        try:
            self._pending.remove(ticket)
        except ValueError:
            removed = False
        else:
            removed = True
        pending = self._pending_by_cancellation.get(cancellation) if cancellation is not None else None
        if pending is not None and pending[0] == ticket:
            self._pending_by_cancellation.pop(cancellation, None)
        return removed

    def _active_profile_ready_locked(self, profile: ModelProfile) -> bool:
        """Whether *profile* is the exact readiness-gated resident engine."""
        if self._active_name != profile.name:
            return False
        return self._engine_matches(profile, self._port_for(profile))

    def _reserve_concurrency_locked(self, profile: ModelProfile) -> None:
        """Reserve active/queued capacity or reject immediately like the pinned scheduler."""
        global_limit = self._catalog.settings.global_concurrency_limit
        profile_limit = profile.concurrency_limit or DEFAULT_PROFILE_CONCURRENCY_LIMIT
        profile_reserved = self._profile_reservations.get(profile.name, 0)
        if (global_limit and self._reservations >= global_limit) or profile_reserved >= profile_limit:
            raise RoutingError(
                "concurrency_limit",
                f"concurrency limit reached for profile {profile.name!r}",
                status_code=429,
            )
        self._reservations += 1
        self._profile_reservations[profile.name] = profile_reserved + 1

    def _drop_concurrency_reservation_locked(self, profile: ModelProfile) -> None:
        count = self._profile_reservations.get(profile.name, 0)
        if self._reservations <= 0 or count <= 0:
            raise RuntimeError("routing concurrency reservation underflow")
        self._reservations -= 1
        if count == 1:
            self._profile_reservations.pop(profile.name)
        else:
            self._profile_reservations[profile.name] = count - 1

    def _matches_active(self, profile: ModelProfile, port: int) -> bool:
        return self._active_name == profile.name and self._engine_matches(profile, port)

    def _engine_matches(self, profile: ModelProfile, port: int) -> bool:
        state = self._manager.status()
        return bool(
            state.get("running")
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
        readiness_args = {
            "pid": result.get("pid"),
            "port": port,
            "timeout_s": profile.ready_timeout_s,
        }
        if profile.check_endpoint != DEFAULT_CHECK_ENDPOINT:
            readiness_args["path"] = profile.check_endpoint
        readiness = self._ready_fn(self._manager, self._probe, **readiness_args)
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
