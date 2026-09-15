"""Wait for a newly launched FreeToken serve to report its own readiness.

The daemon never treats a listening socket as ready.  ``/health`` is the
engine's lifecycle authority and reports ``loading``, ``ok``, or ``error``.
This helper intentionally does not kill an engine on timeout: model loads can
be slow, and the existing manager must keep the still-visible process available
for logs, diagnosis, or an explicit operator stop.
"""
# What: document wait for a newly launched free token in the readiness docstring; why: introspection and maintainers read this exact docstring fragment to understand readiness behavior without executing it.
# What: document the daemon never treats a listening in the readiness docstring; why: introspection and maintainers read this exact docstring fragment to understand readiness behavior without executing it.
# What: document engine s lifecycle authority and reports in the readiness docstring; why: introspection and maintainers read this exact docstring fragment to understand readiness behavior without executing it.
# What: document this helper intentionally does not kill in the readiness docstring; why: introspection and maintainers read this exact docstring fragment to understand readiness behavior without executing it.
# What: document be slow and the existing manager in the readiness docstring; why: introspection and maintainers read this exact docstring fragment to understand readiness behavior without executing it.
# What: document for logs diagnosis or an explicit in the readiness docstring; why: introspection and maintainers read this exact docstring fragment to understand readiness behavior without executing it.
# What: preserve the paragraph boundary in the the readiness docstring; why: introspection and maintainers read this paragraph break to understand readiness behavior without executing it.

# What: enable postponed evaluation of annotations; why: type hints in readiness can reference runtime types without eager imports or forward-reference failures.
from __future__ import annotations

# What: import time for wait for ready using time; why: wait_for_ready uses time monotonic, making that imported dependency available to its named operation.
import time
# What: import any and callable for wait for ready using typing and any and callable; why: wait_for_ready uses the any annotation in wait for ready and the callable annotation in wait for ready, making that imported dependency available to its named operation.
from typing import Any, Callable


# What: define wait_for_ready around manager and probe and pid and port and timeout s and path and now and sleep; why: its direct callers call wait_for_ready for wait for ready and rely on this exact input and result contract.
def wait_for_ready(
    # What: declare the manager input for wait_for_ready; why: wait_for_ready consumes manager during state manager status, so callers must bind it with the other signature inputs.
    manager,
    # What: declare the probe input for wait_for_ready; why: wait_for_ready consumes probe during probe fresh health port, so callers must bind it with the other signature inputs.
    probe,
    # What: mark the remaining parameters as keyword-only; why: wait_for_ready prevents callers from confusing adjacent lifecycle and timing arguments.
    *,
    # What: declare the pid input for wait_for_ready; why: wait_for_ready consumes pid during if not state get running or pid, so callers must bind it with the other signature inputs.
    pid: int | None,
    # What: declare the port input for wait_for_ready; why: wait_for_ready consumes port during probe fresh health port, so callers must bind it with the other signature inputs.
    port: int,
    # What: declare the timeout s input for wait_for_ready; why: wait_for_ready consumes timeout s during deadline now timeout s, so callers must bind it with the other signature inputs.
    timeout_s: float,
    # What: declare the path input for wait_for_ready; why: wait_for_ready consumes path during if path health, so callers must bind it with the other signature inputs.
    path: str = "/health",
    # What: declare the now input for wait_for_ready; why: wait_for_ready consumes now during deadline now timeout s, so callers must bind it with the other signature inputs.
    now: Callable[[], float] = time.monotonic,
    # What: declare the sleep input for wait_for_ready; why: wait_for_ready consumes sleep during sleep min remaining, so callers must bind it with the other signature inputs.
    sleep: Callable[[float], None] = time.sleep,
# What: declare a heterogeneous readiness-result mapping; why: callers receive ready, reason, and health fields whose values include booleans, strings, and nested health data.
) -> dict[str, Any]:
    # What: compute deadline from timeout s and now; why: remaining deadline now later reads deadline, so wait_for_ready must retain the computed value under that name.
    deadline = now() + timeout_s
    # What: map the reachable field as false; why: wait_for_ready carries reachable through last into return ready false reason superseded health last.
    last: dict[str, Any] = {"reachable": False, "status": "unreachable"}
    # What: poll readiness until an explicit terminal condition returns; why: supersession, ready, engine-error, and timeout returns bound this loop despite its unconditional header.
    while True:
        # What: compute state from status and manager; why: if not state get running or pid later reads state, so wait_for_ready must retain the computed value under that name.
        state = manager.status()
        # What: gate on get and pid and state before last; why: wait_for_ready admits last only for this predicate and excludes the opposite state.
        if not state.get("running") or (pid is not None and state.get("pid") != pid):
            # What: map the ready field as false; why: wait_for_ready carries ready into return {"ready": False, "reason": "superseded", "health": last}.
            return {"ready": False, "reason": "superseded", "health": last}
        # What: compute last from path and fresh health and port and fresh readiness; why: return ready reason superseded health last later reads last, so wait_for_ready must retain the computed value under that name.
        last = (
            # What: call probe.fresh_health with port; why: wait_for_ready invokes probe.fresh_health while performing if path health; the call advances that operation through its result or side effect.
            probe.fresh_health(port)
            # What: apply the if path health portion of last; why: wait_for_ready uses this clause to evaluate last as one grouped value.
            if path == "/health"
            # What: call probe.fresh_readiness with port and path; why: wait_for_ready consumes the probe.fresh_readiness return value while evaluating else probe.fresh_readiness(port, path).
            else probe.fresh_readiness(port, path)
        # What: complete the last expression with last probe fresh health port if path equals health else probe fresh readiness; why: wait_for_ready groups the supplied clauses as one last expression before its value is consumed.
        )
        # Replacement or exit can happen while the HTTP request is in flight.
        # What: compute state from status and manager; why: if not state get running or pid later reads state, so wait_for_ready must retain the computed value under that name.
        state = manager.status()
        # What: gate on get and pid and state before last; why: wait_for_ready admits last only for this predicate and excludes the opposite state.
        if not state.get("running") or (pid is not None and state.get("pid") != pid):
            # What: map the ready field as false; why: wait_for_ready carries ready into return {"ready": False, "reason": "superseded", "health": last}.
            return {"ready": False, "reason": "superseded", "health": last}
        # What: gate on get and last and path before last; why: wait_for_ready admits last only for this predicate and excludes the opposite state.
        if last.get("reachable") and (
            # What: apply the path health portion of the enclosing predicate; why: this clause remains in wait_for_ready\'s enclosing expression so its grouping and evaluation order stay intact.
            path != "/health"
            # What: apply the or portion of the enclosing predicate; why: this clause remains in wait_for_ready\'s enclosing expression so its grouping and evaluation order stay intact.
            or (
                # What: call last.get with status; why: wait_for_ready invokes last.get while performing and last get maintenance serving serving; the call advances that operation through its result or side effect.
                last.get("status") == "ok"
                # What: call last.get with maintenance and serving; why: wait_for_ready consumes the last.get return value while evaluating and last.get("maintenance", "serving") == "serving".
                and last.get("maintenance", "serving") == "serving"
            # What: complete the enclosing predicate with path differs from health or last get status equals ok; why: wait_for_ready groups the supplied clauses as one enclosing predicate expression before its value is consumed.
            )
        # What: complete the enclosing predicate with last get reachable and path differs from health or last get; why: wait_for_ready groups the supplied clauses as one enclosing predicate expression before its value is consumed.
        ):
            # What: map the ready field as true; why: wait_for_ready carries ready into return {"ready": True, "health": last}.
            return {"ready": True, "health": last}
        # What: gate on get and last before last; why: wait_for_ready admits last only for this predicate and excludes the opposite state.
        if last.get("status") == "error":
            # What: map the ready field as false; why: wait_for_ready carries ready into return {"ready": False, "reason": "engine-error", "health": last}.
            return {"ready": False, "reason": "engine-error", "health": last}
        # What: compute remaining from deadline and now; why: if remaining later reads remaining, so wait_for_ready must retain the computed value under that name.
        remaining = deadline - now()
        # What: gate on remaining before last; why: wait_for_ready admits last only for this predicate and excludes the opposite state.
        if remaining <= 0:
            # What: map the ready field as false; why: wait_for_ready carries ready into return {"ready": False, "reason": "timeout", "health": last}.
            return {"ready": False, "reason": "timeout", "health": last}
        # What: pace the next readiness poll with the injected sleep callback; why: the quarter-second cap avoids busy-waiting while the remaining deadline prevents oversleeping the timeout.
        sleep(min(0.25, remaining))
