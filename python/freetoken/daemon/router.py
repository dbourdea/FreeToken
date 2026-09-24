"""Native, transport-independent admission and model activation for freetoken-swap.

The router owns the decision to retain an already ready engine or to make a
safe lifecycle transition before an inference request is forwarded. It does
not implement HTTP itself: keeping this boundary small makes FIFO priority,
leases, readiness, and rollback directly testable without a model runtime.
"""
# What: document native transport independent admission and model activation in the router docstring; why: introspection and maintainers read this exact docstring fragment to understand router behavior without executing it.
# What: document the router owns the decision to in the router docstring; why: introspection and maintainers read this exact docstring fragment to understand router behavior without executing it.
# What: document safe lifecycle transition before an inference in the router docstring; why: introspection and maintainers read this exact docstring fragment to understand router behavior without executing it.
# What: document not implement http itself keeping this in the router docstring; why: introspection and maintainers read this exact docstring fragment to understand router behavior without executing it.
# What: document leases readiness and rollback directly testable in the router docstring; why: introspection and maintainers read this exact docstring fragment to understand router behavior without executing it.
# What: preserve the paragraph boundary in the the router docstring; why: introspection and maintainers read this paragraph break to understand router behavior without executing it.

# What: enable postponed evaluation of annotations; why: type hints in router can reference runtime types without eager imports or forward-reference failures.
from __future__ import annotations

# What: import socket for allocate loopback port using socket; why: allocate_loopback_port uses socket socket, making that imported dependency available to its named operation.
import socket

# What: import threading for init using threading; why: __init__ uses threading condition, making that imported dependency available to its named operation.
import threading

# What: import time for acquire using time; why: acquire uses time monotonic, making that imported dependency available to its named operation.
import time

# What: import callable for init using typing and callable; why: __init__ uses the callable annotation in init, making that imported dependency available to its named operation.
from collections.abc import Callable

# What: import dataclass and field for module initialization using dataclasses and dataclass and field; why: module initialization uses the dataclass annotation in module initialization and field, making that imported dependency available to its named operation.
from dataclasses import dataclass, field

# What: import from catalog import DEFAULT CHECK ENDPOINT CatalogError ModelCatalog ModelProfile; why: this module calls or annotates these symbols in the branch-created operations below.
from .catalog import DEFAULT_CHECK_ENDPOINT, CatalogError, ModelCatalog, ModelProfile

# What: import wait for ready for init using readiness and wait for ready; why: __init__ uses the wait for ready annotation in init, making that imported dependency available to its named operation.
from .readiness import wait_for_ready

# What: import conflict and switch launch error for acquire using serve manager and conflict and switch launch error; why: acquire uses the conflict annotation in acquire and the switch launch error annotation in acquire, making that imported dependency available to its named operation.
from .serve_manager import Conflict, SwitchLaunchError

# What: compute default profile concurrency limit from 10; why: default profile concurrency limit default profile concurrency limit later reads default profile concurrency limit, so router must retain the computed value under that name.
DEFAULT_PROFILE_CONCURRENCY_LIMIT = 10


# What: define allocate_loopback_port around the current object state; why: its direct callers call allocate_loopback_port for allocate loopback port and rely on this exact input and result contract.
def allocate_loopback_port() -> int:
    """Ask the kernel for an ephemeral loopback TCP port pair.

    The listener is intentionally closed before the child starts: FreeToken's
    serve process, not the daemon, must own the listening socket. The manager
    serializes the immediately following launch. FreeToken also reserves the
    next port for its local distributed store, so both adjacent ports must be
    available. A local process can still win the unavoidable post-check bind
    race, in which case readiness fails closed and rollback applies.
    """
    # What: document ask the kernel for an ephemeral in the allocate_loopback_port docstring; why: introspection and maintainers read this exact docstring fragment to understand allocate loopback port behavior without executing it.
    # What: document the listener is intentionally closed before in the allocate_loopback_port docstring; why: introspection and maintainers read this exact docstring fragment to understand allocate loopback port behavior without executing it.
    # What: document serve process not the daemon must in the allocate_loopback_port docstring; why: introspection and maintainers read this exact docstring fragment to understand allocate loopback port behavior without executing it.
    # What: document serializes the immediately following launch a in the allocate_loopback_port docstring; why: introspection and maintainers read this exact docstring fragment to understand allocate loopback port behavior without executing it.
    # What: document process can still win that unavoidable in the allocate_loopback_port docstring; why: introspection and maintainers read this exact docstring fragment to understand allocate loopback port behavior without executing it.
    # What: document fails closed and the normal rollback in the allocate_loopback_port docstring; why: introspection and maintainers read this exact docstring fragment to understand allocate loopback port behavior without executing it.
    # What: preserve the paragraph boundary in the the allocate_loopback_port docstring; why: introspection and maintainers read this paragraph break to understand allocate loopback port behavior without executing it.
    # What: bound ephemeral-pair selection attempts; why: repeated adjacent-port conflicts must fail instead of looping forever.
    for _ in range(64):
        # What: reserve a kernel-selected candidate service port during validation; why: concurrent allocators cannot take the base port before its companion is checked.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as service_sock:
            # What: forbid address reuse on the candidate service socket; why: the availability check must reflect an exclusive future listener.
            service_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            # What: ask the kernel for a loopback candidate; why: hard-coded ports would collide across parallel daemon instances.
            service_sock.bind(("127.0.0.1", 0))
            # What: retain the selected service port; why: its adjacent distributed-store port must be validated before launch.
            port = int(service_sock.getsockname()[1])
            # What: skip a terminal port with no valid successor; why: FreeToken cannot bind a distributed store above TCP port 65535.
            if port >= 65535:
                # What: retry with another kernel-selected port; why: only a complete adjacent pair is usable.
                continue
            # What: attempt to reserve the adjacent distributed-store port; why: FreeToken initializes its local process group on service port plus one.
            try:
                # What: hold the companion listener during validation; why: both required ports must be simultaneously available.
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as distributed_sock:
                    # What: forbid address reuse on the companion socket; why: an existing listener must be detected as a conflict.
                    distributed_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
                    # What: bind the exact companion port; why: a free base port alone previously produced EADDRINUSE during model switching.
                    distributed_sock.bind(("127.0.0.1", port + 1))
            # What: retry when the companion port is already occupied; why: the child would otherwise fail after an expensive model switch.
            except OSError:
                # What: continue bounded pair selection; why: another candidate may have both required listeners free.
                continue
            # What: return the validated base port after both temporary reservations close; why: the FreeToken child must own both real listeners.
            return port
    # What: fail after exhausting bounded pair-selection attempts; why: launching without a proven port pair would create a predictable lifecycle failure.
    raise OSError("could not allocate adjacent loopback ports for FreeToken serve")


# What: define RoutingError as the owner of __init__; why: daemon callers use this class boundary so those methods share one routing error state invariant.
class RoutingError(RuntimeError):
    """A request could not be admitted to a ready native engine."""
# What: document a request could not be admitted in the RoutingError docstring; why: introspection and maintainers read this exact docstring fragment to understand routing error behavior without executing it.

    # What: define __init__ around code and detail and status code and recovery; why: its direct callers call __init__ for init and rely on this exact input and result contract.
    def __init__(self, code: str, detail: str, *, status_code: int = 503, recovery: dict | None = None):
        # What: call operation.__init__ with detail; why: __init__ invokes operation.__init__ while performing self code code; the call advances that operation through its result or side effect.
        super().__init__(detail)
        # What: compute code from code; why: the enclosing return or state update later reads code, so __init__ must retain the computed value under that name.
        self.code = code
        # What: compute status code from status code; why: the enclosing return or state update later reads status code, so __init__ must retain the computed value under that name.
        self.status_code = status_code
        # What: compute recovery from recovery; why: the enclosing return or state update later reads recovery, so __init__ must retain the computed value under that name.
        self.recovery = recovery


# What: generate dataclass initialization and value semantics for RouteLease; why: RouteLease acts as a typed state record with consistent construction, comparison, and representation.
@dataclass
# What: define RouteLease as the owner of release and proxy_base_url; why: daemon callers use this class boundary so those methods share one route lease state invariant.
class RouteLease:
    """One admitted request. Call :meth:`release` exactly once when it ends."""
# What: document one admitted request call meth release in the RouteLease docstring; why: introspection and maintainers read this exact docstring fragment to understand route lease behavior without executing it.

    # What: compute router from the named fixture input; why: self router release later reads router, so router must retain the computed value under that name.
    router: RoutingCoordinator
    # What: compute profile from the named fixture input; why: return self profile proxy base url self port later reads profile, so router must retain the computed value under that name.
    profile: ModelProfile
    # What: compute port from the named fixture input; why: return self profile proxy base url self port later reads port, so router must retain the computed value under that name.
    port: int
    # What: compute pid from the named fixture input; why: state get pid later reads pid, so router must retain the computed value under that name.
    pid: int | None
    # What: compute model id from the named fixture input; why: model id profile selector id routing profile id pin id later reads model id, so router must retain the computed value under that name.
    model_id: str | None = None
    # What: compute selector id from the named fixture input; why: model id profile selector id routing profile id pin id later reads selector id, so router must retain the computed value under that name.
    selector_id: str | None = None
    # What: compute routing profile id from the named fixture input; why: model id profile selector id routing profile id pin id later reads routing profile id, so router must retain the computed value under that name.
    routing_profile_id: str | None = None
    # What: compute pin id from the named fixture input; why: model id profile selector id routing profile id pin id later reads pin id, so router must retain the computed value under that name.
    pin_id: str | None = None
    # What: compute released from field and false and false and false; why: if lease released or self leases later reads released, so router must retain the computed value under that name.
    _released: bool = field(default=False, init=False, repr=False)

    # What: define release around the current object state; why: its direct callers call release for release and rely on this exact input and result contract.
    def release(self) -> None:
        # What: call self.router.release with the named fixture input; why: release invokes self.router.release while performing the enclosing return; the call advances that operation through its result or side effect.
        self.router.release(self)

    # What: expose proxy_base_url as a read-only computed property; why: callers read proxy_base_url through attribute access while its getter retains control of the derived value.
    @property
    # What: define proxy_base_url around the current object state; why: the registered API client call proxy_base_url for proxy base url and rely on this exact input and result contract.
    def proxy_base_url(self) -> str:
        # What: return proxy base url and port and profile from proxy_base_url; why: proxy_base_url exposes proxy base url and port and profile so its caller can continue with the function\'s computed outcome.
        return self.profile.proxy_base_url(self.port)


# What: define RoutingCoordinator as the owner of __init__ and _adopt_exact_catalog_resident and acquire and cancel_acquire and queue_position; why: daemon callers use this class boundary so those methods share one routing coordinator state invariant.
class RoutingCoordinator:
    """Serialize unsafe swaps while allowing concurrent requests for one engine.

    A higher profile priority wins over lower priority requests that have not
    begun an activation. Equal priorities use strict FIFO ordering. A swap is
    never started while an admitted lease exists, which preserves streaming
    requests and their cancellation semantics.
    """
# What: document serialize unsafe swaps while allowing concurrent in the RoutingCoordinator docstring; why: introspection and maintainers read this exact docstring fragment to understand routing coordinator behavior without executing it.
# What: document a higher profile priority wins over in the RoutingCoordinator docstring; why: introspection and maintainers read this exact docstring fragment to understand routing coordinator behavior without executing it.
# What: document begun an activation equal priorities use in the RoutingCoordinator docstring; why: introspection and maintainers read this exact docstring fragment to understand routing coordinator behavior without executing it.
# What: document never started while an admitted lease in the RoutingCoordinator docstring; why: introspection and maintainers read this exact docstring fragment to understand routing coordinator behavior without executing it.
# What: document requests and their cancellation semantics in the RoutingCoordinator docstring; why: introspection and maintainers read this exact docstring fragment to understand routing coordinator behavior without executing it.
# What: preserve the paragraph boundary in the the RoutingCoordinator docstring; why: introspection and maintainers read this paragraph break to understand routing coordinator behavior without executing it.

    # What: define __init__ around manager and catalog and probe and default port and ready fn and timer factory and port allocator; why: its direct callers call __init__ for init and rely on this exact input and result contract.
    def __init__(
        # What: declare the self input for __init__; why: __init__ consumes self during self manager manager, so callers must bind it with the other signature inputs.
        self,
        # What: declare the manager input for __init__; why: __init__ consumes manager during self manager manager, so callers must bind it with the other signature inputs.
        manager,
        # What: declare the catalog input for __init__; why: __init__ consumes catalog during self catalog catalog, so callers must bind it with the other signature inputs.
        catalog: ModelCatalog,
        # What: declare the probe input for __init__; why: __init__ consumes probe during self probe probe, so callers must bind it with the other signature inputs.
        probe,
        # What: mark the remaining parameters as keyword-only; why: __init__ prevents callers from confusing adjacent lifecycle and timing arguments.
        *,
        # What: declare the default port input for __init__; why: __init__ consumes default port during self default port default port, so callers must bind it with the other signature inputs.
        default_port: int = 1919,
        # What: declare the ready fn input for __init__; why: __init__ consumes ready fn during self ready fn ready fn, so callers must bind it with the other signature inputs.
        ready_fn: Callable = wait_for_ready,
        # What: declare the timer factory input for __init__; why: __init__ consumes timer factory during self timer factory timer factory or self new timer, so callers must bind it with the other signature inputs.
        timer_factory: Callable[[float, Callable[[], None]], object] | None = None,
        # What: declare the port allocator input for __init__; why: __init__ consumes port allocator during self port allocator port allocator, so callers must bind it with the other signature inputs.
        port_allocator: Callable[[], int] = allocate_loopback_port,
    # What: complete the enclosing predicate with group delimiter; why: RoutingCoordinator.__init__ groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ) -> None:
        # What: compute manager from manager; why: the enclosing return or state update later reads manager, so __init__ must retain the computed value under that name.
        self._manager = manager
        # What: compute catalog from catalog; why: the enclosing return or state update later reads catalog, so __init__ must retain the computed value under that name.
        self._catalog = catalog
        # What: compute probe from probe; why: the enclosing return or state update later reads probe, so __init__ must retain the computed value under that name.
        self._probe = probe
        # What: compute default port from default port; why: the enclosing return or state update later reads default port, so __init__ must retain the computed value under that name.
        self._default_port = default_port
        # What: compute ready fn from ready fn; why: the enclosing return or state update later reads ready fn, so __init__ must retain the computed value under that name.
        self._ready_fn = ready_fn
        # What: compute timer factory from timer factory and new timer; why: the enclosing return or state update later reads timer factory, so __init__ must retain the computed value under that name.
        self._timer_factory = timer_factory or self._new_timer
        # What: compute port allocator from port allocator; why: the enclosing return or state update later reads port allocator, so __init__ must retain the computed value under that name.
        self._port_allocator = port_allocator
        # What: compute cond from condition and threading and lock; why: the enclosing return or state update later reads cond, so __init__ must retain the computed value under that name.
        self._cond = threading.Condition(threading.Lock())
        # What: compute next sequence from 0; why: the enclosing return or state update later reads next sequence, so __init__ must retain the computed value under that name.
        self._next_sequence = 0
        # What: initialize pending as an empty runtime accumulator; why: RoutingCoordinator.__init__ appends or maps entries into it during the enclosing return or state update before consuming the aggregate.
        self._pending: list[tuple[int, int, str]] = []
        # What: initialize pending by cancellation as an empty runtime accumulator; why: RoutingCoordinator.__init__ appends or maps entries into it during the enclosing return or state update before consuming the aggregate.
        self._pending_by_cancellation: dict[
            # What: apply the threading event tuple tuple int int str portion of pending by cancellation; why: __init__ uses this clause to evaluate pending by cancellation as one grouped value.
            threading.Event, tuple[tuple[int, int, str], ModelProfile]
        # What: apply the grouped expression portion of pending by cancellation; why: __init__ uses this clause to evaluate pending by cancellation as one grouped value.
        ] = {}
        # What: compute leases from 0; why: the enclosing return or state update later reads leases, so __init__ must retain the computed value under that name.
        self._leases = 0
        # What: compute reservations from 0; why: the enclosing return or state update later reads reservations, so __init__ must retain the computed value under that name.
        self._reservations = 0
        # What: initialize profile reservations as an empty runtime accumulator; why: RoutingCoordinator.__init__ appends or maps entries into it during the enclosing return or state update before consuming the aggregate.
        self._profile_reservations: dict[str, int] = {}
        # What: compute active name from the named fixture input; why: the enclosing return or state update later reads active name, so __init__ must retain the computed value under that name.
        self._active_name: str | None = None
        # What: compute active routing profile from the named fixture input; why: the enclosing return or state update later reads active routing profile, so __init__ must retain the computed value under that name.
        self._active_routing_profile: str | None = None
        # What: compute activating name from the named fixture input; why: the enclosing return or state update later reads activating name, so __init__ must retain the computed value under that name.
        self._activating_name: str | None = None
        # What: compute activating port from the named fixture input; why: the enclosing return or state update later reads activating port, so __init__ must retain the computed value under that name.
        self._activating_port: int | None = None
        # What: compute switching from false; why: the enclosing return or state update later reads switching, so __init__ must retain the computed value under that name.
        self._switching = False
        # What: compute manual lifecycle owner from the named fixture input; why: the enclosing return or state update later reads manual lifecycle owner, so __init__ must retain the computed value under that name.
        self._manual_lifecycle_owner: object | None = None
        # What: compute manual lifecycle tokens from set; why: the enclosing return or state update later reads manual lifecycle tokens, so __init__ must retain the computed value under that name.
        self._manual_lifecycle_tokens: set[object] = set()
        # What: compute shutdown requested from false; why: the enclosing return or state update later reads shutdown requested, so __init__ must retain the computed value under that name.
        self._shutdown_requested = False
        # What: compute shutdown owner from the named fixture input; why: the enclosing return or state update later reads shutdown owner, so __init__ must retain the computed value under that name.
        self._shutdown_owner: object | None = None
        # What: compute idle timer from the named fixture input; why: the enclosing return or state update later reads idle timer, so __init__ must retain the computed value under that name.
        self._idle_timer: object | None = None
        # What: compute evictions from 0; why: the enclosing return or state update later reads evictions, so __init__ must retain the computed value under that name.
        self._evictions = 0
        # What: compute admissions from 0; why: the enclosing return or state update later reads admissions, so __init__ must retain the computed value under that name.
        self._admissions = 0
        # What: compute activations from 0; why: the enclosing return or state update later reads activations, so __init__ must retain the computed value under that name.
        self._activations = 0
        # What: compute activation failures from 0; why: the enclosing return or state update later reads activation failures, so __init__ must retain the computed value under that name.
        self._activation_failures = 0
        # What: compute cancellations from 0; why: the enclosing return or state update later reads cancellations, so __init__ must retain the computed value under that name.
        self._cancellations = 0
        # What: compute terminal streams from 0; why: the enclosing return or state update later reads terminal streams, so __init__ must retain the computed value under that name.
        self._terminal_streams = 0
        # What: compute last ttft ms from the named fixture input; why: the enclosing return or state update later reads last ttft ms, so __init__ must retain the computed value under that name.
        self._last_ttft_ms: float | None = None
        # What: compute last duration ms from the named fixture input; why: the enclosing return or state update later reads last duration ms, so __init__ must retain the computed value under that name.
        self._last_duration_ms: float | None = None
        # What: compute last activation ms from the named fixture input; why: the enclosing return or state update later reads last activation ms, so __init__ must retain the computed value under that name.
        self._last_activation_ms: float | None = None
        # What: compute last queue wait ms from the named fixture input; why: the enclosing return or state update later reads last queue wait ms, so __init__ must retain the computed value under that name.
        self._last_queue_wait_ms: float | None = None
        # What: compute last response bytes from the named fixture input; why: the enclosing return or state update later reads last response bytes, so __init__ must retain the computed value under that name.
        self._last_response_bytes: int | None = None
        # What: compute last proxy bytes per second from the named fixture input; why: the enclosing return or state update later reads last proxy bytes per second, so __init__ must retain the computed value under that name.
        self._last_proxy_bytes_per_second: float | None = None
        # What: call self._adopt_exact_catalog_resident with the declared inputs; why: __init__ invokes self._adopt_exact_catalog_resident while performing the enclosing return; the call advances that operation through its result or side effect.
        self._adopt_exact_catalog_resident()

    # What: define _adopt_exact_catalog_resident around the current object state; why: its direct callers call _adopt_exact_catalog_resident for adopt exact catalog resident and rely on this exact input and result contract.
    def _adopt_exact_catalog_resident(self) -> None:
        """Bind one unambiguous catalog profile to a manager-re-adopted engine.

        Omitted ports match the configured default and dynamic-port profiles
        match the concrete persisted port. If multiple profiles describe the
        same process identity, fail closed rather than inventing which one owns
        residency.
        """
        # What: document bind one unambiguous catalog profile to in the _adopt_exact_catalog_resident docstring; why: introspection and maintainers read this exact docstring fragment to understand adopt exact catalog resident behavior without executing it.
        # What: document omitted ports match the configured default in the _adopt_exact_catalog_resident docstring; why: introspection and maintainers read this exact docstring fragment to understand adopt exact catalog resident behavior without executing it.
        # What: document match the concrete persisted port if in the _adopt_exact_catalog_resident docstring; why: introspection and maintainers read this exact docstring fragment to understand adopt exact catalog resident behavior without executing it.
        # What: document same process identity fail closed rather in the _adopt_exact_catalog_resident docstring; why: introspection and maintainers read this exact docstring fragment to understand adopt exact catalog resident behavior without executing it.
        # What: document residency in the _adopt_exact_catalog_resident docstring; why: introspection and maintainers read this exact docstring fragment to understand adopt exact catalog resident behavior without executing it.
        # What: preserve the paragraph boundary in the the _adopt_exact_catalog_resident docstring; why: introspection and maintainers read this paragraph break to understand adopt exact catalog resident behavior without executing it.
        # What: compute state from status and manager; why: port state get port later reads state, so _adopt_exact_catalog_resident must retain the computed value under that name.
        state = self._manager.status()
        # What: compute port from get and state and port; why: if not state get running or not later reads port, so _adopt_exact_catalog_resident must retain the computed value under that name.
        port = state.get("port")
        # What: gate on port and get and isinstance and int and state before the computed value; why: _adopt_exact_catalog_resident admits the computed value only for this predicate and excludes the opposite state.
        if not state.get("running") or not isinstance(port, int) or port <= 0:
            # What: return no value from _adopt_exact_catalog_resident; why: _adopt_exact_catalog_resident returns no value to callers that depend on its completed result.
            return
        # What: compute args from serve args and manager; why: and list profile args args later reads args, so _adopt_exact_catalog_resident must retain the computed value under that name.
        args = self._manager.serve_args()
        # What: compute matches from profile and profiles and catalog and model; why: if len matches later reads matches, so _adopt_exact_catalog_resident must retain the computed value under that name.
        matches = [
            # What: call self._catalog.profiles with the declared inputs; why: _adopt_exact_catalog_resident invokes self._catalog.profiles while performing if profile model state get model; the call advances that operation through its result or side effect.
            profile for profile in self._catalog.profiles()
            # What: call state.get with model; why: _adopt_exact_catalog_resident invokes state.get while performing and; the call advances that operation through its result or side effect.
            if profile.model == state.get("model")
            # What: apply the and portion of matches; why: _adopt_exact_catalog_resident uses this clause to evaluate matches as one grouped value.
            and (
                # What: apply the profile port port portion of matches; why: _adopt_exact_catalog_resident uses this clause to evaluate matches as one grouped value.
                profile.port == port
                # What: apply the or profile port portion of matches; why: _adopt_exact_catalog_resident uses this clause to evaluate matches as one grouped value.
                or profile.port == 0
                # What: apply the or profile port is and port self default port portion of matches; why: _adopt_exact_catalog_resident uses this clause to evaluate matches as one grouped value.
                or (profile.port is None and port == self._default_port)
            # What: complete the matches expression with profile model equals state get model and profile port equals port or; why: RoutingCoordinator._adopt_exact_catalog_resident groups the supplied clauses as one matches expression before its value is consumed.
            )
            # What: call list with args and profile; why: _adopt_exact_catalog_resident consumes the list return value while evaluating and list(profile.args) == args.
            and list(profile.args) == args
        # What: complete the matches expression with matches profile for profile in self catalog profiles if profile model equals; why: RoutingCoordinator._adopt_exact_catalog_resident groups the supplied clauses as one matches expression before its value is consumed.
        ]
        # What: gate on len and matches before the computed value; why: _adopt_exact_catalog_resident admits the computed value only for this predicate and excludes the opposite state.
        if len(matches) != 1:
            # What: return no value from _adopt_exact_catalog_resident; why: _adopt_exact_catalog_resident returns no value to callers that depend on its completed result.
            return
        # What: compute active name from name and matches and 0; why: the enclosing return or state update later reads active name, so _adopt_exact_catalog_resident must retain the computed value under that name.
        self._active_name = matches[0].name
        # What: call self._schedule_idle_eviction with the declared inputs; why: _adopt_exact_catalog_resident invokes self._schedule_idle_eviction while performing the enclosing return; the call advances that operation through its result or side effect.
        self._schedule_idle_eviction()

    # What: define acquire around name and cancellation and on reserved and apply loading policy and apply routing profile; why: its direct callers call acquire for acquire and rely on this exact input and result contract.
    def acquire(
        # What: declare the self input for acquire; why: acquire consumes self while evaluating self, so callers must bind it with the other signature inputs.
        self,
        # What: declare the name input for acquire; why: acquire consumes name during name apply routing profile apply routing profile, so callers must bind it with the other signature inputs.
        name: str,
        # What: declare the cancellation input for acquire; why: acquire consumes cancellation during if cancellation is not, so callers must bind it with the other signature inputs.
        cancellation: threading.Event | None = None,
        # What: declare the on reserved input for acquire; why: acquire consumes on reserved during if on reserved is not, so callers must bind it with the other signature inputs.
        on_reserved: Callable[[bool, int], None] | None = None,
        # What: mark the remaining parameters as keyword-only; why: acquire prevents callers from confusing adjacent lifecycle and timing arguments.
        *,
        # What: declare the apply loading policy input for acquire; why: acquire consumes apply loading policy during on reserved loading enabled and cold if apply loading policy, so callers must bind it with the other signature inputs.
        apply_loading_policy: bool = False,
        # What: declare the apply routing profile input for acquire; why: acquire consumes apply routing profile during name apply routing profile apply routing profile, so callers must bind it with the other signature inputs.
        apply_routing_profile: bool = True,
    # What: complete the enclosing predicate with route lease; why: RoutingCoordinator.acquire groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ) -> RouteLease:
        """Return a lease only after *name* has a health-verified engine."""
        # What: document return a lease only after name in the acquire docstring; why: introspection and maintainers read this exact docstring fragment to understand acquire behavior without executing it.
        # What: compute queued at from monotonic and time; why: self last queue wait ms round time monotonic queued at later reads queued at, so acquire must retain the computed value under that name.
        queued_at = time.monotonic()
        # What: enter the cond managed context before if self shutdown requested; why: acquire releases this resource or lock after if self shutdown requested on both success and failure paths.
        with self._cond:
            # What: gate on shutdown requested before routing error; why: acquire admits routing error only for this predicate and excludes the opposite state.
            if self._shutdown_requested:
                # What: raise RoutingError for the caller; why:  RoutingCoordinator.acquire stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RoutingError(
                    # What: supply status code to RoutingError; why: acquire binds this 503 value to RoutingError's status code input.
                    "router_shutting_down", "router shutdown is in progress", status_code=503
                # What: complete the RoutingError call with status code; why: RoutingCoordinator.acquire groups the supplied clauses as one RoutingError call before its value is consumed.
                )
            # What: establish the handler boundary for the protected operation; why: RoutingCoordinator.acquire routes failures to catalog error while preserving cleanup and success flow.
            try:
                # What: evaluate and capture model id profile selector id routing profile id pin id; why: the enclosing qualifier uses the captured result in its next validation or artifact step.
                model_id, profile, selector_id, routing_profile_id, pin_id = (
                    # What: call self._resolve_request_locked with name; why: acquire invokes self._resolve_request_locked while performing name apply routing profile apply routing profile; the call advances that operation through its result or side effect.
                    self._resolve_request_locked(
                        # What: supply apply routing profile to self._resolve_request_locked; why: acquire binds this apply routing profile value to self._resolve_request_locked's apply routing profile input.
                        name, apply_routing_profile=apply_routing_profile
                    # What: complete the self._resolve_request_locked call with apply routing profile; why: RoutingCoordinator.acquire groups the supplied clauses as one self._resolve_request_locked call before its value is consumed.
                    )
                # What: execute the grouped source fragment; why:  the enclosing symbol requires this operation for its concrete qualification or routing path.
                )
            # What: handle catalog error by raise routing error unknown model str exc status code 404; why: RoutingCoordinator.acquire converts that failure into this concrete recovery, response, or cleanup behavior.
            except CatalogError as exc:
                # What: raise RoutingError for the caller; why:  RoutingCoordinator.acquire stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RoutingError("unknown_model", str(exc), status_code=404) from exc
            # What: gate on cancellation and is set before routing error; why: acquire admits routing error only for this predicate and excludes the opposite state.
            if cancellation is not None and cancellation.is_set():
                # What: raise RoutingError for the caller; why:  RoutingCoordinator.acquire stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RoutingError(
                    # What: supply status code to RoutingError; why: acquire binds this 409 value to RoutingError's status code input.
                    "request_cancelled", "request cancelled before admission", status_code=409
                # What: complete the RoutingError call with status code; why: RoutingCoordinator.acquire groups the supplied clauses as one RoutingError call before its value is consumed.
                )
            # What: call self._reserve_concurrency_locked with profile; why: acquire invokes self._reserve_concurrency_locked while performing ticket profile priority self next sequence profile name; the call advances that operation through its result or side effect.
            self._reserve_concurrency_locked(profile)
            # What: compute ticket from next sequence and name and priority and profile; why: self pending append ticket later reads ticket, so acquire must retain the computed value under that name.
            ticket = (-profile.priority, self._next_sequence, profile.name)
            # What: compute next sequence from 1; why: the enclosing return or state update later reads next sequence, so acquire must retain the computed value under that name.
            self._next_sequence += 1
            # What: call self._pending.append with ticket; why: acquire invokes self._pending.append while performing if cancellation is not; the call advances that operation through its result or side effect.
            self._pending.append(ticket)
            # What: gate on cancellation before pending by cancellation and cancellation and ticket and profile; why: acquire admits pending by cancellation and cancellation and ticket and profile only for this predicate and excludes the opposite state.
            if cancellation is not None:
                # What: compute pending by cancellation entry from ticket and profile; why: the enclosing return or state update later reads pending by cancellation entry, so acquire must retain the computed value under that name.
                self._pending_by_cancellation[cancellation] = (ticket, profile)
            # What: gate on on reserved before position and loading enabled and cold and base exception and send loading state; why: acquire admits position and loading enabled and cold and base exception and send loading state only for this predicate and excludes the opposite state.
            if on_reserved is not None:
                # What: establish the handler boundary for the protected operation; why: RoutingCoordinator.acquire routes failures to base exception while preserving cleanup and success flow.
                try:
                    # What: compute position from index and ticket and sorted and pending and 1; why: on reserved loading enabled and cold if apply loading policy later reads position, so acquire must retain the computed value under that name.
                    position = sorted(self._pending).index(ticket) + 1
                    # What: compute loading enabled from send loading state and profile and settings and catalog; why: on reserved loading enabled and cold if apply loading policy later reads loading enabled, so acquire must retain the computed value under that name.
                    loading_enabled = (
                        # What: apply the profile send loading state portion of loading enabled; why: acquire uses this clause to evaluate loading enabled as one grouped value.
                        profile.send_loading_state
                        # What: apply the if profile send loading state is not portion of loading enabled; why: acquire uses this clause to evaluate loading enabled as one grouped value.
                        if profile.send_loading_state is not None
                        # What: apply the else self catalog settings send loading state portion of loading enabled; why: acquire uses this clause to evaluate loading enabled as one grouped value.
                        else self._catalog.settings.send_loading_state
                    # What: execute the grouped source fragment; why:  the enclosing symbol requires this operation for its concrete qualification or routing path.
                    )
                    # What: compute cold from active profile ready locked and profile; why: on reserved loading enabled and cold if apply loading policy later reads cold, so acquire must retain the computed value under that name.
                    cold = not self._active_profile_ready_locked(profile)
                    # What: call on_reserved with apply loading policy and cold and loading enabled and position; why: acquire invokes on_reserved while performing except base exception; the call advances that operation through its result or side effect.
                    on_reserved(loading_enabled and cold if apply_loading_policy else cold, position)
                # What: handle base exception by self remove pending locked ticket cancellation; why: RoutingCoordinator.acquire converts that failure into this concrete recovery, response, or cleanup behavior.
                except BaseException:
                    # What: call self._remove_pending_locked with ticket and cancellation; why: acquire invokes self._remove_pending_locked while performing self drop concurrency reservation locked profile; the call advances that operation through its result or side effect.
                    self._remove_pending_locked(ticket, cancellation)
                    # What: call self._drop_concurrency_reservation_locked with profile; why: acquire invokes self._drop_concurrency_reservation_locked while performing self cond notify all; the call advances that operation through its result or side effect.
                    self._drop_concurrency_reservation_locked(profile)
                    # What: call self._cond.notify_all with the declared inputs; why: acquire invokes self._cond.notify_all while performing raise; the call advances that operation through its result or side effect.
                    self._cond.notify_all()
                    # What: re-propagate the active failure to the caller; why: RoutingCoordinator.acquire stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise
            # What: iterate across the computed value to perform shutdown requested and remove pending locked and ticket and cancellation and notify all; why: acquire repeats the body only while or for the loop header admits an iteration.
            while True:
                # What: execute if self  shutdown requested; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
                if self._shutdown_requested:
                    # What: gate on remove pending locked and ticket and cancellation before drop concurrency reservation locked and profile; why: acquire admits drop concurrency reservation locked and profile only for this predicate and excludes the opposite state.
                    if self._remove_pending_locked(ticket, cancellation):
                        # What: call self._drop_concurrency_reservation_locked with profile; why: acquire invokes self._drop_concurrency_reservation_locked while performing self cond notify all; the call advances that operation through its result or side effect.
                        self._drop_concurrency_reservation_locked(profile)
                    # What: call self._cond.notify_all with the declared inputs; why: acquire invokes self._cond.notify_all while performing raise routing error; the call advances that operation through its result or side effect.
                    self._cond.notify_all()
                    # What: raise RoutingError for the caller; why:  RoutingCoordinator.acquire stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise RoutingError(
                        # What: supply status code to RoutingError; why: acquire binds this 503 value to RoutingError's status code input.
                        "router_shutting_down", "router shutdown is in progress", status_code=503
                    # What: complete the RoutingError call with status code; why: RoutingCoordinator.acquire groups the supplied clauses as one RoutingError call before its value is consumed.
                    )
                # What: execute if cancellation is not None and cancellation is set; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
                if cancellation is not None and cancellation.is_set():
                    # What: gate on remove pending locked and ticket and cancellation before drop concurrency reservation locked and profile; why: acquire admits drop concurrency reservation locked and profile only for this predicate and excludes the opposite state.
                    if self._remove_pending_locked(ticket, cancellation):
                        # What: call self._drop_concurrency_reservation_locked with profile; why: acquire invokes self._drop_concurrency_reservation_locked while performing self cond notify all; the call advances that operation through its result or side effect.
                        self._drop_concurrency_reservation_locked(profile)
                    # What: call self._cond.notify_all with the declared inputs; why: acquire invokes self._cond.notify_all while performing raise routing error; the call advances that operation through its result or side effect.
                    self._cond.notify_all()
                    # What: raise RoutingError for the caller; why:  RoutingCoordinator.acquire stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise RoutingError(
                        # What: supply status code to RoutingError; why: acquire binds this 409 value to RoutingError's status code input.
                        "request_cancelled", "request cancelled before admission", status_code=409
                    # What: complete the RoutingError call with status code; why: RoutingCoordinator.acquire groups the supplied clauses as one RoutingError call before its value is consumed.
                    )
                # What: compute head from min and pending; why: if ticket head later reads head, so acquire must retain the computed value under that name.
                head = min(self._pending)
                # What: gate on ticket and head before wait and cond; why: acquire admits wait and cond only for this predicate and excludes the opposite state.
                if ticket != head:
                    # What: call self._cond.wait with the declared inputs; why: acquire invokes self._cond.wait while performing continue; the call advances that operation through its result or side effect.
                    self._cond.wait()
                    # What: apply the continue portion of the enclosing predicate; why: this clause remains in acquire\'s enclosing expression so its grouping and evaluation order stay intact.
                    continue
                # What: gate on switching before wait and cond; why: acquire admits wait and cond only for this predicate and excludes the opposite state.
                if self._switching:
                    # What: call self._cond.wait with the declared inputs; why: acquire invokes self._cond.wait while performing continue; the call advances that operation through its result or side effect.
                    self._cond.wait()
                    # What: apply the continue portion of the enclosing predicate; why: this clause remains in acquire\'s enclosing expression so its grouping and evaluation order stay intact.
                    continue
                # What: establish the handler boundary for the protected operation; why: RoutingCoordinator.acquire routes failures to base exception while preserving cleanup and success flow.
                try:
                    # Dynamic binding happens only for the head ticket. Other
                    # cold requests then reuse the committed resident target.
                    # What: compute port from port for and profile; why: if self matches active profile port later reads port, so acquire must retain the computed value under that name.
                    port = self._port_for(profile)
                # What: handle base exception by self remove pending locked ticket cancellation; why: RoutingCoordinator.acquire converts that failure into this concrete recovery, response, or cleanup behavior.
                except BaseException:
                    # What: call self._remove_pending_locked with ticket and cancellation; why: acquire invokes self._remove_pending_locked while performing self drop concurrency reservation locked profile; the call advances that operation through its result or side effect.
                    self._remove_pending_locked(ticket, cancellation)
                    # What: call self._drop_concurrency_reservation_locked with profile; why: acquire invokes self._drop_concurrency_reservation_locked while performing self cond notify all; the call advances that operation through its result or side effect.
                    self._drop_concurrency_reservation_locked(profile)
                    # What: call self._cond.notify_all with the declared inputs; why: acquire invokes self._cond.notify_all while performing raise; the call advances that operation through its result or side effect.
                    self._cond.notify_all()
                    # What: re-propagate the active failure to the caller; why: RoutingCoordinator.acquire stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise
                # What: gate on matches active and profile and port before cancel idle timer; why: acquire admits cancel idle timer only for this predicate and excludes the opposite state.
                if self._matches_active(profile, port):
                    # What: call self._cancel_idle_timer with the declared inputs; why: acquire invokes self._cancel_idle_timer while performing self remove pending locked ticket cancellation; the call advances that operation through its result or side effect.
                    self._cancel_idle_timer()
                    # What: call self._remove_pending_locked with ticket and cancellation; why: acquire invokes self._remove_pending_locked while performing self leases; the call advances that operation through its result or side effect.
                    self._remove_pending_locked(ticket, cancellation)
                    # What: compute leases from 1; why: if self leases later reads leases, so acquire must retain the computed value under that name.
                    self._leases += 1
                    # What: compute admissions from 1; why: self admissions later reads admissions, so acquire must retain the computed value under that name.
                    self._admissions += 1
                    # What: compute last queue wait ms from round and queued at and monotonic and time and 3; why: self last queue wait ms round activated at queued at later reads last queue wait ms, so acquire must retain the computed value under that name.
                    self._last_queue_wait_ms = round((time.monotonic() - queued_at) * 1000, 3)
                    # What: compute state from status and manager; why: state get pid later reads state, so acquire must retain the computed value under that name.
                    state = self._manager.status()
                    # What: call self._cond.notify_all with the declared inputs; why: acquire invokes self._cond.notify_all while performing return route lease; the call advances that operation through its result or side effect.
                    self._cond.notify_all()
                    # What: return route lease and profile and port and get from acquire; why: acquire exposes route lease and profile and port and get so its caller can continue with the function\'s computed outcome.
                    return RouteLease(
                        # What: apply the grouped expression portion of the enclosing predicate; why: this clause remains in  acquire\'s enclosing expression so its grouping and evaluation order stay intact.
                        self,
                        # What: apply the profile portion of the enclosing predicate; why: this clause remains in acquire\'s enclosing expression so its grouping and evaluation order stay intact.
                        profile,
                        # What: apply the port portion of the enclosing predicate; why: this clause remains in acquire\'s enclosing expression so its grouping and evaluation order stay intact.
                        port,
                        # What: call state.get with pid; why: acquire invokes state.get while performing model id model id; the call advances that operation through its result or side effect.
                        state.get("pid"),
                        # What: supply model id to RouteLease; why: acquire binds this model id value to RouteLease's model id input.
                        model_id=model_id,
                        # What: supply selector id to RouteLease; why: acquire binds this selector id value to RouteLease's selector id input.
                        selector_id=selector_id,
                        # What: supply routing profile id to RouteLease; why: acquire binds this routing profile id value to RouteLease's routing profile id input.
                        routing_profile_id=routing_profile_id,
                        # What: supply pin id to RouteLease; why: acquire binds this pin id value to RouteLease's pin id input.
                        pin_id=pin_id,
                    # What: complete the RouteLease call with model id and selector id and routing profile id and pin id; why: RoutingCoordinator.acquire groups the supplied clauses as one RouteLease call before its value is consumed.
                    )
                # What: gate on leases before wait and cond; why: acquire admits wait and cond only for this predicate and excludes the opposite state.
                if self._leases:
                    # What: call self._cond.wait with the declared inputs; why: acquire invokes self._cond.wait while performing continue; the call advances that operation through its result or side effect.
                    self._cond.wait()
                    # What: apply the continue portion of the enclosing predicate; why: this clause remains in acquire\'s enclosing expression so its grouping and evaluation order stay intact.
                    continue
                # What: compute block from capacity block and profile; why: if block is not later reads block, so acquire must retain the computed value under that name.
                block = self._capacity_block(profile)
                # What: gate on block before remove pending locked and ticket and cancellation; why: acquire admits remove pending locked and ticket and cancellation only for this predicate and excludes the opposite state.
                if block is not None:
                    # What: call self._remove_pending_locked with ticket and cancellation; why: acquire invokes self._remove_pending_locked while performing self drop concurrency reservation locked profile; the call advances that operation through its result or side effect.
                    self._remove_pending_locked(ticket, cancellation)
                    # What: call self._drop_concurrency_reservation_locked with profile; why: acquire invokes self._drop_concurrency_reservation_locked while performing self cond notify all; the call advances that operation through its result or side effect.
                    self._drop_concurrency_reservation_locked(profile)
                    # What: call self._cond.notify_all with the declared inputs; why: acquire invokes self._cond.notify_all while performing raise routing error capacity unavailable block status code; the call advances that operation through its result or side effect.
                    self._cond.notify_all()
                    # What: raise RoutingError for the caller; why:  RoutingCoordinator.acquire stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise RoutingError("capacity_unavailable", block, status_code=409)
                # What: compute switching from true; why: self switching later reads switching, so acquire must retain the computed value under that name.
                self._switching = True
                # What: compute activating name from name and profile; why: self activating name later reads activating name, so acquire must retain the computed value under that name.
                self._activating_name = profile.name
                # What: compute activating port from port; why: self activating port later reads activating port, so acquire must retain the computed value under that name.
                self._activating_port = port
                # What: call self._remove_pending_locked with ticket and cancellation; why: acquire invokes self._remove_pending_locked while performing break; the call advances that operation through its result or side effect.
                self._remove_pending_locked(ticket, cancellation)
                # What: apply the break portion of the enclosing predicate; why: this clause remains in acquire\'s enclosing expression so its grouping and evaluation order stay intact.
                break

        # What: compute activated at from monotonic and time; why: self last queue wait ms round activated at queued at later reads activated at, so acquire must retain the computed value under that name.
        activated_at = time.monotonic()
        # What: establish the handler boundary for the protected operation; why: RoutingCoordinator.acquire routes failures to exception while preserving cleanup and success flow.
        try:
            # What: compute pid from activate and profile and port; why: pid later reads pid, so acquire must retain the computed value under that name.
            pid = self._activate(profile, port)
        # What: handle exception by with self cond; why: RoutingCoordinator.acquire converts that failure into this concrete recovery, response, or cleanup behavior.
        except Exception as exc:
            # What: enter the cond managed context before self switching; why: acquire releases this resource or lock after self switching on both success and failure paths.
            with self._cond:
                # What: compute switching from false; why: self switching later reads switching, so acquire must retain the computed value under that name.
                self._switching = False
                # What: compute activating name from the named fixture input; why: self activating name later reads activating name, so acquire must retain the computed value under that name.
                self._activating_name = None
                # What: compute activating port from the named fixture input; why: self activating port later reads activating port, so acquire must retain the computed value under that name.
                self._activating_port = None
                # What: compute activation failures from 1; why: the enclosing return or state update later reads activation failures, so acquire must retain the computed value under that name.
                self._activation_failures += 1
                # What: call self._drop_concurrency_reservation_locked with profile; why: acquire invokes self._drop_concurrency_reservation_locked while performing self cond notify all; the call advances that operation through its result or side effect.
                self._drop_concurrency_reservation_locked(profile)
                # What: call self._cond.notify_all with the declared inputs; why: acquire invokes self._cond.notify_all while performing if isinstance exc routing error; the call advances that operation through its result or side effect.
                self._cond.notify_all()
            # What: gate on isinstance and exc and routing error before the computed value; why: acquire admits the computed value only for this predicate and excludes the opposite state.
            if isinstance(exc, RoutingError):
                # What: re-propagate the active failure to the caller; why: RoutingCoordinator.acquire stops this rejected path before it can mutate state, dispatch work, or report success.
                raise
            # What: gate on isinstance and exc and switch launch error before exc and routing error and str and rollback; why: acquire admits exc and routing error and str and rollback only for this predicate and excludes the opposite state.
            if isinstance(exc, SwitchLaunchError):
                # What: raise RoutingError for the caller; why:  RoutingCoordinator.acquire stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RoutingError("switch_launch_failed", str(exc), recovery=exc.rollback) from exc
            # What: gate on isinstance and exc and conflict before exc and routing error and str; why: acquire admits exc and routing error and str only for this predicate and excludes the opposite state.
            if isinstance(exc, Conflict):
                # What: raise RoutingError for the caller; why:  RoutingCoordinator.acquire stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RoutingError("serve_conflict", str(exc), status_code=409) from exc
            # What: raise RoutingError for the caller; why:  RoutingCoordinator.acquire stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RoutingError("activation_failed", str(exc)) from exc
        # What: enter the cond managed context before self active name profile name; why: acquire releases this resource or lock after self active name profile name on both success and failure paths.
        with self._cond:
            # What: compute active name from name and profile; why: the enclosing return or state update later reads active name, so acquire must retain the computed value under that name.
            self._active_name = profile.name
            # What: compute activating name from the named fixture input; why: the enclosing return or state update later reads activating name, so acquire must retain the computed value under that name.
            self._activating_name = None
            # What: compute activating port from the named fixture input; why: the enclosing return or state update later reads activating port, so acquire must retain the computed value under that name.
            self._activating_port = None
            # What: compute switching from false; why: the enclosing return or state update later reads switching, so acquire must retain the computed value under that name.
            self._switching = False
            # What: call self._cancel_idle_timer with the declared inputs; why: acquire invokes self._cancel_idle_timer while performing self leases; the call advances that operation through its result or side effect.
            self._cancel_idle_timer()
            # What: compute leases from 1; why: the enclosing return or state update later reads leases, so acquire must retain the computed value under that name.
            self._leases += 1
            # What: compute admissions from 1; why: the enclosing return or state update later reads admissions, so acquire must retain the computed value under that name.
            self._admissions += 1
            # What: compute last queue wait ms from round and activated at and queued at and 3 and 1000; why: the enclosing return or state update later reads last queue wait ms, so acquire must retain the computed value under that name.
            self._last_queue_wait_ms = round((activated_at - queued_at) * 1000, 3)
            # What: compute last activation ms from round and activated at and monotonic and time and 3; why: the enclosing return or state update later reads last activation ms, so acquire must retain the computed value under that name.
            self._last_activation_ms = round((time.monotonic() - activated_at) * 1000, 3)
            # What: call self._cond.notify_all with the declared inputs; why: acquire invokes self._cond.notify_all while performing return route lease; the call advances that operation through its result or side effect.
            self._cond.notify_all()
        # What: return route lease and profile and port and pid from acquire; why: acquire exposes route lease and profile and port and pid so its caller can continue with the function\'s computed outcome.
        return RouteLease(
            # What: apply the grouped expression portion of the enclosing predicate; why: this clause remains in  acquire\'s enclosing expression so its grouping and evaluation order stay intact.
            self,
            # What: apply the profile portion of the enclosing predicate; why: this clause remains in acquire\'s enclosing expression so its grouping and evaluation order stay intact.
            profile,
            # What: apply the port portion of the enclosing predicate; why: this clause remains in acquire\'s enclosing expression so its grouping and evaluation order stay intact.
            port,
            # What: apply the pid portion of the enclosing predicate; why: this clause remains in acquire\'s enclosing expression so its grouping and evaluation order stay intact.
            pid,
            # What: supply model id to RouteLease; why: acquire binds this model id value to RouteLease's model id input.
            model_id=model_id,
            # What: supply selector id to RouteLease; why: acquire binds this selector id value to RouteLease's selector id input.
            selector_id=selector_id,
            # What: supply routing profile id to RouteLease; why: acquire binds this routing profile id value to RouteLease's routing profile id input.
            routing_profile_id=routing_profile_id,
            # What: supply pin id to RouteLease; why: acquire binds this pin id value to RouteLease's pin id input.
            pin_id=pin_id,
        # What: complete the RouteLease call with model id and selector id and routing profile id and pin id; why: RoutingCoordinator.acquire groups the supplied clauses as one RouteLease call before its value is consumed.
        )

    # What: define cancel_acquire around cancellation; why: its direct callers call cancel_acquire for cancel acquire and rely on this exact input and result contract.
    def cancel_acquire(self, cancellation: threading.Event) -> None:
        """Atomically retire queued ownership, then wake its admission worker."""
        # What: document atomically retire queued ownership then wake in the cancel_acquire docstring; why: introspection and maintainers read this exact docstring fragment to understand cancel acquire behavior without executing it.
        # What: enter the cond managed context before cancellation set; why: cancel_acquire releases this resource or lock after cancellation set on both success and failure paths.
        with self._cond:
            # What: call cancellation.set with the declared inputs; why: cancel_acquire invokes cancellation.set while performing pending self pending by cancellation get cancellation; the call advances that operation through its result or side effect.
            cancellation.set()
            # What: compute pending from get and cancellation and pending by cancellation; why: if pending is not later reads pending, so cancel_acquire must retain the computed value under that name.
            pending = self._pending_by_cancellation.get(cancellation)
            # What: gate on pending before pending and ticket and profile; why: cancel_acquire admits pending and ticket and profile only for this predicate and excludes the opposite state.
            if pending is not None:
                # What: compute ticket and profile from pending; why: if self remove pending locked ticket cancellation later reads ticket and profile, so cancel_acquire must retain the computed value under that name.
                ticket, profile = pending
                # What: gate on remove pending locked and ticket and cancellation before drop concurrency reservation locked and profile; why: cancel_acquire admits drop concurrency reservation locked and profile only for this predicate and excludes the opposite state.
                if self._remove_pending_locked(ticket, cancellation):
                    # What: call self._drop_concurrency_reservation_locked with profile; why: cancel_acquire invokes self._drop_concurrency_reservation_locked while performing self cond notify all; the call advances that operation through its result or side effect.
                    self._drop_concurrency_reservation_locked(profile)
            # What: call self._cond.notify_all with the declared inputs; why: cancel_acquire invokes self._cond.notify_all while performing the enclosing return; the call advances that operation through its result or side effect.
            self._cond.notify_all()

    # What: define queue_position around cancellation; why: its direct callers call queue_position for queue position and rely on this exact input and result contract.
    def queue_position(self, cancellation: threading.Event) -> int | None:
        """Return the current one-based scheduler position for a reserved request."""
        # What: document return the current one based scheduler position in the queue_position docstring; why: introspection and maintainers read this exact docstring fragment to understand queue position behavior without executing it.
        # What: enter the cond managed context before pending self pending by cancellation get cancellation; why: queue_position releases this resource or lock after pending self pending by cancellation get cancellation on both success and failure paths.
        with self._cond:
            # What: compute pending from get and cancellation and pending by cancellation; why: if pending is later reads pending, so queue_position must retain the computed value under that name.
            pending = self._pending_by_cancellation.get(cancellation)
            # What: gate on pending before the computed value; why: queue_position admits the computed value only for this predicate and excludes the opposite state.
            if pending is None:
                # What: return no value from queue_position; why: queue_position returns no value to callers that depend on its completed result.
                return None
            # What: compute ticket and profile from pending; why: return sorted self pending index ticket later reads ticket and profile, so queue_position must retain the computed value under that name.
            ticket, _profile = pending
            # What: return index and ticket and sorted and pending and 1 from queue_position; why: queue_position exposes index and ticket and sorted and pending and 1 so its caller can continue with the function\'s computed outcome.
            return sorted(self._pending).index(ticket) + 1

    # What: define loading_feedback_enabled around name; why: its direct callers call loading_feedback_enabled for loading feedback enabled and rely on this exact input and result contract.
    def loading_feedback_enabled(self, name: str) -> bool:
        """Resolve the per-profile loading setting over the global default atomically."""
        # What: document resolve the per profile loading setting over in the loading_feedback_enabled docstring; why: introspection and maintainers read this exact docstring fragment to understand loading feedback enabled behavior without executing it.
        # What: enter the cond managed context before try; why: loading_feedback_enabled releases this resource or lock after try on both success and failure paths.
        with self._cond:
            # What: establish the handler boundary for the protected operation; why: RoutingCoordinator.loading_feedback_enabled routes failures to catalog error while preserving cleanup and success flow.
            try:
                # What: compute and profile and and and from resolve request locked and name; why: the enclosing return or state update later reads and profile and and and, so loading_feedback_enabled must retain the computed value under that name.
                _, profile, _, _, _ = self._resolve_request_locked(name)
            # What: handle catalog error by return false; why: RoutingCoordinator.loading_feedback_enabled converts that failure into this concrete recovery, response, or cleanup behavior.
            except CatalogError:
                # Admission owns the authoritative unknown-model response. A
                # concurrent catalog replacement must not leak an exception
                # from this optional pre-admission presentation policy.
                # What: return false from loading_feedback_enabled; why: loading_feedback_enabled exposes false so its caller can continue with the function\'s computed outcome.
                return False
            # What: gate on send loading state and profile before send loading state and profile; why: loading_feedback_enabled admits send loading state and profile only for this predicate and excludes the opposite state.
            if profile.send_loading_state is not None:
                # What: return send loading state and profile from loading_feedback_enabled; why: loading_feedback_enabled exposes send loading state and profile so its caller can continue with the function\'s computed outcome.
                return profile.send_loading_state
            # What: return send loading state and settings and catalog from loading_feedback_enabled; why: loading_feedback_enabled exposes send loading state and settings and catalog so its caller can continue with the function\'s computed outcome.
            return self._catalog.settings.send_loading_state

    # What: define _resolve_request_locked around name and apply routing profile; why: its direct callers call _resolve_request_locked for resolve request locked and rely on this exact input and result contract.
    def _resolve_request_locked(
        # What: declare the self input for _resolve_request_locked; why: _resolve_request_locked consumes self during if apply routing profile and self active routing profile is not, so callers must bind it with the other signature inputs.
        self, name: str, *, apply_routing_profile: bool = True
    # What: complete the enclosing predicate collection with str and model profile and str and str; why: RoutingCoordinator._resolve_request_locked groups the supplied clauses as one enclosing predicate collection collection before its value is consumed.
    ) -> tuple[str, ModelProfile, str | None, str | None, str | None]:
        # What: compute routing profile id from the named fixture input; why: routing profile id routing profile name later reads routing profile id, so _resolve_request_locked must retain the computed value under that name.
        routing_profile_id = None
        # What: compute pin id from the named fixture input; why: pin id name later reads pin id, so _resolve_request_locked must retain the computed value under that name.
        pin_id = None
        # What: gate on apply routing profile and active routing profile before routing profile and active routing profile and catalog; why: _resolve_request_locked admits routing profile and active routing profile and catalog only for this predicate and excludes the opposite state.
        if apply_routing_profile and self._active_routing_profile is not None:
            # What: compute routing profile from routing profile and active routing profile and catalog; why: if routing profile is not later reads routing profile, so _resolve_request_locked must retain the computed value under that name.
            routing_profile = self._catalog.routing_profile(self._active_routing_profile)
            # What: gate on routing profile before pinned and target and replacement and name and routing profile; why: _resolve_request_locked admits pinned and target and replacement and name and routing profile only for this predicate and excludes the opposite state.
            if routing_profile is not None:
                # What: compute pinned and target from replacement and name and routing profile; why: if pinned later reads pinned and target, so _resolve_request_locked must retain the computed value under that name.
                pinned, target = routing_profile.replacement(name)
                # What: gate on pinned before routing profile id and name and routing profile; why: _resolve_request_locked admits routing profile id and name and routing profile only for this predicate and excludes the opposite state.
                if pinned:
                    # What: compute routing profile id from name and routing profile; why: return name self catalog get name routing profile id pin id later reads routing profile id, so _resolve_request_locked must retain the computed value under that name.
                    routing_profile_id = routing_profile.name
                    # What: compute pin id from name; why: return name self catalog get name routing profile id pin id later reads pin id, so _resolve_request_locked must retain the computed value under that name.
                    pin_id = name
                    # What: gate on target before catalog error and name and routing profile; why: _resolve_request_locked admits catalog error and name and routing profile only for this predicate and excludes the opposite state.
                    if target is None:
                        # What: raise CatalogError for the caller; why: RoutingCoordinator._resolve_request_locked stops this rejected path before it can mutate state, dispatch work, or report success.
                        raise CatalogError(
                            # What: apply the f model id name r is portion of the enclosing predicate; why: this clause remains in _resolve_request_locked\'s enclosing expression so its grouping and evaluation order stay intact.
                            f"model ID {name!r} is disabled by routing profile {routing_profile.name!r}"
                        # What: complete the CatalogError call with name; why: RoutingCoordinator._resolve_request_locked groups the supplied clauses as one CatalogError call before its value is consumed.
                        )
                    # What: compute name from target; why: selector self catalog selector name later reads name, so _resolve_request_locked must retain the computed value under that name.
                    name = target
        # What: compute selector from selector and name and catalog; why: if selector is later reads selector, so _resolve_request_locked must retain the computed value under that name.
        selector = self._catalog.selector(name)
        # What: gate on selector before name and routing profile id and pin id and get and catalog; why: _resolve_request_locked admits name and routing profile id and pin id and get and catalog only for this predicate and excludes the opposite state.
        if selector is None:
            # What: return name and routing profile id and pin id and get from _resolve_request_locked; why: _resolve_request_locked exposes name and routing profile id and pin id and get so its caller can continue with the function\'s computed outcome.
            return name, self._catalog.get(name), None, routing_profile_id, pin_id
        # What: gate on strategy and selector before target and targets and selector and profile and get; why: _resolve_request_locked admits target and targets and selector and profile and get only for this predicate and excludes the opposite state.
        if selector.strategy == "warm":
            # What: iterate across targets and selector to perform profile and get and target and catalog; why: _resolve_request_locked repeats the body only while or for the loop header admits an iteration.
            for target in selector.targets:
                # What: compute profile from get and target and catalog; why: if self active profile ready locked profile later reads profile, so _resolve_request_locked must retain the computed value under that name.
                profile = self._catalog.get(target)
                # What: gate on active profile ready locked and profile before target and profile and name and routing profile id and pin id; why: _resolve_request_locked admits target and profile and name and routing profile id and pin id only for this predicate and excludes the opposite state.
                if self._active_profile_ready_locked(profile):
                    # What: return target and profile and name and routing profile id from _resolve_request_locked; why: _resolve_request_locked exposes target and profile and name and routing profile id so its caller can continue with the function\'s computed outcome.
                    return target, profile, selector.name, routing_profile_id, pin_id
            # What: iterate across targets and selector to perform profile and get and target and catalog; why: _resolve_request_locked repeats the body only while or for the loop header admits an iteration.
            for target in selector.targets:
                # What: compute profile from get and target and catalog; why: if self activating name profile name later reads profile, so _resolve_request_locked must retain the computed value under that name.
                profile = self._catalog.get(target)
                # What: gate on activating name and name and profile before target and profile and name and routing profile id and pin id; why: _resolve_request_locked admits target and profile and name and routing profile id and pin id only for this predicate and excludes the opposite state.
                if self._activating_name == profile.name:
                    # What: return target and profile and name and routing profile id from _resolve_request_locked; why: _resolve_request_locked exposes target and profile and name and routing profile id so its caller can continue with the function\'s computed outcome.
                    return target, profile, selector.name, routing_profile_id, pin_id
        # What: compute target from targets and selector and 0; why: return target self catalog get target selector name routing profile id later reads target, so _resolve_request_locked must retain the computed value under that name.
        target = selector.targets[0]
        # What: return target and name and routing profile id and pin id from _resolve_request_locked; why: _resolve_request_locked exposes target and name and routing profile id and pin id so its caller can continue with the function\'s computed outcome.
        return target, self._catalog.get(target), selector.name, routing_profile_id, pin_id

    # What: define has_routable_id around name; why: its direct callers call has_routable_id for has routable id and rely on this exact input and result contract.
    def has_routable_id(self, name: str) -> bool:
        """Whether *name* resolves under the current runtime profile snapshot."""
        # What: document whether name resolves under the current in the has_routable_id docstring; why: introspection and maintainers read this exact docstring fragment to understand has routable id behavior without executing it.
        # What: enter the cond managed context before try; why: has_routable_id releases this resource or lock after try on both success and failure paths.
        with self._cond:
            # What: establish the handler boundary for the protected operation; why: RoutingCoordinator.has_routable_id routes failures to catalog error while preserving cleanup and success flow.
            try:
                # What: call self._resolve_request_locked with name; why: has_routable_id invokes self._resolve_request_locked while performing except catalog error; the call advances that operation through its result or side effect.
                self._resolve_request_locked(name)
            # What: handle catalog error by return false; why: RoutingCoordinator.has_routable_id converts that failure into this concrete recovery, response, or cleanup behavior.
            except CatalogError:
                # What: return false from has_routable_id; why: has_routable_id exposes false so its caller can continue with the function\'s computed outcome.
                return False
            # What: return true from has_routable_id; why: has_routable_id exposes true so its caller can continue with the function\'s computed outcome.
            return True

    # What: define set_active_routing_profile around name; why: its direct callers call set_active_routing_profile for set active routing profile and rely on this exact input and result contract.
    def set_active_routing_profile(self, name: str | None) -> str | None:
        """Atomically activate one pin map, or clear runtime pinning with ``None``."""
        # What: document atomically activate one pin map or in the set_active_routing_profile docstring; why: introspection and maintainers read this exact docstring fragment to understand set active routing profile behavior without executing it.
        # What: enter the cond managed context before if name is not and self catalog routing profile; why: set_active_routing_profile releases this resource or lock after if name is not and self catalog routing profile on both success and failure paths.
        with self._cond:
            # What: gate on name and routing profile and catalog before routing error and name; why: set_active_routing_profile admits routing error and name only for this predicate and excludes the opposite state.
            if name is not None and self._catalog.routing_profile(name) is None:
                # What: raise RoutingError for the caller; why: RoutingCoordinator.set_active_routing_profile stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RoutingError(
                    # What: supply status code to RoutingError; why: set_active_routing_profile binds this 404 value to RoutingError's status code input.
                    "unknown_profile", f"routing profile {name!r} not found", status_code=404
                # What: complete the RoutingError call with status code; why: RoutingCoordinator.set_active_routing_profile groups the supplied clauses as one RoutingError call before its value is consumed.
                )
            # What: compute active routing profile from name; why: return self active routing profile later reads active routing profile, so set_active_routing_profile must retain the computed value under that name.
            self._active_routing_profile = name
            # What: call self._cond.notify_all with the declared inputs; why: set_active_routing_profile invokes self._cond.notify_all while performing return self active routing profile; the call advances that operation through its result or side effect.
            self._cond.notify_all()
            # What: return active routing profile from set_active_routing_profile; why: set_active_routing_profile exposes active routing profile so its caller can continue with the function\'s computed outcome.
            return self._active_routing_profile

    # What: define resolve_upstream_path around path; why: its direct callers call resolve_upstream_path for resolve upstream path and rely on this exact input and result contract.
    def resolve_upstream_path(
        # What: declare the self input for resolve_upstream_path; why: resolve_upstream_path consumes self during with self cond, so callers must bind it with the other signature inputs.
        self, path: str
    # What: complete the enclosing predicate collection with str and str and model profile and str; why: RoutingCoordinator.resolve_upstream_path groups the supplied clauses as one enclosing predicate collection collection before its value is consumed.
    ) -> tuple[str, str, ModelProfile, str]:
        """Apply the active profile's longest pin before concrete upstream lookup."""
        # What: document apply the active profile s longest in the resolve_upstream_path docstring; why: introspection and maintainers read this exact docstring fragment to understand resolve upstream path behavior without executing it.
        # What: enter the cond managed context before normalized path strip; why: resolve_upstream_path releases this resource or lock after normalized path strip on both success and failure paths.
        with self._cond:
            # What: compute normalized from strip and path and value; why: rewritten normalized later reads normalized, so resolve_upstream_path must retain the computed value under that name.
            normalized = path.strip("/")
            # What: compute source id from the named fixture input; why: if source id is or len pin later reads source id, so resolve_upstream_path must retain the computed value under that name.
            source_id = None
            # What: compute rewritten from normalized; why: rewritten later reads rewritten, so resolve_upstream_path must retain the computed value under that name.
            rewritten = normalized
            # What: gate on active routing profile before routing profile and active routing profile and catalog; why: resolve_upstream_path admits routing profile and active routing profile and catalog only for this predicate and excludes the opposite state.
            if self._active_routing_profile is not None:
                # What: compute routing profile from routing profile and active routing profile and catalog; why: if routing profile is not later reads routing profile, so resolve_upstream_path must retain the computed value under that name.
                routing_profile = self._catalog.routing_profile(self._active_routing_profile)
                # What: gate on routing profile before pins and pin and target and routing profile and normalized; why: resolve_upstream_path admits pins and pin and target and routing profile and normalized only for this predicate and excludes the opposite state.
                if routing_profile is not None:
                    # What: iterate across pins and routing profile to perform normalized and pin and startswith and source id and target; why: resolve_upstream_path repeats the body only while or for the loop header admits an iteration.
                    for pin, target in routing_profile.pins:
                        # What: gate on normalized and pin and startswith before source id and pin and target and rewritten and len; why: resolve_upstream_path admits source id and pin and target and rewritten and len only for this predicate and excludes the opposite state.
                        if (normalized == pin or normalized.startswith(pin + "/")) and (
                            source_id is None or len(pin) > len(source_id)
                        ):
                                # What: compute source id from pin; why: if source id is not and not later reads source id, so resolve_upstream_path must retain the computed value under that name.
                                source_id = pin
                                # What: gate on target before rewritten; why: resolve_upstream_path admits rewritten only for this predicate and excludes the opposite state.
                                if target is None:
                                    # What: compute rewritten from value; why: rewritten target normalized len pin later reads rewritten, so resolve_upstream_path must retain the computed value under that name.
                                    rewritten = ""
                                # What: select the remaining branch that performs rewritten target normalized len pin; why: resolve_upstream_path covers the state excluded by the preceding predicate without conflating the two outcomes.
                                else:
                                    # What: compute rewritten from target and normalized and len and pin; why: if source id is not and not later reads rewritten, so resolve_upstream_path must retain the computed value under that name.
                                    rewritten = target + normalized[len(pin):]
            # What: gate on source id and rewritten before catalog error and source id; why: resolve_upstream_path admits catalog error and source id only for this predicate and excludes the opposite state.
            if source_id is not None and not rewritten:
                # What: raise CatalogError for the caller; why: RoutingCoordinator.resolve_upstream_path stops this rejected path before it can mutate state, dispatch work, or report success.
                raise CatalogError(
                    # What: apply the f upstream model id source id r portion of the enclosing predicate; why: this clause remains in resolve_upstream_path\'s enclosing expression so its grouping and evaluation order stay intact.
                    f"upstream model ID {source_id!r} is disabled by the active routing profile"
                # What: complete the CatalogError call with source id; why: RoutingCoordinator.resolve_upstream_path groups the supplied clauses as one CatalogError call before its value is consumed.
                )
            # What: compute routed id and profile and remaining from resolve upstream path and rewritten and catalog; why: return source id or routed id routed id profile later reads routed id and profile and remaining, so resolve_upstream_path must retain the computed value under that name.
            routed_id, profile, remaining = self._catalog.resolve_upstream_path(rewritten)
            # What: return routed id and profile and remaining and source id from resolve_upstream_path; why: resolve_upstream_path exposes routed id and profile and remaining and source id so its caller can continue with the function\'s computed outcome.
            return source_id or routed_id, routed_id, profile, remaining

    # What: define begin_manual_lifecycle and its declared inputs; why: callers use begin_manual_lifecycle to perform the behavior named by this helper without duplicating its boundary checks.
    def begin_manual_lifecycle(self, *, preempt_manual: bool = False) -> object:
        """Reserve the lifecycle barrier for one legacy engine operation."""
        # What: document reserve the lifecycle barrier for one in the begin_manual_lifecycle docstring; why: introspection and maintainers read this exact docstring fragment to understand begin manual lifecycle behavior without executing it.
        # What: enter the cond managed context before if self shutdown requested; why: begin_manual_lifecycle releases this resource or lock after if self shutdown requested on both success and failure paths.
        with self._cond:
            # What: gate on shutdown requested before routing error; why: begin_manual_lifecycle admits routing error only for this predicate and excludes the opposite state.
            if self._shutdown_requested:
                # What: raise RoutingError for the caller; why: RoutingCoordinator.begin_manual_lifecycle stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RoutingError(
                    # What: supply status code to RoutingError; why: begin_manual_lifecycle binds this 503 value to RoutingError's status code input.
                    "router_shutting_down", "router shutdown is in progress", status_code=503
                # What: complete the RoutingError call with status code; why: RoutingCoordinator.begin_manual_lifecycle groups the supplied clauses as one RoutingError call before its value is consumed.
                )
            # What: compute manual owned from manual lifecycle owner; why: or self pending and not manual owned later reads manual owned, so begin_manual_lifecycle must retain the computed value under that name.
            manual_owned = self._manual_lifecycle_owner is not None
            # What: compute routed owned from bool and leases and active name and pending; why: if routed owned or self switching and not later reads routed owned, so begin_manual_lifecycle must retain the computed value under that name.
            routed_owned = bool(
                # What: apply the self active name is not or self leases portion of routed owned; why: begin_manual_lifecycle uses this clause to evaluate routed owned as one grouped value.
                self._active_name is not None or self._leases
                # What: apply the or self pending and not manual owned portion of routed owned; why: begin_manual_lifecycle uses this clause to evaluate routed owned as one grouped value.
                or (self._pending and not manual_owned)
            # What: complete the bool call with leases; why: RoutingCoordinator.begin_manual_lifecycle groups the supplied clauses as one bool call before its value is consumed.
            )
            # What: gate on routed owned and switching and preempt manual and manual owned before routing error; why: begin_manual_lifecycle admits routing error only for this predicate and excludes the opposite state.
            if (routed_owned or (self._switching and not (preempt_manual and manual_owned))):
                # What: raise RoutingError for the caller; why: RoutingCoordinator.begin_manual_lifecycle stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RoutingError(
                    # What: apply the router owned portion of the enclosing predicate; why: this clause remains in begin_manual_lifecycle\'s enclosing expression so its grouping and evaluation order stay intact.
                    "router_owned",
                    # What: apply the router owns or is admitting an portion of the enclosing predicate; why: this clause remains in begin_manual_lifecycle\'s enclosing expression so its grouping and evaluation order stay intact.
                    "router owns or is admitting an engine; use router controls or wait",
                    # What: supply status code to RoutingError; why: begin_manual_lifecycle binds this 409 value to RoutingError's status code input.
                    status_code=409,
                # What: complete the RoutingError call with status code; why: RoutingCoordinator.begin_manual_lifecycle groups the supplied clauses as one RoutingError call before its value is consumed.
                )
            # What: compute owner from object; why: self manual lifecycle tokens add owner later reads owner, so begin_manual_lifecycle must retain the computed value under that name.
            owner = object()
            # What: call self._manual_lifecycle_tokens.add with owner; why: begin_manual_lifecycle invokes self._manual_lifecycle_tokens.add while performing self manual lifecycle owner owner; the call advances that operation through its result or side effect.
            self._manual_lifecycle_tokens.add(owner)
            # What: compute manual lifecycle owner from owner; why: the enclosing return or state update later reads manual lifecycle owner, so begin_manual_lifecycle must retain the computed value under that name.
            self._manual_lifecycle_owner = owner
            # What: compute switching from true; why: the enclosing return or state update later reads switching, so begin_manual_lifecycle must retain the computed value under that name.
            self._switching = True
            # What: return owner from begin_manual_lifecycle; why: begin_manual_lifecycle exposes owner so its caller can continue with the function\'s computed outcome.
            return owner

    # What: define end_manual_lifecycle around owner; why: its direct callers call end_manual_lifecycle for end manual lifecycle and rely on this exact input and result contract.
    def end_manual_lifecycle(self, owner: object) -> None:
        """Release a matching legacy lifecycle reservation."""
        # What: document release a matching legacy lifecycle reservation in the end_manual_lifecycle docstring; why: introspection and maintainers read this exact docstring fragment to understand end manual lifecycle behavior without executing it.
        # What: enter the cond managed context before if owner not in self manual lifecycle tokens; why: end_manual_lifecycle releases this resource or lock after if owner not in self manual lifecycle tokens on both success and failure paths.
        with self._cond:
            # What: gate on owner and manual lifecycle tokens before value error; why: end_manual_lifecycle admits value error only for this predicate and excludes the opposite state.
            if owner not in self._manual_lifecycle_tokens:
                # What: raise ValueError for the caller; why: RoutingCoordinator.end_manual_lifecycle stops this rejected path before it can mutate state, dispatch work, or report success.
                raise ValueError("manual lifecycle reservation is not owned by caller")
            # What: call self._manual_lifecycle_tokens.remove with owner; why: end_manual_lifecycle invokes self._manual_lifecycle_tokens.remove while performing if self manual lifecycle owner is owner; the call advances that operation through its result or side effect.
            self._manual_lifecycle_tokens.remove(owner)
            # What: gate on manual lifecycle owner and owner before manual lifecycle owner; why: end_manual_lifecycle admits manual lifecycle owner only for this predicate and excludes the opposite state.
            if self._manual_lifecycle_owner is owner:
                # What: compute manual lifecycle owner from the named fixture input; why: the enclosing return or state update later reads manual lifecycle owner, so end_manual_lifecycle must retain the computed value under that name.
                self._manual_lifecycle_owner = None
                # What: compute switching from false; why: the enclosing return or state update later reads switching, so end_manual_lifecycle must retain the computed value under that name.
                self._switching = False
            # What: call self._cond.notify_all with the declared inputs; why: end_manual_lifecycle invokes self._cond.notify_all while performing the enclosing return; the call advances that operation through its result or side effect.
            self._cond.notify_all()

    # What: define release around lease; why: its direct callers call release for release and rely on this exact input and result contract.
    def release(self, lease: RouteLease) -> None:
        # What: enter the cond managed context before if lease router is not; why: release releases this resource or lock after if lease router is not on both success and failure paths.
        with self._cond:
            # What: gate on router and lease before value error; why: release admits value error only for this predicate and excludes the opposite state.
            if lease.router is not self:
                # What: raise ValueError for the caller; why:  RoutingCoordinator.release stops this rejected path before it can mutate state, dispatch work, or report success.
                raise ValueError("lease belongs to a different routing coordinator")
            # What: gate on released and lease and leases before value error; why: release admits value error only for this predicate and excludes the opposite state.
            if lease._released or self._leases <= 0:
                # What: raise ValueError for the caller; why:  RoutingCoordinator.release stops this rejected path before it can mutate state, dispatch work, or report success.
                raise ValueError("routing lease was already released")
            # What: compute released from true; why: the enclosing return or state update later reads released, so release must retain the computed value under that name.
            lease._released = True
            # What: compute leases from 1; why: if self leases later reads leases, so release must retain the computed value under that name.
            self._leases -= 1
            # What: call self._drop_concurrency_reservation_locked with profile and lease; why: release invokes self._drop_concurrency_reservation_locked while performing if self leases; the call advances that operation through its result or side effect.
            self._drop_concurrency_reservation_locked(lease.profile)
            # What: gate on leases before schedule idle eviction; why: release admits schedule idle eviction only for this predicate and excludes the opposite state.
            if self._leases == 0:
                # What: call self._schedule_idle_eviction with the declared inputs; why: release invokes self._schedule_idle_eviction while performing self cond notify all; the call advances that operation through its result or side effect.
                self._schedule_idle_eviction()
            # What: call self._cond.notify_all with the declared inputs; why: release invokes self._cond.notify_all while performing the enclosing return; the call advances that operation through its result or side effect.
            self._cond.notify_all()

    # What: define status around the current object state; why: its direct callers call status for status and rely on this exact input and result contract.
    def status(self) -> dict:
        # What: enter the cond managed context before return self status locked; why: status releases this resource or lock after return self status locked on both success and failure paths.
        with self._cond:
            # What: return status locked from status; why: status exposes status locked so its caller can continue with the function\'s computed outcome.
            return self._status_locked()

    # What: define _status_locked around the current object state; why: its direct callers call _status_locked for status locked and rely on this exact input and result contract.
    def _status_locked(self) -> dict:
        # What: compute group from active name and group for and catalog; why: active group group name if group else later reads group, so _status_locked must retain the computed value under that name.
        group = self._catalog.group_for(self._active_name) if self._active_name else None
        # What: compute active identity matches from active matches engine locked; why: resident profiles self active name if active identity matches else later reads active identity matches, so _status_locked must retain the computed value under that name.
        active_identity_matches = self._active_matches_engine_locked()
        # What: return active name and active routing profile and activating name and active identity matches from _status_locked; why: _status_locked exposes active name and active routing profile and activating name and active identity matches so its caller can continue with the function\'s computed outcome.
        return {
            # What: map the active profile field as active name; why: RoutingCoordinator._status_locked carries active profile into "activeProfile": self._active_name.
            "activeProfile": self._active_name,
            # What: map the active routing profile field as active routing profile; why: RoutingCoordinator._status_locked carries active routing profile into "activeRoutingProfile": self._active_routing_profile.
            "activeRoutingProfile": self._active_routing_profile,
            # What: map the activating profile field as activating name; why: RoutingCoordinator._status_locked carries activating profile into "activatingProfile": self._activating_name.
            "activatingProfile": self._activating_name,
            # What: map the active group field as group and name; why: RoutingCoordinator._status_locked carries active group into "activeGroup": group.name if group else None.
            "activeGroup": group.name if group else None,
            # What: map the resident profiles field as active identity matches and active name; why: RoutingCoordinator._status_locked carries resident profiles into "residentProfiles": [self._active_name] if active_identity_matches else.
            "residentProfiles": [self._active_name] if active_identity_matches else [],
            # What: map the active identity matches engine field as active identity matches; why: RoutingCoordinator._status_locked carries active identity matches engine into "activeIdentityMatchesEngine": active_identity_matches.
            "activeIdentityMatchesEngine": active_identity_matches,
            # What: map the persistent field as bool and active identity matches and group and persistent; why: RoutingCoordinator._status_locked carries persistent into "persistent": bool(active_identity_matches and group and group.persisten.
            "persistent": bool(active_identity_matches and group and group.persistent),
            # What: map the max resident models field as 1; why: RoutingCoordinator._status_locked carries max resident models into "capacity": {"maxResidentModels": 1, "availableResidentSlots": 0 if self.
            "capacity": {"maxResidentModels": 1, "availableResidentSlots": 0 if self._active_name else 1},
            # What: map the active requests field as leases; why: RoutingCoordinator._status_locked carries active requests into "activeRequests": self._leases.
            "activeRequests": self._leases,
            # What: map the reserved requests field as reservations; why: RoutingCoordinator._status_locked carries reserved requests into "reservedRequests": self._reservations.
            "reservedRequests": self._reservations,
            # What: map the shutting down field as shutdown requested; why: RoutingCoordinator._status_locked carries shutting down into "shuttingDown": self._shutdown_requested.
            "shuttingDown": self._shutdown_requested,
            # What: map the switching field as switching; why: RoutingCoordinator._status_locked carries switching into "switching": self._switching.
            "switching": self._switching,
            # What: map the queued requests field as len and pending; why: RoutingCoordinator._status_locked carries queued requests into "queuedRequests": len(self._pending).
            "queuedRequests": len(self._pending),
            # What: map the idle eviction scheduled field as idle timer; why: RoutingCoordinator._status_locked carries idle eviction scheduled into "idleEvictionScheduled": self._idle_timer is not None.
            "idleEvictionScheduled": self._idle_timer is not None,
            # What: map the evictions field as evictions; why: RoutingCoordinator._status_locked carries evictions into "evictions": self._evictions.
            "evictions": self._evictions,
            # What: map the admissions field as admissions; why: RoutingCoordinator._status_locked carries admissions into "admissions": self._admissions.
            "admissions": self._admissions,
            # What: map the activations field as activations; why: RoutingCoordinator._status_locked carries activations into "activations": self._activations.
            "activations": self._activations,
            # What: map the activation failures field as activation failures; why: RoutingCoordinator._status_locked carries activation failures into "activationFailures": self._activation_failures.
            "activationFailures": self._activation_failures,
            # What: map the cancellations field as cancellations; why: RoutingCoordinator._status_locked carries cancellations into "cancellations": self._cancellations.
            "cancellations": self._cancellations,
            # What: map the terminal streams field as terminal streams; why: RoutingCoordinator._status_locked carries terminal streams into "terminalStreams": self._terminal_streams.
            "terminalStreams": self._terminal_streams,
            # What: map the last ttft ms field as last ttft ms; why: RoutingCoordinator._status_locked carries last ttft ms into "lastTtftMs": self._last_ttft_ms.
            "lastTtftMs": self._last_ttft_ms,
            # What: map the last duration ms field as last duration ms; why: RoutingCoordinator._status_locked carries last duration ms into "lastDurationMs": self._last_duration_ms.
            "lastDurationMs": self._last_duration_ms,
            # What: map the last activation ms field as last activation ms; why: RoutingCoordinator._status_locked carries last activation ms into "lastActivationMs": self._last_activation_ms.
            "lastActivationMs": self._last_activation_ms,
            # What: map the last queue wait ms field as last queue wait ms; why: RoutingCoordinator._status_locked carries last queue wait ms into "lastQueueWaitMs": self._last_queue_wait_ms.
            "lastQueueWaitMs": self._last_queue_wait_ms,
            # What: map the last response bytes field as last response bytes; why: RoutingCoordinator._status_locked carries last response bytes into "lastResponseBytes": self._last_response_bytes.
            "lastResponseBytes": self._last_response_bytes,
            # What: map the last proxy bytes per second field as last proxy bytes per second; why: RoutingCoordinator._status_locked carries last proxy bytes per second into "lastProxyBytesPerSecond": self._last_proxy_bytes_per_second.
            "lastProxyBytesPerSecond": self._last_proxy_bytes_per_second,
            # What: map the scheduler field as scheduler and settings and catalog; why: RoutingCoordinator._status_locked carries scheduler into "scheduler": self._catalog.settings.scheduler.
            "scheduler": self._catalog.settings.scheduler,
            # What: map the global concurrency limit field as global concurrency limit and settings and catalog; why: RoutingCoordinator._status_locked carries global concurrency limit into "globalConcurrencyLimit": self._catalog.settings.global_concurrency_limi.
            "globalConcurrencyLimit": self._catalog.settings.global_concurrency_limit,
            # What: map the default profile concurrency limit field as default profile concurrency limit; why: RoutingCoordinator._status_locked carries default profile concurrency limit into "defaultProfileConcurrencyLimit": DEFAULT_PROFILE_CONCURRENCY_LIMIT.
            "defaultProfileConcurrencyLimit": DEFAULT_PROFILE_CONCURRENCY_LIMIT,
        # What: complete the enclosing predicate mapping with active profile and active routing profile and activating profile and active group and resident profiles; why: RoutingCoordinator._status_locked groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
        }

    # What: expose catalog as a read-only computed property; why: callers read catalog through attribute access while its getter retains control of the derived value.
    @property
    # What: define catalog around the current object state; why: the registered API client call catalog for catalog and rely on this exact input and result contract.
    def catalog(self) -> ModelCatalog:
        # What: enter the cond managed context before return self catalog; why: catalog releases this resource or lock after return self catalog on both success and failure paths.
        with self._cond:
            # What: return catalog from catalog; why: catalog exposes catalog so its caller can continue with the function\'s computed outcome.
            return self._catalog

    # What: define control_plane_snapshot around the current object state; why: its direct callers call control_plane_snapshot for control plane snapshot and rely on this exact input and result contract.
    def control_plane_snapshot(self) -> tuple[ModelCatalog, dict]:
        """Return one catalog and routing-state snapshot for control responses."""
        # What: document return one catalog and routing state snapshot in the control_plane_snapshot docstring; why: introspection and maintainers read this exact docstring fragment to understand control plane snapshot behavior without executing it.
        # What: enter the cond managed context before return self catalog self status locked; why: control_plane_snapshot releases this resource or lock after return self catalog self status locked on both success and failure paths.
        with self._cond:
            # What: return catalog and status locked from control_plane_snapshot; why: control_plane_snapshot exposes catalog and status locked so its caller can continue with the function\'s computed outcome.
            return self._catalog, self._status_locked()

    # What: define model_listing_snapshot around the current object state; why: its direct callers call model_listing_snapshot for model listing snapshot and rely on this exact input and result contract.
    def model_listing_snapshot(self) -> tuple[ModelCatalog, frozenset[str]]:
        """Return one atomic public-catalog and loaded/starting identity snapshot."""
        # What: document return one atomic public catalog and loaded in the model_listing_snapshot docstring; why: introspection and maintainers read this exact docstring fragment to understand model listing snapshot behavior without executing it.
        # What: enter the cond managed context before loaded set str set; why: model_listing_snapshot releases this resource or lock after loaded set str set on both success and failure paths.
        with self._cond:
            # What: compute loaded from set; why: loaded add self active name later reads loaded, so model_listing_snapshot must retain the computed value under that name.
            loaded: set[str] = set()
            # What: gate on active name and active matches engine locked before add and active name and loaded; why: model_listing_snapshot admits add and active name and loaded only for this predicate and excludes the opposite state.
            if self._active_name is not None and self._active_matches_engine_locked():
                # What: call loaded.add with active name; why: model_listing_snapshot invokes loaded.add while performing if self activating name is not and self activating port; the call advances that operation through its result or side effect.
                loaded.add(self._active_name)
            # What: gate on activating name and activating port before profile and get and activating name and catalog; why: model_listing_snapshot admits profile and get and activating name and catalog only for this predicate and excludes the opposite state.
            if self._activating_name is not None and self._activating_port is not None:
                # What: compute profile from get and activating name and catalog; why: if self engine matches profile self activating port later reads profile, so model_listing_snapshot must retain the computed value under that name.
                profile = self._catalog.get(self._activating_name)
                # What: gate on engine matches and profile and activating port before add and activating name and loaded; why: model_listing_snapshot admits add and activating name and loaded only for this predicate and excludes the opposite state.
                if self._engine_matches(profile, self._activating_port):
                    # What: call loaded.add with activating name; why: model_listing_snapshot invokes loaded.add while performing return self catalog frozenset loaded; the call advances that operation through its result or side effect.
                    loaded.add(self._activating_name)
            # What: return catalog and frozenset and loaded from model_listing_snapshot; why: model_listing_snapshot exposes catalog and frozenset and loaded so its caller can continue with the function\'s computed outcome.
            return self._catalog, frozenset(loaded)

    # What: define public_model_listing_snapshot around the current object state; why: its direct callers call public_model_listing_snapshot for public model listing snapshot and rely on this exact input and result contract.
    def public_model_listing_snapshot(
        # What: declare the self input for public_model_listing_snapshot; why: public_model_listing_snapshot consumes self during with self cond, so callers must bind it with the other signature inputs.
        self,
    # What: complete the enclosing predicate collection with model catalog and frozenset and str and str; why: RoutingCoordinator.public_model_listing_snapshot groups the supplied clauses as one enclosing predicate collection collection before its value is consumed.
    ) -> tuple[ModelCatalog, frozenset[str], str | None]:
        """Include the active runtime pin map in the same catalog/residency snapshot."""
        # What: document include the active runtime pin map in the public_model_listing_snapshot docstring; why: introspection and maintainers read this exact docstring fragment to understand public model listing snapshot behavior without executing it.
        # What: enter the cond managed context before loaded set str set; why: public_model_listing_snapshot releases this resource or lock after loaded set str set on both success and failure paths.
        with self._cond:
            # What: compute loaded from set; why: loaded add self active name later reads loaded, so public_model_listing_snapshot must retain the computed value under that name.
            loaded: set[str] = set()
            # What: gate on active name and active matches engine locked before add and active name and loaded; why: public_model_listing_snapshot admits add and active name and loaded only for this predicate and excludes the opposite state.
            if self._active_name is not None and self._active_matches_engine_locked():
                # What: call loaded.add with active name; why: public_model_listing_snapshot invokes loaded.add while performing if self activating name is not and self activating port; the call advances that operation through its result or side effect.
                loaded.add(self._active_name)
            # What: gate on activating name and activating port before profile and get and activating name and catalog; why: public_model_listing_snapshot admits profile and get and activating name and catalog only for this predicate and excludes the opposite state.
            if self._activating_name is not None and self._activating_port is not None:
                # What: compute profile from get and activating name and catalog; why: if self engine matches profile self activating port later reads profile, so public_model_listing_snapshot must retain the computed value under that name.
                profile = self._catalog.get(self._activating_name)
                # What: gate on engine matches and profile and activating port before add and activating name and loaded; why: public_model_listing_snapshot admits add and activating name and loaded only for this predicate and excludes the opposite state.
                if self._engine_matches(profile, self._activating_port):
                    # What: call loaded.add with activating name; why: public_model_listing_snapshot invokes loaded.add while performing return self catalog frozenset loaded self active routing profile; the call advances that operation through its result or side effect.
                    loaded.add(self._activating_name)
            # What: return catalog and active routing profile and frozenset and loaded from public_model_listing_snapshot; why: public_model_listing_snapshot exposes catalog and active routing profile and frozenset and loaded so its caller can continue with the function\'s computed outcome.
            return self._catalog, frozenset(loaded), self._active_routing_profile

    # What: define active_matches_engine around the current object state; why: its direct callers call active_matches_engine for active matches engine and rely on this exact input and result contract.
    def active_matches_engine(self) -> bool:
        """Whether the manager still owns the exact resident routed profile.

        A listening child alone is not a readiness signal: an out-of-band or
        stale child must not make the stable router URL appear healthy for the
        alias recorded by the coordinator.
        """
        # What: document whether the manager still owns the in the active_matches_engine docstring; why: introspection and maintainers read this exact docstring fragment to understand active matches engine behavior without executing it.
        # What: document a listening child alone is not in the active_matches_engine docstring; why: introspection and maintainers read this exact docstring fragment to understand active matches engine behavior without executing it.
        # What: document stale child must not make the in the active_matches_engine docstring; why: introspection and maintainers read this exact docstring fragment to understand active matches engine behavior without executing it.
        # What: document alias recorded by the coordinator in the active_matches_engine docstring; why: introspection and maintainers read this exact docstring fragment to understand active matches engine behavior without executing it.
        # What: preserve the paragraph boundary in the the active_matches_engine docstring; why: introspection and maintainers read this paragraph break to understand active matches engine behavior without executing it.
        # What: enter the cond managed context before return self active matches engine locked; why: active_matches_engine releases this resource or lock after return self active matches engine locked on both success and failure paths.
        with self._cond:
            # What: return active matches engine locked from active_matches_engine; why: active_matches_engine exposes active matches engine locked so its caller can continue with the function\'s computed outcome.
            return self._active_matches_engine_locked()

    # What: define profile_is_resident around model id; why: its direct callers call profile_is_resident for profile is resident and rely on this exact input and result contract.
    def profile_is_resident(self, model_id: str) -> bool:
        """Whether *model_id* resolves to the exact readiness-gated resident.

        This lifecycle-state query intentionally does not perform network I/O.
        It lets direct static-asset requests refuse a cold activation while
        using the same exact identity check as ordinary warm admission.
        """
        # What: document whether model id resolves to the exact in the profile_is_resident docstring; why: introspection and maintainers read this exact docstring fragment to understand profile is resident behavior without executing it.
        # What: document this lifecycle state query intentionally does not in the profile_is_resident docstring; why: introspection and maintainers read this exact docstring fragment to understand profile is resident behavior without executing it.
        # What: document it lets direct static asset requests refuse in the profile_is_resident docstring; why: introspection and maintainers read this exact docstring fragment to understand profile is resident behavior without executing it.
        # What: document using the same exact identity check in the profile_is_resident docstring; why: introspection and maintainers read this exact docstring fragment to understand profile is resident behavior without executing it.
        # What: preserve the paragraph boundary in the the profile_is_resident docstring; why: introspection and maintainers read this paragraph break to understand profile is resident behavior without executing it.
        # What: enter the cond managed context before try; why: profile_is_resident releases this resource or lock after try on both success and failure paths.
        with self._cond:
            # What: establish the handler boundary for the protected operation; why: RoutingCoordinator.profile_is_resident routes failures to catalog error while preserving cleanup and success flow.
            try:
                # What: compute profile from get and model id and catalog; why: and self active profile ready locked profile later reads profile, so profile_is_resident must retain the computed value under that name.
                profile = self._catalog.get(model_id)
            # What: handle catalog error by return false; why: RoutingCoordinator.profile_is_resident converts that failure into this concrete recovery, response, or cleanup behavior.
            except CatalogError:
                # What: return false from profile_is_resident; why: profile_is_resident exposes false so its caller can continue with the function\'s computed outcome.
                return False
            # What: return shutdown requested and switching and active profile ready locked and profile from profile_is_resident; why: profile_is_resident exposes shutdown requested and switching and active profile ready locked and profile so its caller can continue with the function\'s computed outcome.
            return (
                # What: apply the not self shutdown requested portion of the enclosing predicate; why: this clause remains in profile_is_resident\'s enclosing expression so its grouping and evaluation order stay intact.
                not self._shutdown_requested
                # What: apply the and not self switching portion of the enclosing predicate; why: this clause remains in profile_is_resident\'s enclosing expression so its grouping and evaluation order stay intact.
                and not self._switching
                # What: call self._active_profile_ready_locked with profile; why: profile_is_resident consumes the self._active_profile_ready_locked return value while evaluating and self._active_profile_ready_locked(profile).
                and self._active_profile_ready_locked(profile)
            # What: complete the profile_is_resident signature with self and model id; why: RoutingCoordinator.profile_is_resident groups the supplied clauses as one profile_is_resident signature before its value is consumed.
            )

    # What: define is_ready around probe; why: its direct callers call is_ready for is ready and rely on this exact input and result contract.
    def is_ready(self, probe=None) -> bool:
        """Atomically verify resident identity and fresh engine readiness.

        Holding the admission condition across the bounded loopback probe keeps
        a conflicting swap from committing between an identity snapshot and a
        stale successful health response.
        """
        # What: document atomically verify resident identity and fresh in the is_ready docstring; why: introspection and maintainers read this exact docstring fragment to understand is ready behavior without executing it.
        # What: document holding the admission condition across the in the is_ready docstring; why: introspection and maintainers read this exact docstring fragment to understand is ready behavior without executing it.
        # What: document a conflicting swap from committing around in the is_ready docstring; why: introspection and maintainers read this exact docstring fragment to understand is ready behavior without executing it.
        # What: document stale successful health response in the is_ready docstring; why: introspection and maintainers read this exact docstring fragment to understand is ready behavior without executing it.
        # What: preserve the paragraph boundary in the the is_ready docstring; why: introspection and maintainers read this paragraph break to understand is ready behavior without executing it.
        # What: enter the cond managed context before if self shutdown requested or self switching or not; why: is_ready releases this resource or lock after if self shutdown requested or self switching or not on both success and failure paths.
        with self._cond:
            # What: gate on shutdown requested and switching and active matches engine locked before the computed value; why: is_ready admits the computed value only for this predicate and excludes the opposite state.
            if self._shutdown_requested or self._switching or not self._active_matches_engine_locked():
                # What: return false from is_ready; why: is_ready exposes false so its caller can continue with the function\'s computed outcome.
                return False
            # What: compute state from status and manager; why: port state get port later reads state, so is_ready must retain the computed value under that name.
            state = self._manager.status()
            # What: compute port from get and state and port; why: if not isinstance port int or later reads port, so is_ready must retain the computed value under that name.
            port = state.get("port")
            # What: gate on port and isinstance and int before the computed value; why: is_ready admits the computed value only for this predicate and excludes the opposite state.
            if not isinstance(port, int) or port <= 0:
                # What: return false from is_ready; why: is_ready exposes false so its caller can continue with the function\'s computed outcome.
                return False
            # What: compute profile from get and active name and catalog; why: if profile check endpoint default check endpoint later reads profile, so is_ready must retain the computed value under that name.
            profile = self._catalog.get(self._active_name)
            # What: compute active probe from probe and probe; why: active probe fresh health port later reads active probe, so is_ready must retain the computed value under that name.
            active_probe = probe or self._probe
            # What: compute health from check endpoint and default check endpoint and fresh health and port; why: health get reachable later reads health, so is_ready must retain the computed value under that name.
            health = (
                # What: call active_probe.fresh_health with port; why: is_ready invokes active_probe.fresh_health while performing if profile check endpoint default check endpoint; the call advances that operation through its result or side effect.
                active_probe.fresh_health(port)
                # What: apply the if profile check endpoint default check endpoint portion of health; why: is_ready uses this clause to evaluate health as one grouped value.
                if profile.check_endpoint == DEFAULT_CHECK_ENDPOINT
                # What: call active_probe.fresh_readiness with port and check endpoint and profile; why: is_ready consumes the active_probe.fresh_readiness return value while evaluating else active_probe.fresh_readiness(port, profile.check_endpoint).
                else active_probe.fresh_readiness(port, profile.check_endpoint)
            # What: complete the health expression with health active probe fresh health port if profile check endpoint equals default check endpoint else active probe fresh re; why: RoutingCoordinator.is_ready groups the supplied clauses as one health expression before its value is consumed.
            )
            # What: gate on shutdown requested and switching and active matches engine locked before the computed value; why: is_ready admits the computed value only for this predicate and excludes the opposite state.
            if self._shutdown_requested or self._switching or not self._active_matches_engine_locked():
                # What: return false from is_ready; why: is_ready exposes false so its caller can continue with the function\'s computed outcome.
                return False
            # What: return bool and get and health and check endpoint from is_ready; why: is_ready exposes bool and get and health and check endpoint so its caller can continue with the function\'s computed outcome.
            return bool(
                # What: call health.get with reachable; why: is_ready invokes health.get while performing and; the call advances that operation through its result or side effect.
                health.get("reachable")
                # What: apply the and portion of the enclosing predicate; why: this clause remains in is_ready\'s enclosing expression so its grouping and evaluation order stay intact.
                and (
                    # What: apply the profile check endpoint default check endpoint portion of the enclosing predicate; why: this clause remains in is_ready\'s enclosing expression so its grouping and evaluation order stay intact.
                    profile.check_endpoint != DEFAULT_CHECK_ENDPOINT
                    # What: apply the or portion of the enclosing predicate; why: this clause remains in is_ready\'s enclosing expression so its grouping and evaluation order stay intact.
                    or (
                        # What: call health.get with status; why: is_ready invokes health.get while performing and health get maintenance serving serving; the call advances that operation through its result or side effect.
                        health.get("status") == "ok"
                        # What: call health.get with maintenance and serving; why: is_ready consumes the health.get return value while evaluating and health.get("maintenance", "serving") == "serving".
                        and health.get("maintenance", "serving") == "serving"
                    # What: complete the bool call with get; why: RoutingCoordinator.is_ready groups the supplied clauses as one bool call before its value is consumed.
                    )
                # What: complete the bool call with get; why: RoutingCoordinator.is_ready groups the supplied clauses as one bool call before its value is consumed.
                )
            # What: complete the bool call with get; why: RoutingCoordinator.is_ready groups the supplied clauses as one bool call before its value is consumed.
            )

    # What: expose upstream_timeout_s as a read-only computed property; why: callers read upstream_timeout_s through attribute access while its getter retains control of the derived value.
    @property
    # What: define upstream_timeout_s around the current object state; why: the registered API client call upstream_timeout_s for upstream timeout s and rely on this exact input and result contract.
    def upstream_timeout_s(self) -> float:
        # What: enter the cond managed context before return self catalog settings upstream timeout s; why: upstream_timeout_s releases this resource or lock after return self catalog settings upstream timeout s on both success and failure paths.
        with self._cond:
            # What: return upstream timeout s and settings and catalog from upstream_timeout_s; why: upstream_timeout_s exposes upstream timeout s and settings and catalog so its caller can continue with the function\'s computed outcome.
            return self._catalog.settings.upstream_timeout_s

    # What: define replace_catalog around catalog; why: its direct callers call replace_catalog for replace catalog and rely on this exact input and result contract.
    def replace_catalog(self, catalog: ModelCatalog) -> None:
        """Atomically install a validated catalog without changing a live engine.

        Removing or redefining the active profile is refused. The operator can
        explicitly unload first, which keeps configuration reload from silently
        changing the ownership contract of an existing engine.
        """
        # What: document atomically install a validated catalog without in the replace_catalog docstring; why: introspection and maintainers read this exact docstring fragment to understand replace catalog behavior without executing it.
        # What: document removing or redefining the active profile in the replace_catalog docstring; why: introspection and maintainers read this exact docstring fragment to understand replace catalog behavior without executing it.
        # What: document explicitly unload first which keeps configuration in the replace_catalog docstring; why: introspection and maintainers read this exact docstring fragment to understand replace catalog behavior without executing it.
        # What: document changing the ownership contract of an in the replace_catalog docstring; why: introspection and maintainers read this exact docstring fragment to understand replace catalog behavior without executing it.
        # What: preserve the paragraph boundary in the the replace_catalog docstring; why: introspection and maintainers read this paragraph break to understand replace catalog behavior without executing it.
        # What: enter the cond managed context before if; why: replace_catalog releases this resource or lock after if on both success and failure paths.
        with self._cond:
            # What: gate on shutdown requested and switching and pending and manual lifecycle tokens before routing error; why: replace_catalog admits routing error only for this predicate and excludes the opposite state.
            if (
                # What: apply the self shutdown requested portion of the enclosing predicate; why: this clause remains in replace_catalog\'s enclosing expression so its grouping and evaluation order stay intact.
                self._shutdown_requested
                # What: apply the or self switching portion of the enclosing predicate; why: this clause remains in replace_catalog\'s enclosing expression so its grouping and evaluation order stay intact.
                or self._switching
                # What: apply the or self pending portion of the enclosing predicate; why: this clause remains in replace_catalog\'s enclosing expression so its grouping and evaluation order stay intact.
                or self._pending
                # What: apply the or self manual lifecycle tokens portion of the enclosing predicate; why: this clause remains in replace_catalog\'s enclosing expression so its grouping and evaluation order stay intact.
                or self._manual_lifecycle_tokens
            # What: complete the enclosing predicate with if self shutdown requested or self switching or self pending or self manual lifecycle tokens raise; why: RoutingCoordinator.replace_catalog groups the supplied clauses as one enclosing predicate expression before its value is consumed.
            ):
                # What: raise RoutingError for the caller; why: RoutingCoordinator.replace_catalog stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RoutingError(
                    # What: apply the reload conflict portion of the enclosing predicate; why: this clause remains in replace_catalog\'s enclosing expression so its grouping and evaluation order stay intact.
                    "reload_conflict",
                    # What: apply the cannot reload while admission or lifecycle portion of the enclosing predicate; why: this clause remains in replace_catalog\'s enclosing expression so its grouping and evaluation order stay intact.
                    "cannot reload while admission or lifecycle work is in progress",
                    # What: supply status code to RoutingError; why: replace_catalog binds this 409 value to RoutingError's status code input.
                    status_code=409,
                # What: complete the RoutingError call with status code; why: RoutingCoordinator.replace_catalog groups the supplied clauses as one RoutingError call before its value is consumed.
                )
            # What: gate on active name before replacement and current and catalog error and get and active name; why: replace_catalog admits replacement and current and catalog error and get and active name only for this predicate and excludes the opposite state.
            if self._active_name is not None:
                # What: establish the handler boundary for the protected operation; why: RoutingCoordinator.replace_catalog routes failures to catalog error while preserving cleanup and success flow.
                try:
                    # What: compute replacement from get and active name and catalog; why: replacement ttl s if replacement ttl s is not else later reads replacement, so replace_catalog must retain the computed value under that name.
                    replacement = catalog.get(self._active_name)
                    # What: compute current from get and active name and catalog; why: current ttl s if current ttl s is not else later reads current, so replace_catalog must retain the computed value under that name.
                    current = self._catalog.get(self._active_name)
                # What: handle catalog error by raise routing error; why: RoutingCoordinator.replace_catalog converts that failure into this concrete recovery, response, or cleanup behavior.
                except CatalogError as exc:
                    # What: raise RoutingError for the caller; why: RoutingCoordinator.replace_catalog stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise RoutingError(
                        # What: apply the reload conflict portion of the enclosing predicate; why: this clause remains in replace_catalog\'s enclosing expression so its grouping and evaluation order stay intact.
                        "reload_conflict",
                        # What: apply the cannot remove the active profile until portion of the enclosing predicate; why: this clause remains in replace_catalog\'s enclosing expression so its grouping and evaluation order stay intact.
                        "cannot remove the active profile until it is unloaded",
                        # What: supply status code to RoutingError; why: replace_catalog binds this 409 value to RoutingError's status code input.
                        status_code=409,
                    # What: apply the from exc portion of the enclosing predicate; why: this clause remains in replace_catalog\'s enclosing expression so its grouping and evaluation order stay intact.
                    ) from exc
                # What: compute current group from group for and active name and catalog; why: or replacement group current group later reads current group, so replace_catalog must retain the computed value under that name.
                current_group = self._catalog.group_for(self._active_name)
                # What: compute replacement group from group for and active name and catalog; why: or replacement group current group later reads replacement group, so replace_catalog must retain the computed value under that name.
                replacement_group = catalog.group_for(self._active_name)
                # What: compute current ttl from ttl s and default ttl s and current and settings; why: or replacement ttl current ttl later reads current ttl, so replace_catalog must retain the computed value under that name.
                current_ttl = (
                    # What: apply the current ttl s if current ttl s is not else portion of current ttl; why: replace_catalog uses this clause to evaluate current ttl as one grouped value.
                    current.ttl_s if current.ttl_s is not None else self._catalog.settings.default_ttl_s
                # What: complete the current_ttl expression with current ttl current ttl s if current ttl s is not else self catalog settings default ttl s; why: RoutingCoordinator.replace_catalog groups the supplied clauses as one current_ttl expression before its value is consumed.
                )
                # What: compute replacement ttl from ttl s and default ttl s and replacement and settings; why: or replacement ttl current ttl later reads replacement ttl, so replace_catalog must retain the computed value under that name.
                replacement_ttl = (
                    # What: apply the replacement ttl s if replacement ttl s is not else portion of replacement ttl; why: replace_catalog uses this clause to evaluate replacement ttl as one grouped value.
                    replacement.ttl_s if replacement.ttl_s is not None else catalog.settings.default_ttl_s
                # What: complete the replacement_ttl expression with replacement ttl replacement ttl s if replacement ttl s is not else catalog settings default ttl s; why: RoutingCoordinator.replace_catalog groups the supplied clauses as one replacement_ttl expression before its value is consumed.
                )
                # What: compute current unload timeout from unload timeout s and current and settings and catalog; why: or replacement unload timeout current unload timeout later reads current unload timeout, so replace_catalog must retain the computed value under that name.
                current_unload_timeout = (
                    # What: apply the current unload timeout s portion of current unload timeout; why: replace_catalog uses this clause to evaluate current unload timeout as one grouped value.
                    current.unload_timeout_s
                    # What: apply the if current unload timeout s is not portion of current unload timeout; why: replace_catalog uses this clause to evaluate current unload timeout as one grouped value.
                    if current.unload_timeout_s is not None
                    # What: apply the else self catalog settings unload timeout s portion of current unload timeout; why: replace_catalog uses this clause to evaluate current unload timeout as one grouped value.
                    else self._catalog.settings.unload_timeout_s
                # What: execute the grouped source fragment; why:  the enclosing symbol requires this operation for its concrete qualification or routing path.
                )
                # What: compute replacement unload timeout from unload timeout s and replacement and settings and catalog; why: or replacement unload timeout current unload timeout later reads replacement unload timeout, so replace_catalog must retain the computed value under that name.
                replacement_unload_timeout = (
                    # What: apply the replacement unload timeout s portion of replacement unload timeout; why: replace_catalog uses this clause to evaluate replacement unload timeout as one grouped value.
                    replacement.unload_timeout_s
                    # What: apply the if replacement unload timeout s is not portion of replacement unload timeout; why: replace_catalog uses this clause to evaluate replacement unload timeout as one grouped value.
                    if replacement.unload_timeout_s is not None
                    # What: apply the else catalog settings unload timeout s portion of replacement unload timeout; why: replace_catalog uses this clause to evaluate replacement unload timeout as one grouped value.
                    else catalog.settings.unload_timeout_s
                # What: execute the grouped source fragment; why:  the enclosing symbol requires this operation for its concrete qualification or routing path.
                )
                # What: gate on replacement and current and replacement group and current group and replacement ttl before routing error; why: replace_catalog admits routing error only for this predicate and excludes the opposite state.
                if (
                    # What: apply the replacement current portion of the enclosing predicate; why: this clause remains in replace_catalog\'s enclosing expression so its grouping and evaluation order stay intact.
                    replacement != current
                    # What: apply the or replacement group current group portion of the enclosing predicate; why: this clause remains in replace_catalog\'s enclosing expression so its grouping and evaluation order stay intact.
                    or replacement_group != current_group
                    # What: apply the or replacement ttl current ttl portion of the enclosing predicate; why: this clause remains in replace_catalog\'s enclosing expression so its grouping and evaluation order stay intact.
                    or replacement_ttl != current_ttl
                    # What: apply the or replacement unload timeout current unload timeout portion of the enclosing predicate; why: this clause remains in replace_catalog\'s enclosing expression so its grouping and evaluation order stay intact.
                    or replacement_unload_timeout != current_unload_timeout
                # What: complete the enclosing predicate with if replacement differs from current or replacement group differs from; why: RoutingCoordinator.replace_catalog groups the supplied clauses as one enclosing predicate expression before its value is consumed.
                ):
                    # What: raise RoutingError for the caller; why: RoutingCoordinator.replace_catalog stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise RoutingError(
                        # What: apply the reload conflict portion of the enclosing predicate; why: this clause remains in replace_catalog\'s enclosing expression so its grouping and evaluation order stay intact.
                        "reload_conflict",
                        # What: apply the cannot redefine the active profile until portion of the enclosing predicate; why: this clause remains in replace_catalog\'s enclosing expression so its grouping and evaluation order stay intact.
                        "cannot redefine the active profile until it is unloaded",
                        # What: supply status code to RoutingError; why: replace_catalog binds this 409 value to RoutingError's status code input.
                        status_code=409,
                    # What: complete the RoutingError call with status code; why: RoutingCoordinator.replace_catalog groups the supplied clauses as one RoutingError call before its value is consumed.
                    )
            # What: compute catalog from catalog; why: the enclosing return or state update later reads catalog, so replace_catalog must retain the computed value under that name.
            self._catalog = catalog
            # Match the pinned runtime contract: config reload starts with no
            # active routing profile rather than silently carrying pin state
            # into a potentially different profile definition.
            # What: compute active routing profile from the named fixture input; why: the enclosing return or state update later reads active routing profile, so replace_catalog must retain the computed value under that name.
            self._active_routing_profile = None
            # What: call self._cond.notify_all with the declared inputs; why: replace_catalog invokes self._cond.notify_all while performing the enclosing return; the call advances that operation through its result or side effect.
            self._cond.notify_all()

    # What: define prometheus around the current object state; why: its direct callers call prometheus for prometheus and rely on this exact input and result contract.
    def prometheus(self) -> str:
        """Render bounded router counters without importing a metrics package."""
        # What: document render bounded router counters without importing in the prometheus docstring; why: introspection and maintainers read this exact docstring fragment to understand prometheus behavior without executing it.
        # What: compute status from status; why: active requests status active requests later reads status, so prometheus must retain the computed value under that name.
        status = self.status()
        # What: compute values from status and int and active requests and reserved requests and queued requests; why: for name value in values items later reads values, so prometheus must retain the computed value under that name.
        values = {
            # What: map the active requests field as status and active requests; why: RoutingCoordinator.prometheus carries active requests through values into for name value in values items.
            "active_requests": status["activeRequests"],
            # What: map the reserved requests field as status and reserved requests; why: RoutingCoordinator.prometheus carries reserved requests through values into for name value in values items.
            "reserved_requests": status["reservedRequests"],
            # What: map the queued requests field as status and queued requests; why: RoutingCoordinator.prometheus carries queued requests through values into for name value in values items.
            "queued_requests": status["queuedRequests"],
            # What: map the shutting down field as int and status and shutting down; why: RoutingCoordinator.prometheus carries shutting down through values into for name value in values items.
            "shutting_down": int(status["shuttingDown"]),
            # What: map the active identity matches engine field as int and status and active identity matches engine; why: RoutingCoordinator.prometheus carries active identity matches engine through values into for name value in values items.
            "active_identity_matches_engine": int(status["activeIdentityMatchesEngine"]),
            # What: map the admissions total field as status and admissions; why: RoutingCoordinator.prometheus carries admissions total through values into for name value in values items.
            "admissions_total": status["admissions"],
            # What: map the activations total field as status and activations; why: RoutingCoordinator.prometheus carries activations total through values into for name value in values items.
            "activations_total": status["activations"],
            # What: map the activation failures total field as status and activation failures; why: RoutingCoordinator.prometheus carries activation failures total through values into for name value in values items.
            "activation_failures_total": status["activationFailures"],
            # What: map the cancellations total field as status and cancellations; why: RoutingCoordinator.prometheus carries cancellations total through values into for name value in values items.
            "cancellations_total": status["cancellations"],
            # What: map the terminal streams total field as status and terminal streams; why: RoutingCoordinator.prometheus carries terminal streams total through values into for name value in values items.
            "terminal_streams_total": status["terminalStreams"],
            # What: map the evictions total field as status and evictions; why: RoutingCoordinator.prometheus carries evictions total through values into for name value in values items.
            "evictions_total": status["evictions"],
        # What: complete the values mapping with active requests and reserved requests and queued requests and shutting down and active identity matches engine; why: RoutingCoordinator.prometheus groups the supplied clauses as one values mapping before its value is consumed.
        }
        # What: initialize lines as an empty runtime accumulator; why: RoutingCoordinator.prometheus appends or maps entries into it during lines extend f type metric metric type f metric before consuming the aggregate.
        lines = []
        # What: iterate across items and values to perform metric and name; why: prometheus repeats the body only while or for the loop header admits an iteration.
        for name, value in values.items():
            # What: compute metric from name and freetoken swap; why: lines extend f type metric metric type f later reads metric, so prometheus must retain the computed value under that name.
            metric = f"freetoken_swap_{name}"
            # What: compute metric type from endswith and name and counter and gauge and total; why: lines extend f type metric metric type f later reads metric type, so prometheus must retain the computed value under that name.
            metric_type = "counter" if name.endswith("_total") else "gauge"
            # What: preserve the exact lines extend f type metric metric type f literal fragment; why: prometheus passes this fragment verbatim through lines.extend((f"# TYPE {metric} {metric_type}", f"{metric} {value}")), because changing it would alter a protocol payload, serialized fixture, or public message.
            lines.extend((f"# TYPE {metric} {metric_type}", f"{metric} {value}"))
        # What: iterate across status to perform value and metric and extend and name and lines; why: prometheus repeats the body only while or for the loop header admits an iteration.
        for name, value in (
            # What: apply the last ttft ms status last ttft ms portion of the enclosing predicate; why: this clause remains in prometheus\'s enclosing expression so its grouping and evaluation order stay intact.
            ("last_ttft_ms", status["lastTtftMs"]),
            # What: apply the last duration ms status last duration ms portion of the enclosing predicate; why: this clause remains in prometheus\'s enclosing expression so its grouping and evaluation order stay intact.
            ("last_duration_ms", status["lastDurationMs"]),
            # What: apply the last activation ms status last activation ms portion of the enclosing predicate; why: this clause remains in prometheus\'s enclosing expression so its grouping and evaluation order stay intact.
            ("last_activation_ms", status["lastActivationMs"]),
            # What: apply the last queue wait ms status last queue wait ms portion of the enclosing predicate; why: this clause remains in prometheus\'s enclosing expression so its grouping and evaluation order stay intact.
            ("last_queue_wait_ms", status["lastQueueWaitMs"]),
            # What: apply the last response bytes status last response bytes portion of the enclosing predicate; why: this clause remains in prometheus\'s enclosing expression so its grouping and evaluation order stay intact.
            ("last_response_bytes", status["lastResponseBytes"]),
            # What: apply the last proxy bytes per second status last proxy bytes per second portion of the enclosing predicate; why: this clause remains in prometheus\'s enclosing expression so its grouping and evaluation order stay intact.
            ("last_proxy_bytes_per_second", status["lastProxyBytesPerSecond"]),
        # What: execute the grouped source fragment; why:  the enclosing symbol requires this operation for its concrete qualification or routing path.
        ):
            # What: gate on value before metric and name; why: prometheus admits metric and name only for this predicate and excludes the opposite state.
            if value is not None:
                # What: compute metric from name and freetoken swap; why: lines extend f type metric gauge f later reads metric, so prometheus must retain the computed value under that name.
                metric = f"freetoken_swap_{name}"
                # What: preserve the exact lines extend f type metric gauge f literal fragment; why: prometheus passes this fragment verbatim through lines.extend((f"# TYPE {metric} gauge", f"{metric} {value}")), because changing it would alter a protocol payload, serialized fixture, or public message.
                lines.extend((f"# TYPE {metric} gauge", f"{metric} {value}"))
        # What: return join and lines and value and value from prometheus; why: prometheus exposes join and lines and value and value so its caller can continue with the function\'s computed outcome.
        return "\n".join(lines) + "\n"

    # What: define record_cancellation around the current object state; why: its direct callers call record_cancellation for record cancellation and rely on this exact input and result contract.
    def record_cancellation(self) -> None:
        # What: enter the cond managed context before self cancellations; why: record_cancellation releases this resource or lock after self cancellations on both success and failure paths.
        with self._cond:
            # What: compute cancellations from 1; why: the enclosing return or state update later reads cancellations, so record_cancellation must retain the computed value under that name.
            self._cancellations += 1

    # What: define record_stream around ttft s and duration s and response bytes and completed; why: its direct callers call record_stream for record stream and rely on this exact input and result contract.
    def record_stream(
        # What: declare the self input for record_stream; why: record_stream consumes self during with self cond, so callers must bind it with the other signature inputs.
        self, *, ttft_s: float | None, duration_s: float, response_bytes: int, completed: bool = True
    # What: complete the enclosing predicate with group delimiter; why: RoutingCoordinator.record_stream groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ) -> None:
        """Record transport timing without crediting a router-cancelled stream as complete."""
        # What: document record transport timing without crediting a in the record_stream docstring; why: introspection and maintainers read this exact docstring fragment to understand record stream behavior without executing it.
        # What: enter the cond managed context before if completed; why: record_stream releases this resource or lock after if completed on both success and failure paths.
        with self._cond:
            # What: gate on completed before terminal streams; why: record_stream admits terminal streams only for this predicate and excludes the opposite state.
            if completed:
                # What: compute terminal streams from 1; why: the enclosing return or state update later reads terminal streams, so record_stream must retain the computed value under that name.
                self._terminal_streams += 1
            # What: compute last ttft ms from ttft s and round and 3 and 1000; why: the enclosing return or state update later reads last ttft ms, so record_stream must retain the computed value under that name.
            self._last_ttft_ms = round(ttft_s * 1000, 3) if ttft_s is not None else None
            # What: compute last duration ms from round and duration s and 3 and 1000; why: the enclosing return or state update later reads last duration ms, so record_stream must retain the computed value under that name.
            self._last_duration_ms = round(duration_s * 1000, 3)
            # What: compute last response bytes from response bytes; why: the enclosing return or state update later reads last response bytes, so record_stream must retain the computed value under that name.
            self._last_response_bytes = response_bytes
            # What: compute last proxy bytes per second from duration s and round and response bytes and 0 and 3; why: the enclosing return or state update later reads last proxy bytes per second, so record_stream must retain the computed value under that name.
            self._last_proxy_bytes_per_second = round(response_bytes / duration_s, 3) if duration_s > 0 else None

    # What: define evict_idle around name; why: its direct callers call evict_idle for evict idle and rely on this exact input and result contract.
    def evict_idle(self, name: str | None = None) -> bool:
        """Unload a truly idle matching engine, preserving lifecycle accounting.

        The timer calls this method, and tests may call it directly. A stale
        timer cannot unload a newer profile because identity is checked under
        admission before entering the manager lifecycle transaction.
        """
        # What: document unload a truly idle matching engine in the evict_idle docstring; why: introspection and maintainers read this exact docstring fragment to understand evict idle behavior without executing it.
        # What: document the timer calls this method and in the evict_idle docstring; why: introspection and maintainers read this exact docstring fragment to understand evict idle behavior without executing it.
        # What: document timer cannot unload a newer profile in the evict_idle docstring; why: introspection and maintainers read this exact docstring fragment to understand evict idle behavior without executing it.
        # What: document admission before entering the manager lifecycle in the evict_idle docstring; why: introspection and maintainers read this exact docstring fragment to understand evict idle behavior without executing it.
        # What: preserve the paragraph boundary in the the evict_idle docstring; why: introspection and maintainers read this paragraph break to understand evict idle behavior without executing it.
        # What: enter the cond managed context before if self shutdown requested; why: evict_idle releases this resource or lock after if self shutdown requested on both success and failure paths.
        with self._cond:
            # What: gate on shutdown requested before the computed value; why: evict_idle admits the computed value only for this predicate and excludes the opposite state.
            if self._shutdown_requested:
                # What: return false from evict_idle; why: evict_idle exposes false so its caller can continue with the function\'s computed outcome.
                return False
            # What: gate on name before name and catalog error and get and catalog; why: evict_idle admits name and catalog error and get and catalog only for this predicate and excludes the opposite state.
            if name is not None:
                # What: establish the handler boundary for the protected operation; why: RoutingCoordinator.evict_idle routes failures to catalog error while preserving cleanup and success flow.
                try:
                    # What: compute name from name and get and catalog; why: if name is not and active later reads name, so evict_idle must retain the computed value under that name.
                    name = self._catalog.get(name).name
                # What: handle catalog error by return false; why: RoutingCoordinator.evict_idle converts that failure into this concrete recovery, response, or cleanup behavior.
                except CatalogError:
                    # What: return false from evict_idle; why: evict_idle exposes false so its caller can continue with the function\'s computed outcome.
                    return False
            # What: compute active from active name; why: if name is not and active later reads active, so evict_idle must retain the computed value under that name.
            active = self._active_name
            # What: gate on name and active before the computed value; why: evict_idle admits the computed value only for this predicate and excludes the opposite state.
            if name is not None and active != name:
                # What: return false from evict_idle; why: evict_idle exposes false so its caller can continue with the function\'s computed outcome.
                return False
            # What: gate on leases and switching and active before the computed value; why: evict_idle admits the computed value only for this predicate and excludes the opposite state.
            if active is None or self._leases or self._switching:
                # What: return false from evict_idle; why: evict_idle exposes false so its caller can continue with the function\'s computed outcome.
                return False
            # What: compute profile from get and active and catalog; why: port self port for profile later reads profile, so evict_idle must retain the computed value under that name.
            profile = self._catalog.get(active)
            # What: compute port from port for and profile; why: if not self matches active profile port later reads port, so evict_idle must retain the computed value under that name.
            port = self._port_for(profile)
            # What: gate on matches active and profile and port before active name; why: evict_idle admits active name only for this predicate and excludes the opposite state.
            if not self._matches_active(profile, port):
                # What: compute active name from the named fixture input; why: self active name later reads active name, so evict_idle must retain the computed value under that name.
                self._active_name = None
                # What: compute idle timer from the named fixture input; why: self idle timer later reads idle timer, so evict_idle must retain the computed value under that name.
                self._idle_timer = None
                # What: call self._cond.notify_all with the declared inputs; why: evict_idle invokes self._cond.notify_all while performing return; the call advances that operation through its result or side effect.
                self._cond.notify_all()
                # What: return false from evict_idle; why: evict_idle exposes false so its caller can continue with the function\'s computed outcome.
                return False
            # What: compute switching from true; why: self switching later reads switching, so evict_idle must retain the computed value under that name.
            self._switching = True
            # What: compute idle timer from the named fixture input; why: the enclosing return or state update later reads idle timer, so evict_idle must retain the computed value under that name.
            self._idle_timer = None
        # What: establish the handler boundary for the protected operation; why: RoutingCoordinator.evict_idle routes failures to exception while preserving cleanup and success flow.
        try:
            # What: compute timeout from unload timeout s and profile and settings and catalog; why: self manager stop timeout timeout later reads timeout, so evict_idle must retain the computed value under that name.
            timeout = profile.unload_timeout_s or self._catalog.settings.unload_timeout_s
            # What: supply timeout to self._manager.stop; why: evict_idle binds this timeout value to self._manager.stop's timeout input.
            self._manager.stop(timeout=timeout)
        # What: handle exception by with self cond; why: RoutingCoordinator.evict_idle converts that failure into this concrete recovery, response, or cleanup behavior.
        except Exception:
            # What: enter the cond managed context before self switching; why: evict_idle releases this resource or lock after self switching on both success and failure paths.
            with self._cond:
                # What: compute switching from false; why: self switching later reads switching, so evict_idle must retain the computed value under that name.
                self._switching = False
                # What: call self._cond.notify_all with the declared inputs; why: evict_idle invokes self._cond.notify_all while performing raise; the call advances that operation through its result or side effect.
                self._cond.notify_all()
            # What: re-propagate the active failure to the caller; why: RoutingCoordinator.evict_idle stops this rejected path before it can mutate state, dispatch work, or report success.
            raise
        # What: enter the cond managed context before self active name; why: evict_idle releases this resource or lock after self active name on both success and failure paths.
        with self._cond:
            # What: compute active name from the named fixture input; why: the enclosing return or state update later reads active name, so evict_idle must retain the computed value under that name.
            self._active_name = None
            # What: compute switching from false; why: the enclosing return or state update later reads switching, so evict_idle must retain the computed value under that name.
            self._switching = False
            # What: compute evictions from 1; why: the enclosing return or state update later reads evictions, so evict_idle must retain the computed value under that name.
            self._evictions += 1
            # What: call self._cond.notify_all with the declared inputs; why: evict_idle invokes self._cond.notify_all while performing return; the call advances that operation through its result or side effect.
            self._cond.notify_all()
        # What: return true from evict_idle; why: evict_idle exposes true so its caller can continue with the function\'s computed outcome.
        return True

    # What: define begin_shutdown around the current object state; why: its direct callers call begin_shutdown for begin shutdown and rely on this exact input and result contract.
    def begin_shutdown(self) -> object:
        """Close admission immediately, before executor-side lifecycle work can queue."""
        # What: document close admission immediately before executor side lifecycle in the begin_shutdown docstring; why: introspection and maintainers read this exact docstring fragment to understand begin shutdown behavior without executing it.
        # What: enter the cond managed context before if self shutdown requested; why: begin_shutdown releases this resource or lock after if self shutdown requested on both success and failure paths.
        with self._cond:
            # What: gate on shutdown requested before routing error; why: begin_shutdown admits routing error only for this predicate and excludes the opposite state.
            if self._shutdown_requested:
                # What: raise RoutingError for the caller; why: RoutingCoordinator.begin_shutdown stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RoutingError(
                    # What: supply status code to RoutingError; why: begin_shutdown binds this 409 value to RoutingError's status code input.
                    "router_shutting_down", "router shutdown is already in progress", status_code=409
                # What: complete the RoutingError call with status code; why: RoutingCoordinator.begin_shutdown groups the supplied clauses as one RoutingError call before its value is consumed.
                )
            # What: compute owner from object; why: self shutdown owner owner later reads owner, so begin_shutdown must retain the computed value under that name.
            owner = object()
            # What: compute shutdown requested from true; why: the enclosing return or state update later reads shutdown requested, so begin_shutdown must retain the computed value under that name.
            self._shutdown_requested = True
            # What: compute shutdown owner from owner; why: the enclosing return or state update later reads shutdown owner, so begin_shutdown must retain the computed value under that name.
            self._shutdown_owner = owner
            # What: call self._cancel_idle_timer with the declared inputs; why: begin_shutdown invokes self._cancel_idle_timer while performing self cond notify all; the call advances that operation through its result or side effect.
            self._cancel_idle_timer()
            # What: call self._cond.notify_all with the declared inputs; why: begin_shutdown invokes self._cond.notify_all while performing return owner; the call advances that operation through its result or side effect.
            self._cond.notify_all()
            # What: return owner from begin_shutdown; why: begin_shutdown exposes owner so its caller can continue with the function\'s computed outcome.
            return owner

    # What: define finish_shutdown around owner and timeout and force; why: its direct callers call finish_shutdown for finish shutdown and rely on this exact input and result contract.
    def finish_shutdown(
        # What: declare the self input for finish_shutdown; why: finish_shutdown consumes self during return self finish exit owner lambda self manager shutdown timeout, so callers must bind it with the other signature inputs.
        self, owner: object, timeout: float | None = None, force: bool = False
    # What: complete the enclosing predicate with dict; why: RoutingCoordinator.finish_shutdown groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ) -> dict:
        """Drain existing ownership and permanently stop the sole managed child."""
        # What: document drain existing ownership and permanently stop in the finish_shutdown docstring; why: introspection and maintainers read this exact docstring fragment to understand finish shutdown behavior without executing it.
        # What: return finish exit and owner and shutdown and timeout from finish_shutdown; why: finish_shutdown exposes finish exit and owner and shutdown and timeout so its caller can continue with the function\'s computed outcome.
        return self._finish_exit(owner, lambda: self._manager.shutdown(timeout, force))

    # What: define finish_detach around owner; why: its direct callers call finish_detach for finish detach and rely on this exact input and result contract.
    def finish_detach(self, owner: object) -> None:
        """Drain existing ownership, then leave the child persisted for re-adoption."""
        # What: document drain existing ownership then leave the in the finish_detach docstring; why: introspection and maintainers read this exact docstring fragment to understand finish detach behavior without executing it.
        # What: call self._finish_exit with owner and detach and manager; why: finish_detach invokes self._finish_exit while performing the enclosing return; the call advances that operation through its result or side effect.
        self._finish_exit(owner, self._manager.detach)

    # What: define _finish_exit around owner and action; why: its direct callers call _finish_exit for finish exit and rely on this exact input and result contract.
    def _finish_exit(self, owner: object, action: Callable[[], object]):
        # What: enter the cond managed context before if self shutdown owner is not owner; why: _finish_exit releases this resource or lock after if self shutdown owner is not owner on both success and failure paths.
        with self._cond:
            # What: gate on shutdown owner and owner before value error; why: _finish_exit admits value error only for this predicate and excludes the opposite state.
            if self._shutdown_owner is not owner:
                # What: raise ValueError for the caller; why: RoutingCoordinator._finish_exit stops this rejected path before it can mutate state, dispatch work, or report success.
                raise ValueError("shutdown reservation is not owned by caller")
            # What: iterate across leases and switching and manual lifecycle tokens to perform wait and cond; why: _finish_exit repeats the body only while or for the loop header admits an iteration.
            while self._leases or self._switching or self._manual_lifecycle_tokens:
                # What: call self._cond.wait with the declared inputs; why: _finish_exit invokes self._cond.wait while performing self switching; the call advances that operation through its result or side effect.
                self._cond.wait()
            # What: compute switching from true; why: self switching later reads switching, so _finish_exit must retain the computed value under that name.
            self._switching = True
        # What: establish the handler boundary for the protected operation; why: RoutingCoordinator._finish_exit routes failures to exception while preserving cleanup and success flow.
        try:
            # What: compute result from action; why: return result later reads result, so _finish_exit must retain the computed value under that name.
            result = action()
        # What: handle exception by with self cond; why: RoutingCoordinator._finish_exit converts that failure into this concrete recovery, response, or cleanup behavior.
        except Exception:
            # What: enter the cond managed context before self shutdown requested; why: _finish_exit releases this resource or lock after self shutdown requested on both success and failure paths.
            with self._cond:
                # What: compute shutdown requested from false; why: the enclosing return or state update later reads shutdown requested, so _finish_exit must retain the computed value under that name.
                self._shutdown_requested = False
                # What: compute shutdown owner from the named fixture input; why: self shutdown owner later reads shutdown owner, so _finish_exit must retain the computed value under that name.
                self._shutdown_owner = None
                # What: compute switching from false; why: self switching later reads switching, so _finish_exit must retain the computed value under that name.
                self._switching = False
                # What: call self._schedule_idle_eviction with the declared inputs; why: _finish_exit invokes self._schedule_idle_eviction while performing self cond notify all; the call advances that operation through its result or side effect.
                self._schedule_idle_eviction()
                # What: call self._cond.notify_all with the declared inputs; why: _finish_exit invokes self._cond.notify_all while performing raise; the call advances that operation through its result or side effect.
                self._cond.notify_all()
            # What: re-propagate the active failure to the caller; why: RoutingCoordinator._finish_exit stops this rejected path before it can mutate state, dispatch work, or report success.
            raise
        # What: enter the cond managed context before self active name; why: _finish_exit releases this resource or lock after self active name on both success and failure paths.
        with self._cond:
            # What: compute active name from the named fixture input; why: the enclosing return or state update later reads active name, so _finish_exit must retain the computed value under that name.
            self._active_name = None
            # What: compute shutdown owner from the named fixture input; why: the enclosing return or state update later reads shutdown owner, so _finish_exit must retain the computed value under that name.
            self._shutdown_owner = None
            # What: compute switching from false; why: the enclosing return or state update later reads switching, so _finish_exit must retain the computed value under that name.
            self._switching = False
            # What: call self._cond.notify_all with the declared inputs; why: _finish_exit invokes self._cond.notify_all while performing return result; the call advances that operation through its result or side effect.
            self._cond.notify_all()
        # What: return result from _finish_exit; why: _finish_exit exposes result so its caller can continue with the function\'s computed outcome.
        return result

    # What: define shutdown around timeout and force; why: its direct callers call shutdown for shutdown and rely on this exact input and result contract.
    def shutdown(self, timeout: float | None = None, force: bool = False) -> dict:
        """Synchronous convenience wrapper for a complete shutdown transaction."""
        # What: document synchronous convenience wrapper for a complete in the shutdown docstring; why: introspection and maintainers read this exact docstring fragment to understand shutdown behavior without executing it.
        # What: return finish shutdown and timeout and force and begin shutdown from shutdown; why: shutdown exposes finish shutdown and timeout and force and begin shutdown so its caller can continue with the function\'s computed outcome.
        return self.finish_shutdown(self.begin_shutdown(), timeout, force)

    # What: define coordinated_exit around stop child; why: its direct callers call coordinated_exit for coordinated exit and rely on this exact input and result contract.
    def coordinated_exit(self, *, stop_child: bool) -> object | None:
        """Idempotently quiesce for an OS/lifespan exit using the configured child policy."""
        # What: document idempotently quiesce for an os lifespan in the coordinated_exit docstring; why: introspection and maintainers read this exact docstring fragment to understand coordinated exit behavior without executing it.
        # What: iterate across the computed value to perform owner and routing error and begin shutdown and cond and shutdown requested; why: coordinated_exit repeats the body only while or for the loop header admits an iteration.
        while True:
            # What: establish the handler boundary for the protected operation; why: RoutingCoordinator.coordinated_exit routes failures to routing error while preserving cleanup and success flow.
            try:
                # What: compute owner from begin shutdown; why: return self finish shutdown owner later reads owner, so coordinated_exit must retain the computed value under that name.
                owner = self.begin_shutdown()
                # What: apply the break portion of the enclosing predicate; why: this clause remains in coordinated_exit\'s enclosing expression so its grouping and evaluation order stay intact.
                break
            # What: handle routing error by with self cond; why: RoutingCoordinator.coordinated_exit converts that failure into this concrete recovery, response, or cleanup behavior.
            except RoutingError:
                # What: enter the cond managed context before while self shutdown owner is not; why: coordinated_exit releases this resource or lock after while self shutdown owner is not on both success and failure paths.
                with self._cond:
                    # What: iterate across shutdown owner to perform wait and cond; why: coordinated_exit repeats the body only while or for the loop header admits an iteration.
                    while self._shutdown_owner is not None:
                        # What: call self._cond.wait with the declared inputs; why: coordinated_exit invokes self._cond.wait while performing if self shutdown requested; the call advances that operation through its result or side effect.
                        self._cond.wait()
                    # What: gate on shutdown requested before the computed value; why: coordinated_exit admits the computed value only for this predicate and excludes the opposite state.
                    if self._shutdown_requested:
                        # What: return no value from coordinated_exit; why: coordinated_exit returns no value to callers that depend on its completed result.
                        return None
        # What: gate on stop child before finish shutdown and owner; why: coordinated_exit admits finish shutdown and owner only for this predicate and excludes the opposite state.
        if stop_child:
            # What: return finish shutdown and owner from coordinated_exit; why: coordinated_exit exposes finish shutdown and owner so its caller can continue with the function\'s computed outcome.
            return self.finish_shutdown(owner)
        # What: return finish detach and owner from coordinated_exit; why: coordinated_exit exposes finish detach and owner so its caller can continue with the function\'s computed outcome.
        return self.finish_detach(owner)

    # What: apply staticmethod behavior to _new_timer; why: Python attaches this named decorator's registration or descriptor semantics to _new_timer.
    @staticmethod
    # What: define _new_timer around delay and callback; why: the registered API client call _new_timer for new timer and rely on this exact input and result contract.
    def _new_timer(delay: float, callback: Callable[[], None]):
        # What: compute timer from timer and delay and callback and threading; why: timer daemon later reads timer, so _new_timer must retain the computed value under that name.
        timer = threading.Timer(delay, callback)
        # What: compute daemon from true; why: the enclosing return or state update later reads daemon, so _new_timer must retain the computed value under that name.
        timer.daemon = True
        # What: return timer from _new_timer; why: _new_timer exposes timer so its caller can continue with the function\'s computed outcome.
        return timer

    # What: define _cancel_idle_timer around the current object state; why: its direct callers call _cancel_idle_timer for cancel idle timer and rely on this exact input and result contract.
    def _cancel_idle_timer(self) -> None:
        # What: gate on idle timer before cancel and idle timer; why: _cancel_idle_timer admits cancel and idle timer only for this predicate and excludes the opposite state.
        if self._idle_timer is not None:
            # What: call self._idle_timer.cancel with the declared inputs; why: _cancel_idle_timer invokes self._idle_timer.cancel while performing self idle timer; the call advances that operation through its result or side effect.
            self._idle_timer.cancel()
            # What: compute idle timer from the named fixture input; why: the enclosing return or state update later reads idle timer, so _cancel_idle_timer must retain the computed value under that name.
            self._idle_timer = None

    # What: define _schedule_idle_eviction around the current object state; why: its direct callers call _schedule_idle_eviction for schedule idle eviction and rely on this exact input and result contract.
    def _schedule_idle_eviction(self) -> None:
        # What: gate on active name before the computed value; why: _schedule_idle_eviction admits the computed value only for this predicate and excludes the opposite state.
        if self._active_name is None:
            # What: return no value from _schedule_idle_eviction; why: _schedule_idle_eviction returns no value to callers that depend on its completed result.
            return
        # What: compute profile from get and active name and catalog; why: ttl profile ttl s if profile ttl s is not later reads profile, so _schedule_idle_eviction must retain the computed value under that name.
        profile = self._catalog.get(self._active_name)
        # What: compute ttl from ttl s and default ttl s and profile and settings; why: if ttl later reads ttl, so _schedule_idle_eviction must retain the computed value under that name.
        ttl = profile.ttl_s if profile.ttl_s is not None else self._catalog.settings.default_ttl_s
        # What: gate on ttl before the computed value; why: _schedule_idle_eviction admits the computed value only for this predicate and excludes the opposite state.
        if ttl <= 0:
            # What: return no value from _schedule_idle_eviction; why: _schedule_idle_eviction returns no value to callers that depend on its completed result.
            return
        # What: call self._cancel_idle_timer with the declared inputs; why: _schedule_idle_eviction invokes self._cancel_idle_timer while performing timer self timer factory ttl lambda self evict idle profile name; the call advances that operation through its result or side effect.
        self._cancel_idle_timer()
        # What: compute timer from timer factory and ttl and evict idle and name; why: self idle timer timer later reads timer, so _schedule_idle_eviction must retain the computed value under that name.
        timer = self._timer_factory(ttl, lambda: self.evict_idle(profile.name))
        # What: compute idle timer from timer; why: the enclosing return or state update later reads idle timer, so _schedule_idle_eviction must retain the computed value under that name.
        self._idle_timer = timer
        # What: call timer.start with the declared inputs; why: _schedule_idle_eviction invokes timer.start while performing the enclosing return; the call advances that operation through its result or side effect.
        timer.start()

    # What: define _capacity_block around target; why: its direct callers call _capacity_block for capacity block and rely on this exact input and result contract.
    def _capacity_block(self, target: ModelProfile) -> str | None:
        """Return a capacity-policy explanation, if a swap cannot be admitted."""
        # What: document return a capacity policy explanation if a in the _capacity_block docstring; why: introspection and maintainers read this exact docstring fragment to understand capacity block behavior without executing it.
        # What: gate on active name and name and target before the computed value; why: _capacity_block admits the computed value only for this predicate and excludes the opposite state.
        if self._active_name is None or self._active_name == target.name:
            # What: return no value from _capacity_block; why: _capacity_block returns no value to callers that depend on its completed result.
            return None
        # What: compute active group from group for and active name and catalog; why: if active group is not and active group persistent later reads active group, so _capacity_block must retain the computed value under that name.
        active_group = self._catalog.group_for(self._active_name)
        # What: compute target group from group for and name and catalog and target; why: if target group is not and target group persistent later reads target group, so _capacity_block must retain the computed value under that name.
        target_group = self._catalog.group_for(target.name)
        # What: gate on persistent and active group before active name; why: _capacity_block admits active name only for this predicate and excludes the opposite state.
        if active_group is not None and active_group.persistent:
            # What: return active name and active and profile and is and persistent from _capacity_block; why: _capacity_block exposes active name and active and profile and is and persistent so its caller can continue with the function\'s computed outcome.
            return (
                # What: preserve the exact f active profile self active name r is literal fragment; why: _capacity_block passes this fragment verbatim through f"active profile {self._active_name!r} is persistent and consumes the ", because changing it would alter a protocol payload, serialized fixture, or public messa.
                # What: preserve the exact single resident model slot unload it before literal fragment; why: _capacity_block passes this fragment verbatim through f"active profile {self._active_name!r} is persistent and consumes the ", because changing it would alter a protocol payload, serialized fixture, or public.
                f"active profile {self._active_name!r} is persistent and consumes the "
                "single resident-model slot; unload it before selecting another profile"
            # What: complete the enclosing predicate with return f active profile self active name r is persistent and; why: RoutingCoordinator._capacity_block groups the supplied clauses as one enclosing predicate expression before its value is consumed.
            )
        # What: gate on persistent and target group before name and target; why: _capacity_block admits name and target only for this predicate and excludes the opposite state.
        if target_group is not None and target_group.persistent:
            # What: return name and target and profile and requires and a from _capacity_block; why: _capacity_block exposes name and target and profile and requires and a so its caller can continue with the function\'s computed outcome.
            return (
                # What: preserve the exact f profile target name r requires a literal fragment; why: _capacity_block passes this fragment verbatim through f"profile {target.name!r} requires a persistent resident slot; unload th, because changing it would alter a protocol payload, serialized fixture, or public message.
                # What: preserve the exact current profile before selecting it literal fragment; why: _capacity_block passes this fragment verbatim through f"profile {target.name!r} requires a persistent resident slot; unload th, because changing it would alter a protocol payload, serialized fixture, or public message.
                f"profile {target.name!r} requires a persistent resident slot; unload the "
                "current profile before selecting it"
            # What: complete the enclosing predicate with return f profile target name r requires a persistent resident; why: RoutingCoordinator._capacity_block groups the supplied clauses as one enclosing predicate expression before its value is consumed.
            )
        # What: return no value from _capacity_block; why: _capacity_block returns no value to callers that depend on its completed result.
        return None

    # What: define _remove_pending_locked around ticket and cancellation; why: its direct callers call _remove_pending_locked for remove pending locked and rely on this exact input and result contract.
    def _remove_pending_locked(
        # What: declare the self input for _remove_pending_locked; why: _remove_pending_locked consumes self during self pending remove ticket, so callers must bind it with the other signature inputs.
        self,
        # What: declare the ticket input for _remove_pending_locked; why: _remove_pending_locked consumes ticket during self pending remove ticket, so callers must bind it with the other signature inputs.
        ticket: tuple[int, int, str],
        # What: declare the cancellation input for _remove_pending_locked; why: _remove_pending_locked consumes cancellation during pending self pending by cancellation get cancellation if cancellation is, so callers must bind it with the other signature inputs.
        cancellation: threading.Event | None,
    # What: complete the enclosing predicate with bool; why: RoutingCoordinator._remove_pending_locked groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ) -> bool:
        """Idempotently remove one ticket and its optional progress lookup."""
        # What: document idempotently remove one ticket and its in the _remove_pending_locked docstring; why: introspection and maintainers read this exact docstring fragment to understand remove pending locked behavior without executing it.
        # What: establish the handler boundary for the protected operation; why: RoutingCoordinator._remove_pending_locked routes failures to value error while preserving cleanup and success flow.
        try:
            # What: call self._pending.remove with ticket; why: _remove_pending_locked invokes self._pending.remove while performing except value error; the call advances that operation through its result or side effect.
            self._pending.remove(ticket)
        # What: handle value error by removed false; why: RoutingCoordinator._remove_pending_locked converts that failure into this concrete recovery, response, or cleanup behavior.
        except ValueError:
            # What: compute removed from false; why: removed later reads removed, so _remove_pending_locked must retain the computed value under that name.
            removed = False
        # What: select the remaining branch that performs removed; why: _remove_pending_locked covers the state excluded by the preceding predicate without conflating the two outcomes.
        else:
            # What: compute removed from true; why: return removed later reads removed, so _remove_pending_locked must retain the computed value under that name.
            removed = True
        # What: compute pending from cancellation and get and pending by cancellation; why: if pending is not and pending later reads pending, so _remove_pending_locked must retain the computed value under that name.
        pending = self._pending_by_cancellation.get(cancellation) if cancellation is not None else None
        # What: gate on pending and ticket before pop and cancellation and pending by cancellation; why: _remove_pending_locked admits pop and cancellation and pending by cancellation only for this predicate and excludes the opposite state.
        if pending is not None and pending[0] == ticket:
            # What: call self._pending_by_cancellation.pop with cancellation and the named fixture input; why: _remove_pending_locked invokes self._pending_by_cancellation.pop while performing return removed; the call advances that operation through its result or side effect.
            self._pending_by_cancellation.pop(cancellation, None)
        # What: return removed from _remove_pending_locked; why: _remove_pending_locked exposes removed so its caller can continue with the function\'s computed outcome.
        return removed

    # What: define _active_profile_ready_locked around profile; why: its direct callers call _active_profile_ready_locked for active profile ready locked and rely on this exact input and result contract.
    def _active_profile_ready_locked(self, profile: ModelProfile) -> bool:
        """Whether *profile* is the exact readiness-gated resident engine."""
        # What: document whether profile is the exact readiness gated in the _active_profile_ready_locked docstring; why: introspection and maintainers read this exact docstring fragment to understand active profile ready locked behavior without executing it.
        # What: gate on active name and name and profile before the computed value; why: _active_profile_ready_locked admits the computed value only for this predicate and excludes the opposite state.
        if self._active_name != profile.name:
            # What: return false from _active_profile_ready_locked; why: _active_profile_ready_locked exposes false so its caller can continue with the function\'s computed outcome.
            return False
        # What: return engine matches and profile and port for from _active_profile_ready_locked; why: _active_profile_ready_locked exposes engine matches and profile and port for so its caller can continue with the function\'s computed outcome.
        return self._engine_matches(profile, self._port_for(profile))

    # What: define _reserve_concurrency_locked around profile; why: its direct callers call _reserve_concurrency_locked for reserve concurrency locked and rely on this exact input and result contract.
    def _reserve_concurrency_locked(self, profile: ModelProfile) -> None:
        """Reserve active/queued capacity or reject immediately like the pinned scheduler."""
        # What: document reserve active queued capacity or reject in the _reserve_concurrency_locked docstring; why: introspection and maintainers read this exact docstring fragment to understand reserve concurrency locked behavior without executing it.
        # What: compute global limit from global concurrency limit and settings and catalog; why: if global limit and self reservations global limit or later reads global limit, so _reserve_concurrency_locked must retain the computed value under that name.
        global_limit = self._catalog.settings.global_concurrency_limit
        # What: compute profile limit from concurrency limit and default profile concurrency limit and profile; why: if global limit and self reservations global limit or later reads profile limit, so _reserve_concurrency_locked must retain the computed value under that name.
        profile_limit = profile.concurrency_limit or DEFAULT_PROFILE_CONCURRENCY_LIMIT
        # What: compute profile reserved from get and name and profile reservations and profile and 0; why: if global limit and self reservations global limit or later reads profile reserved, so _reserve_concurrency_locked must retain the computed value under that name.
        profile_reserved = self._profile_reservations.get(profile.name, 0)
        # What: gate on global limit and profile reserved and profile limit and reservations before routing error and name and profile; why: _reserve_concurrency_locked admits routing error and name and profile only for this predicate and excludes the opposite state.
        if (global_limit and self._reservations >= global_limit) or profile_reserved >= profile_limit:
            # What: raise RoutingError for the caller; why: RoutingCoordinator._reserve_concurrency_locked stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RoutingError(
                # What: apply the concurrency limit portion of the enclosing predicate; why: this clause remains in _reserve_concurrency_locked\'s enclosing expression so its grouping and evaluation order stay intact.
                "concurrency_limit",
                # What: apply the f concurrency limit reached for profile portion of the enclosing predicate; why: this clause remains in _reserve_concurrency_locked\'s enclosing expression so its grouping and evaluation order stay intact.
                f"concurrency limit reached for profile {profile.name!r}",
                # What: supply status code to RoutingError; why: _reserve_concurrency_locked binds this 429 value to RoutingError's status code input.
                status_code=429,
            # What: complete the RoutingError call with status code; why: RoutingCoordinator._reserve_concurrency_locked groups the supplied clauses as one RoutingError call before its value is consumed.
            )
        # What: compute reservations from 1; why: the enclosing return or state update later reads reservations, so _reserve_concurrency_locked must retain the computed value under that name.
        self._reservations += 1
        # What: compute profile reservations entry from profile reserved and 1; why: the enclosing return or state update later reads profile reservations entry, so _reserve_concurrency_locked must retain the computed value under that name.
        self._profile_reservations[profile.name] = profile_reserved + 1

    # What: define _drop_concurrency_reservation_locked around profile; why: its direct callers call _drop_concurrency_reservation_locked for drop concurrency reservation locked and rely on this exact input and result contract.
    def _drop_concurrency_reservation_locked(self, profile: ModelProfile) -> None:
        # What: compute count from get and name and profile reservations and profile and 0; why: if self reservations or count later reads count, so _drop_concurrency_reservation_locked must retain the computed value under that name.
        count = self._profile_reservations.get(profile.name, 0)
        # What: gate on reservations and count before runtime error; why: _drop_concurrency_reservation_locked admits runtime error only for this predicate and excludes the opposite state.
        if self._reservations <= 0 or count <= 0:
            # What: raise RuntimeError for the caller; why: RoutingCoordinator._drop_concurrency_reservation_locked stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RuntimeError("routing concurrency reservation underflow")
        # What: compute reservations from 1; why: the enclosing return or state update later reads reservations, so _drop_concurrency_reservation_locked must retain the computed value under that name.
        self._reservations -= 1
        # What: gate on count before pop and name and profile reservations and profile; why: _drop_concurrency_reservation_locked admits pop and name and profile reservations and profile only for this predicate and excludes the opposite state.
        if count == 1:
            # What: call self._profile_reservations.pop with name and profile; why: _drop_concurrency_reservation_locked invokes self._profile_reservations.pop while performing else; the call advances that operation through its result or side effect.
            self._profile_reservations.pop(profile.name)
        # What: select the remaining branch that performs self profile reservations profile name count; why: _drop_concurrency_reservation_locked covers the state excluded by the preceding predicate without conflating the two outcomes.
        else:
            # What: compute profile reservations entry from count and 1; why: the enclosing return or state update later reads profile reservations entry, so _drop_concurrency_reservation_locked must retain the computed value under that name.
            self._profile_reservations[profile.name] = count - 1

    # What: define _matches_active around profile and port; why: its direct callers call _matches_active for matches active and rely on this exact input and result contract.
    def _matches_active(self, profile: ModelProfile, port: int) -> bool:
        # What: return active name and name and engine matches and profile from _matches_active; why: _matches_active exposes active name and name and engine matches and profile so its caller can continue with the function\'s computed outcome.
        return self._active_name == profile.name and self._engine_matches(profile, port)

    # What: define _engine_matches around profile and port; why: its direct callers call _engine_matches for engine matches and rely on this exact input and result contract.
    def _engine_matches(self, profile: ModelProfile, port: int) -> bool:
        # What: compute state from status and manager; why: state get running later reads state, so _engine_matches must retain the computed value under that name.
        state = self._manager.status()
        # What: return bool and get and model and port from _engine_matches; why: _engine_matches exposes bool and get and model and port so its caller can continue with the function\'s computed outcome.
        return bool(
            # What: call state.get with running; why: _engine_matches invokes state.get while performing and state get model profile model; the call advances that operation through its result or side effect.
            state.get("running")
            # What: call state.get with model; why: _engine_matches invokes state.get while performing and state get port port; the call advances that operation through its result or side effect.
            and state.get("model") == profile.model
            # What: call state.get with port; why: _engine_matches invokes state.get while performing and self manager serve args list profile args; the call advances that operation through its result or side effect.
            and state.get("port") == port
            # What: call self._manager.serve_args with the declared inputs; why: _engine_matches consumes the self._manager.serve_args return value while evaluating and self._manager.serve_args() == list(profile.args).
            and self._manager.serve_args() == list(profile.args)
        # What: complete the bool call with get; why: RoutingCoordinator._engine_matches groups the supplied clauses as one bool call before its value is consumed.
        )

    # What: define _active_matches_engine_locked around the current object state; why: its direct callers call _active_matches_engine_locked for active matches engine locked and rely on this exact input and result contract.
    def _active_matches_engine_locked(self) -> bool:
        """Internal exact-identity check; caller holds ``self._cond``."""
        # What: document internal exact identity check caller holds self cond in the _active_matches_engine_locked docstring; why: introspection and maintainers read this exact docstring fragment to understand active matches engine locked behavior without executing it.
        # What: gate on active name before the computed value; why: _active_matches_engine_locked admits the computed value only for this predicate and excludes the opposite state.
        if self._active_name is None:
            # What: return false from _active_matches_engine_locked; why: _active_matches_engine_locked exposes false so its caller can continue with the function\'s computed outcome.
            return False
        # What: establish the handler boundary for the protected operation; why: RoutingCoordinator._active_matches_engine_locked routes failures to catalog error while preserving cleanup and success flow.
        try:
            # What: compute profile from get and active name and catalog; why: return self matches active profile self port for profile later reads profile, so _active_matches_engine_locked must retain the computed value under that name.
            profile = self._catalog.get(self._active_name)
        # What: handle catalog error by return false; why: RoutingCoordinator._active_matches_engine_locked converts that failure into this concrete recovery, response, or cleanup behavior.
        except CatalogError:
            # What: return false from _active_matches_engine_locked; why: _active_matches_engine_locked exposes false so its caller can continue with the function\'s computed outcome.
            return False
        # What: return matches active and profile and port for from _active_matches_engine_locked; why: _active_matches_engine_locked exposes matches active and profile and port for so its caller can continue with the function\'s computed outcome.
        return self._matches_active(profile, self._port_for(profile))

    # What: define _port_for around profile; why: its direct callers call _port_for for port for and rely on this exact input and result contract.
    def _port_for(self, profile: ModelProfile) -> int:
        """Resolve a profile's proxy/readiness target under router ownership."""
        # What: document resolve a profile s proxy readiness in the _port_for docstring; why: introspection and maintainers read this exact docstring fragment to understand port for behavior without executing it.
        # What: gate on port and profile before default port; why: _port_for admits default port only for this predicate and excludes the opposite state.
        if profile.port is None:
            # What: return default port from _port_for; why: _port_for exposes default port so its caller can continue with the function\'s computed outcome.
            return self._default_port
        # What: gate on port and profile before port and profile; why: _port_for admits port and profile only for this predicate and excludes the opposite state.
        if profile.port != 0:
            # What: return port and profile from _port_for; why: _port_for exposes port and profile so its caller can continue with the function\'s computed outcome.
            return profile.port
        # What: compute state from status and manager; why: if self active name profile name and state get running later reads state, so _port_for must retain the computed value under that name.
        state = self._manager.status()
        # A dynamic profile retains its concrete port for its whole residency;
        # a fresh activation gets a new kernel-selected one.
        # What: gate on active name and name and get and isinstance and int before state; why: _port_for admits state only for this predicate and excludes the opposite state.
        if (self._active_name == profile.name and state.get("running")
                # What: call isinstance with get and state and port and int; why: _port_for invokes isinstance while performing return state port; the call advances that operation through its result or side effect.
                and isinstance(state.get("port"), int) and state["port"] > 0):
            # What: return state and port from _port_for; why: _port_for exposes state and port so its caller can continue with the function\'s computed outcome.
            return state["port"]
        # What: return port allocator from _port_for; why: _port_for exposes port allocator so its caller can continue with the function\'s computed outcome.
        return self._port_allocator()

    # What: define _activate around profile and port; why: its direct callers call _activate for activate and rely on this exact input and result contract.
    def _activate(self, profile: ModelProfile, port: int) -> int | None:
        # What: compute state from status and manager; why: state get running later reads state, so _activate must retain the computed value under that name.
        state = self._manager.status()
        # What: compute exact from get and model and port and state; why: if exact later reads exact, so _activate must retain the computed value under that name.
        exact = (
            # What: call state.get with running; why: _activate invokes state.get while performing and state get model profile model; the call advances that operation through its result or side effect.
            state.get("running")
            # What: call state.get with model; why: _activate invokes state.get while performing and state get port port; the call advances that operation through its result or side effect.
            and state.get("model") == profile.model
            # What: call state.get with port; why: _activate invokes state.get while performing and self manager serve args list profile args; the call advances that operation through its result or side effect.
            and state.get("port") == port
            # What: call self._manager.serve_args with the declared inputs; why: _activate consumes the self._manager.serve_args return value while evaluating and self._manager.serve_args() == list(profile.args).
            and self._manager.serve_args() == list(profile.args)
        # What: complete the exact expression with exact state get running and state get model equals profile model and; why: RoutingCoordinator._activate groups the supplied clauses as one exact expression before its value is consumed.
        )
        # What: compute ticket from the named fixture input; why: result ticket self manager switch for readiness later reads ticket, so _activate must retain the computed value under that name.
        ticket = None
        # What: gate on exact before result and get and state; why: _activate admits result and get and state only for this predicate and excludes the opposite state.
        if exact:
            # What: map the pid field as get and state and pid; why: RoutingCoordinator._activate carries pid through result into result ticket self manager switch for readiness.
            result = {"pid": state.get("pid"), "idempotent": True}
        # What: gate on get and state before cond and activations; why: _activate admits cond and activations only for this predicate and excludes the opposite state.
        elif state.get("running"):
            # What: enter the cond managed context before self activations; why: _activate releases this resource or lock after self activations on both success and failure paths.
            with self._cond:
                # What: compute activations from 1; why: self activations later reads activations, so _activate must retain the computed value under that name.
                self._activations += 1
            # What: compute result and ticket from switch for readiness and model and port and manager; why: result self manager start profile model port list profile args later reads result and ticket, so _activate must retain the computed value under that name.
            result, ticket = self._manager.switch_for_readiness(
                # What: call list with args and profile; why: _activate consumes the list return value while evaluating profile.model, port, list(profile.args).
                profile.model, port, list(profile.args)
            # What: complete the self._manager.switch_for_readiness call with model and port and list; why: RoutingCoordinator._activate groups the supplied clauses as one self._manager.switch_for_readiness call before its value is consumed.
            )
        # What: select the remaining branch that performs with self cond; why: _activate covers the state excluded by the preceding predicate without conflating the two outcomes.
        else:
            # What: enter the cond managed context before self activations; why: _activate releases this resource or lock after self activations on both success and failure paths.
            with self._cond:
                # What: compute activations from 1; why: the enclosing return or state update later reads activations, so _activate must retain the computed value under that name.
                self._activations += 1
            # What: compute result from start and model and port and manager; why: pid result get pid later reads result, so _activate must retain the computed value under that name.
            result = self._manager.start(profile.model, port, list(profile.args))
        # What: compute readiness args from port and ready timeout s and get and profile; why: readiness args path profile check endpoint later reads readiness args, so _activate must retain the computed value under that name.
        readiness_args = {
            # What: map the pid field as get and result and pid; why: RoutingCoordinator._activate carries pid through readiness args into readiness args path profile check endpoint.
            "pid": result.get("pid"),
            # What: map the port field as port; why: RoutingCoordinator._activate carries port through readiness args into readiness args path profile check endpoint.
            "port": port,
            # What: map the timeout s field as ready timeout s and profile; why: RoutingCoordinator._activate carries timeout s through readiness args into readiness args path profile check endpoint.
            "timeout_s": profile.ready_timeout_s,
        # What: complete the readiness_args mapping with pid and port and timeout s; why: RoutingCoordinator._activate groups the supplied clauses as one readiness_args mapping before its value is consumed.
        }
        # What: gate on check endpoint and default check endpoint and profile before check endpoint and readiness args and profile; why: _activate admits check endpoint and readiness args and profile only for this predicate and excludes the opposite state.
        if profile.check_endpoint != DEFAULT_CHECK_ENDPOINT:
            # What: compute readiness args entry from check endpoint and profile; why: readiness self ready fn self manager self probe readiness args later reads readiness args entry, so _activate must retain the computed value under that name.
            readiness_args["path"] = profile.check_endpoint
        # What: compute readiness from ready fn and manager and probe and readiness args; why: if readiness get ready later reads readiness, so _activate must retain the computed value under that name.
        readiness = self._ready_fn(self._manager, self._probe, **readiness_args)
        # What: gate on get and readiness before get and result; why: _activate admits get and result only for this predicate and excludes the opposite state.
        if readiness.get("ready"):
            # What: return get and result and pid from _activate; why: _activate exposes get and result and pid so its caller can continue with the function\'s computed outcome.
            return result.get("pid")
        # What: compute recovery from the named fixture input; why: recovery self manager recover switch ticket later reads recovery, so _activate must retain the computed value under that name.
        recovery = None
        # What: gate on ticket before recovery and recover switch and ticket and manager; why: _activate admits recovery and recover switch and ticket and manager only for this predicate and excludes the opposite state.
        if ticket is not None:
            # What: compute recovery from recover switch and ticket and manager; why: recovery recovery later reads recovery, so _activate must retain the computed value under that name.
            recovery = self._manager.recover_switch(ticket)
        # What: compute reason from get and readiness and reason and not ready; why: f profile profile name r is not later reads reason, so _activate must retain the computed value under that name.
        reason = readiness.get("reason", "not-ready")
        # What: raise RoutingError for the caller; why: RoutingCoordinator._activate stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RoutingError(
            # What: apply the engine not ready portion of the enclosing predicate; why: this clause remains in _activate\'s enclosing expression so its grouping and evaluation order stay intact.
            "engine_not_ready",
            # What: apply the f profile profile name r is not portion of the enclosing predicate; why: this clause remains in _activate\'s enclosing expression so its grouping and evaluation order stay intact.
            f"profile {profile.name!r} is not ready: {reason}",
            # What: supply recovery to RoutingError; why: _activate binds this recovery value to RoutingError's recovery input.
            recovery=recovery,
        # What: complete the RoutingError call with recovery; why: RoutingCoordinator._activate groups the supplied clauses as one RoutingError call before its value is consumed.
        )
