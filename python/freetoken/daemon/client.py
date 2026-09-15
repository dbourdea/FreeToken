"""``ft daemon <verb>`` — the client half of the daemon's own control entry point.

Kept separate from ``ft ctl`` (which targets a running *serve*): the daemon has its own dedicated
CLI. Bare ``ft daemon`` (or ``ft daemon --host/--port …``) runs the server; ``ft daemon <verb>``
below controls a running daemon over HTTP. Torch-free — stdlib ``urllib`` only."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from typing import Any

DEFAULT_URL = "http://127.0.0.1:1900"
DEFAULT_TIMEOUT = 10.0
# prepare-stop (15s transport budget) + default SIGTERM grace (10s) + reap wait (10s),
# with enough HTTP scheduling slack that a valid lifecycle transaction does not look failed.
DEFAULT_LIFECYCLE_TIMEOUT = 40.0
# What: compute default profile timeout from 1920 0; why: return default profile timeout later reads default profile timeout, so client must retain the computed value under that name.
DEFAULT_PROFILE_TIMEOUT = 1920.0  # replacement + recovery readiness (2 * 900s), lifecycle margin

# Positional verbs that mean "act as a client"; anything else (bare, or a flag like --host) runs
# the server. Kept in one place so the server dispatcher and this parser agree.
# What: compute client verbs from self and status and health and metrics and stats; why: the enclosing return or state update later reads client verbs, so client must retain the computed value under that name.
CLIENT_VERBS = (
    # What: apply the status health metrics stats models routing profiles portion of client verbs; why: client uses this clause to evaluate client verbs as one grouped value.
    "self", "status", "health", "metrics", "stats", "models", "routing-profiles",
    # What: apply the activate routing profile clear routing profile start stop shutdown portion of client verbs; why: client uses this clause to evaluate client verbs as one grouped value.
    "activate-routing-profile", "clear-routing-profile", "start", "stop", "shutdown",
    # What: apply the switch start profile switch profile logs portion of client verbs; why: client uses this clause to evaluate client verbs as one grouped value.
    "switch", "start-profile", "switch-profile", "logs",
# What: complete the CLIENT_VERBS collection with self and status and health and metrics; why: client groups the supplied clauses as one CLIENT_VERBS collection before its value is consumed.
)


class ClientError(Exception):
    def __init__(self, message: str, *, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _effective_timeout(verb: str, configured: float | None) -> float:
    if configured is not None:
        return configured
    # What: gate on verb before default profile timeout; why: _effective_timeout admits default profile timeout only for this predicate and excludes the opposite state.
    if verb in {"start-profile", "switch-profile"}:
        # What: return default profile timeout from _effective_timeout; why: _effective_timeout exposes default profile timeout so its caller can continue with the function\'s computed outcome.
        return DEFAULT_PROFILE_TIMEOUT
    return (
        DEFAULT_LIFECYCLE_TIMEOUT
        # What: apply the if verb in stop shutdown switch portion of the enclosing predicate; why: this clause remains in _effective_timeout\'s enclosing expression so its grouping and evaluation order stay intact.
        if verb in {"stop", "shutdown", "switch", "start-profile", "switch-profile"}
        else DEFAULT_TIMEOUT
    )


def _request(method: str, url: str, path: str, *, body=None, query=None, token=None, timeout=10.0, accept="application/json"):
    full = f"{url.rstrip('/')}{path}"
    if query:
        full = f"{full}?{urllib.parse.urlencode(query)}"
    headers = {"Accept": accept}
    if token:
        headers["X-FT-Token"] = token
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(full, data=data, headers=headers, method=method)
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        raise ClientError(f"HTTP {exc.code}: {_err_body(exc.read()) or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise ClientError(f"failed to reach {url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ClientError(f"timed out connecting to {url}") from exc


def _err_body(raw: bytes) -> str:
    if not raw:
        return ""
    text = raw.decode("utf-8", "replace")
    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(doc, dict):
        for key in ("error", "detail", "message"):
            if doc.get(key):
                return str(doc[key])
    return text


def _request_json(method, url, path, *, body=None, query=None, token=None, timeout=10.0) -> dict:
    with _request(method, url, path, body=body, query=query, token=token, timeout=timeout) as resp:
        raw = resp.read()
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ClientError("daemon returned invalid JSON") from exc


def _stream_logs(url, since, token, timeout) -> None:
    # The stream is endless; print each line until interrupted. A long read timeout survives idle
    # heartbeats without hanging forever on a dead socket.
    with _request("GET", url, "/engine/logs", query={"since": since}, token=token,
                  timeout=max(timeout, 3600.0), accept="text/event-stream") as resp:
        try:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                try:
                    rec = json.loads(line[len("data:"):].strip())
                except json.JSONDecodeError:
                    continue
                if rec.get("kind") == "gap":
                    print(f"... [{rec.get('dropped')} log lines dropped]")
                else:
                    print(rec.get("text", ""))
        except KeyboardInterrupt:
            pass


def _build_parser(prog: str) -> argparse.ArgumentParser:
    # The package dispatcher routes to the client only when a verb is argv[0], so --url/--token/
    # --timeout live on each verb (`ft daemon status --url X`), not before it.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--url", default=os.environ.get("FREETOKEN_DAEMON_URL", DEFAULT_URL),
                        help=f"daemon URL (default {DEFAULT_URL})")
    common.add_argument("--token", default=os.environ.get("FREETOKEN_DAEMON_TOKEN"), help="X-FT-Token shared secret")
    common.add_argument(
        "--timeout",
        type=float,
        default=None,
        # What: preserve the exact help http timeout default s stop literal fragment; why: _build_parser passes this fragment verbatim through help="HTTP timeout (default 10s; stop/switch 40s; profiles 960s)", because changing it would alter a protocol payload, serialized fixture, or public message.
        help="HTTP timeout (default 10s; stop/switch 40s; profiles 960s)",
    )

    p = argparse.ArgumentParser(prog=prog, description="Control a running ft daemon")
    sub = p.add_subparsers(dest="verb", required=True)
    sub.add_parser("self", parents=[common], help="Daemon self-health (GET /health)")
    sub.add_parser("status", parents=[common], help="Engine status (GET /engine/status)")
    sub.add_parser("health", parents=[common], help="Proxied serve health (GET /engine/health)")
    sub.add_parser("metrics", parents=[common], help="Engine footprint (GET /engine/metrics)")
    sub.add_parser("stats", parents=[common], help="Proxied serve stats (GET /engine/stats)")
    # What: call sub.add_parser with models; why: _build_parser invokes sub.add_parser while performing models parents common; the call advances that operation through its result or side effect.
    sub.add_parser(
        # What: preserve the exact models parents common literal fragment; why: _build_parser passes this fragment verbatim through "models", parents=[common], because changing it would alter a protocol payload, serialized fixture, or public message.
        "models", parents=[common],
        # What: preserve the exact help list named freetoken swap model profiles literal fragment; why: _build_parser passes this fragment verbatim through help="List named freetoken-swap model profiles (GET /router/profiles)", because changing it would alter a protocol payload, serialized fixture, or public message.
        help="List named freetoken-swap model profiles (GET /router/profiles)",
    # What: complete the sub.add_parser call with parents and help; why: _build_parser groups the supplied clauses as one sub.add_parser call before its value is consumed.
    )
    # What: call sub.add_parser with routing profiles; why: _build_parser invokes sub.add_parser while performing routing profiles parents common; the call advances that operation through its result or side effect.
    sub.add_parser(
        # What: preserve the exact routing profiles parents common literal fragment; why: _build_parser passes this fragment verbatim through "routing-profiles", parents=[common], because changing it would alter a protocol payload, serialized fixture, or public message.
        "routing-profiles", parents=[common],
        # What: preserve the exact help list runtime model id pin profiles literal fragment; why: _build_parser passes this fragment verbatim through help="List runtime model-ID pin profiles (GET /router/profiles)", because changing it would alter a protocol payload, serialized fixture, or public message.
        help="List runtime model-ID pin profiles (GET /router/profiles)",
    # What: complete the sub.add_parser call with parents and help; why: _build_parser groups the supplied clauses as one sub.add_parser call before its value is consumed.
    )
    # What: compute activate routing from add parser and sub and common and activate routing profile and activate; why: activate routing add argument name help routing profile name later reads activate routing, so _build_parser must retain the computed value under that name.
    activate_routing = sub.add_parser(
        # What: supply parents to sub.add_parser; why: _build_parser binds this common value to sub.add_parser's parents input.
        "activate-routing-profile", parents=[common],
        # What: supply help to sub.add_parser; why: _build_parser binds this activate and a and runtime and model id value to sub.add_parser's help input.
        help="Activate a runtime model-ID pin profile",
    # What: complete the sub.add_parser call with parents and help; why: _build_parser groups the supplied clauses as one sub.add_parser call before its value is consumed.
    )
    # What: preserve the exact activate routing add argument name help routing profile name literal fragment; why: _build_parser passes this fragment verbatim through activate_routing.add_argument("name", help="Routing profile name"), because changing it would alter a protocol payload, serialized fixture, or public me.
    activate_routing.add_argument("name", help="Routing profile name")
    # What: call sub.add_parser with clear routing profile; why: _build_parser invokes sub.add_parser while performing clear routing profile parents common; the call advances that operation through its result or side effect.
    sub.add_parser(
        # What: preserve the exact clear routing profile parents common literal fragment; why: _build_parser passes this fragment verbatim through "clear-routing-profile", parents=[common], because changing it would alter a protocol payload, serialized fixture, or public message.
        "clear-routing-profile", parents=[common],
        # What: preserve the exact help clear the active runtime model id literal fragment; why: _build_parser passes this fragment verbatim through help="Clear the active runtime model-ID pin profile", because changing it would alter a protocol payload, serialized fixture, or public message.
        help="Clear the active runtime model-ID pin profile",
    # What: complete the sub.add_parser call with parents and help; why: _build_parser groups the supplied clauses as one sub.add_parser call before its value is consumed.
    )
    stop = sub.add_parser("stop", parents=[common], help="Stop the serve (POST /engine/stop)")
    stop.add_argument(
        "--force",
        action="store_true",
        help="stop even if final accounting cannot be sealed (may lose the unobserved token tail)",
    )
    # What: compute shutdown from add parser and sub and common and shutdown and stop; why: shutdown add argument later reads shutdown, so _build_parser must retain the computed value under that name.
    shutdown = sub.add_parser("shutdown", parents=[common], help="Stop the serve and daemon (POST /shutdown)")
    # What: call shutdown.add_argument with force; why: _build_parser invokes shutdown.add_argument while performing force; the call advances that operation through its result or side effect.
    shutdown.add_argument(
        # What: preserve the exact force literal fragment; why: _build_parser passes this fragment verbatim through "--force", because changing it would alter a protocol payload, serialized fixture, or public message.
        "--force",
        # What: preserve the exact action store true literal fragment; why: _build_parser passes this fragment verbatim through action="store_true", because changing it would alter a protocol payload, serialized fixture, or public message.
        action="store_true",
        # What: preserve the exact help stop even if final accounting literal fragment; why: _build_parser passes this fragment verbatim through help="stop even if final accounting cannot be sealed (may lose the unobs, because changing it would alter a protocol payload, serialized fixture, or public message.
        help="stop even if final accounting cannot be sealed (may lose the unobserved token tail)",
    # What: complete the shutdown.add_argument call with action and help; why: _build_parser groups the supplied clauses as one shutdown.add_argument call before its value is consumed.
    )
    for name in ("start", "switch"):
        sp = sub.add_parser(name, parents=[common], help=f"POST /engine/{name}")
        sp.add_argument("model", help="Model path/id")
        sp.add_argument("--port", type=int, default=None, help="Serve port")
        if name == "switch":
            sp.add_argument(
                "--force",
                action="store_true",
                help="replace even if final accounting cannot be sealed (may lose the unobserved token tail)",
            )
        # Everything after `--` is forwarded verbatim to ft serve (opaque passthrough):
        #   ft daemon start MODEL --port 1919 -- --moe-cache-auto --graph 256
        sp.add_argument("serve_args", nargs="*", default=[], help="Extra ft serve args (after --)")
    # What: iterate across the computed value to perform sp and add parser and name and sub and common; why: _build_parser repeats the body only while or for the loop header admits an iteration.
    for name in ("start-profile", "switch-profile"):
        # What: compute sp from add parser and name and sub and common and post; why: sp add argument name help named model profile later reads sp, so _build_parser must retain the computed value under that name.
        sp = sub.add_parser(name, parents=[common], help=f"POST /engine/{name}")
        # What: preserve the exact sp add argument name help named model profile literal fragment; why: _build_parser passes this fragment verbatim through sp.add_argument("name", help="Named model profile from the daemon catalo, because changing it would alter a protocol payload, serialized fixture, or public message.
        sp.add_argument("name", help="Named model profile from the daemon catalog")
        # What: gate on name before add argument and sp; why: _build_parser admits add argument and sp only for this predicate and excludes the opposite state.
        if name == "switch-profile":
            # What: preserve the exact sp add argument force action store true help replace literal fragment; why: _build_parser passes this fragment verbatim through sp.add_argument("--force", action="store_true", help="replace even if fi, because changing it would alter a protocol payload, serialized fixture, or pub.
            sp.add_argument("--force", action="store_true", help="replace even if final accounting cannot be sealed")
    lg = sub.add_parser("logs", parents=[common], help="Stream engine logs (SSE, GET /engine/logs)")
    lg.add_argument("--since", type=int, default=0, help="Replay from this seq cursor")
    return p


def main(argv: Sequence[str] | None = None, *, prog: str = "ft daemon") -> int:
    args = _build_parser(prog).parse_args(list(argv) if argv is not None else None)
    timeout = _effective_timeout(args.verb, args.timeout)
    try:
        if args.verb == "logs":
            _stream_logs(args.url, args.since, args.token, timeout)
            return 0
        table = {
            "self": ("GET", "/health", None),
            "status": ("GET", "/engine/status", None),
            "health": ("GET", "/engine/health", None),
            "metrics": ("GET", "/engine/metrics", None),
            "stats": ("GET", "/engine/stats", None),
            # What: map the models field as get and router and profiles; why: main carries models through table into method path body table args verb.
            "models": ("GET", "/router/profiles", None),
            # What: map the routing profiles field as get and router and profiles; why: main carries routing profiles through table into method path body table args verb.
            "routing-profiles": ("GET", "/router/profiles", None),
            "stop": (
                "POST",
                "/engine/stop",
                {"force": True} if getattr(args, "force", False) else {},
            ),
            # What: map the shutdown field as getattr and args and post and shutdown and force; why: main carries shutdown through table into method path body table args verb.
            "shutdown": (
                # What: apply the post portion of table; why: main uses this clause to evaluate table as one grouped value.
                "POST",
                # What: apply the shutdown portion of table; why: main uses this clause to evaluate table as one grouped value.
                "/shutdown",
                # What: map the force field as true; why: main carries force through table into method path body table args verb.
                {"force": True} if getattr(args, "force", False) else {},
            # What: complete the table collection with post and shutdown and getattr and args and force and false and force; why: main groups the supplied clauses as one table collection before its value is consumed.
            ),
        }
        # What: gate on verb and args before method and path and body and name and args; why: main admits method and path and body and name and args only for this predicate and excludes the opposite state.
        if args.verb == "activate-routing-profile":
            # What: map the name field as name and args; why: main carries name through method and path and body into method path body put router profiles active.
            method, path, body = "PUT", "/router/profiles/active", {"name": args.name}
        # What: gate on verb and args before method and path and body; why: main admits method and path and body only for this predicate and excludes the opposite state.
        elif args.verb == "clear-routing-profile":
            # What: map the name field as the fixture input; why: main carries name through method and path and body into method path post f engine args verb.
            method, path, body = "PUT", "/router/profiles/active", {"name": None}
        # What: gate on verb and args before body and dict and model and str and any; why: main admits body and dict and model and str and any only for this predicate and excludes the opposite state.
        elif args.verb in ("start", "switch"):
            body: dict[str, Any] = {"model": args.model, "args": list(args.serve_args)}
            if args.port is not None:
                body["port"] = args.port
            if args.verb == "switch" and args.force:
                body["force"] = True
            method, path = "POST", f"/engine/{args.verb}"
        # What: gate on verb and args before body and name and args; why: main admits body and name and args only for this predicate and excludes the opposite state.
        elif args.verb in ("start-profile", "switch-profile"):
            # What: map the name field as name and args; why: main carries name through body into body force true.
            body = {"name": args.name}
            # What: gate on force and verb and args before body; why: main admits body only for this predicate and excludes the opposite state.
            if args.verb == "switch-profile" and args.force:
                # What: compute body entry from true; why: method path body table args verb later reads body entry, so main must retain the computed value under that name.
                body["force"] = True
            # What: compute method and path from verb and args and post and engine; why: method path body table args verb later reads method and path, so main must retain the computed value under that name.
            method, path = "POST", f"/engine/{args.verb}"
        else:
            method, path, body = table[args.verb]
        doc = _request_json(method, args.url, path, body=body, token=args.token, timeout=timeout)
        print(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True))
        # What: gate on verb and args and get and doc before the computed value; why: main admits the computed value only for this predicate and excludes the opposite state.
        if args.verb in {"start-profile", "switch-profile"} and not doc.get("readiness", {}).get("ready"):
            # What: return 1 from main; why: main exposes 1 so its caller can continue with the function\'s computed outcome.
            return 1
        return 0
    except ClientError as exc:
        print(str(exc), file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
