"""Bounded inference activity and opt-in redacted request/response captures."""
# What: document bounded inference activity and opt in redacted in the activity docstring; why: introspection and maintainers read this exact docstring fragment to understand activity behavior without executing it.

# What: enable postponed evaluation of annotations; why: type hints in activity can reference runtime types without eager imports or forward-reference failures.
from __future__ import annotations

# What: import base64 for record using base64; why: record uses base64 b64encode, making that imported dependency available to its named operation.
import base64
# What: import ordered dict and deque for init using collections and ordered dict and deque; why: __init__ uses ordered dict and deque, making that imported dependency available to its named operation.
from collections import OrderedDict, deque
# What: import dataclass for module initialization using dataclasses and dataclass; why: module initialization uses dataclass, making that imported dependency available to its named operation.
from dataclasses import dataclass
# What: import hashlib for record using hashlib; why: record uses hashlib sha256, making that imported dependency available to its named operation.
import hashlib
# What: import json for load using json; why: _load uses json jsondecode error, making that imported dependency available to its named operation.
import json
# What: import math for from public using math; why: from_public uses math isfinite, making that imported dependency available to its named operation.
import math
# What: import os for compact locked using os; why: _compact_locked uses os replace, making that imported dependency available to its named operation.
import os
# What: import threading for init using threading; why: __init__ uses threading lock, making that imported dependency available to its named operation.
import threading
# What: import time for record using time; why: record uses time time, making that imported dependency available to its named operation.
import time
# What: import mapping for headers using typing and mapping; why: _headers uses the mapping annotation in headers, making that imported dependency available to its named operation.
from typing import Mapping


# What: compute sensitive headers from authorization and proxy authorization and cookie and set cookie and x api key; why: normalized in sensitive headers later reads sensitive headers, so activity must retain the computed value under that name.
_SENSITIVE_HEADERS = {
    # What: apply the authorization proxy authorization cookie set cookie x api key x ft token portion of sensitive headers; why: activity uses this clause to evaluate sensitive headers as one grouped value.
    "authorization", "proxy-authorization", "cookie", "set-cookie", "x-api-key", "x-ft-token",
# What: complete the _SENSITIVE_HEADERS collection with authorization and proxy authorization and cookie and set cookie; why: activity groups the supplied clauses as one _SENSITIVE_HEADERS collection before its value is consumed.
}
# What: compute max persisted row chars from 8192; why: while line source readline max persisted row chars later reads max persisted row chars, so activity must retain the computed value under that name.
_MAX_PERSISTED_ROW_CHARS = 8192


# What: define _sensitive_header around name; why: its direct callers call _sensitive_header for sensitive header and rely on this exact input and result contract.
def _sensitive_header(name: str) -> bool:
    # What: compute normalized from replace and lower and name and value and value; why: parts normalized split later reads normalized, so _sensitive_header must retain the computed value under that name.
    normalized = name.lower().replace("_", "-")
    # What: compute parts from split and normalized and value; why: or token in parts later reads parts, so _sensitive_header must retain the computed value under that name.
    parts = normalized.split("-")
    # What: return normalized and sensitive headers and parts and token and secret from _sensitive_header; why: _sensitive_header exposes normalized and sensitive headers and parts and token and secret so its caller can continue with the function\'s computed outcome.
    return (
        # What: apply the normalized in sensitive headers portion of the enclosing predicate; why: this clause remains in _sensitive_header\'s enclosing expression so its grouping and evaluation order stay intact.
        normalized in _SENSITIVE_HEADERS
        # What: apply the or token in parts portion of the enclosing predicate; why: this clause remains in _sensitive_header\'s enclosing expression so its grouping and evaluation order stay intact.
        or "token" in parts
        # What: apply the or secret in parts portion of the enclosing predicate; why: this clause remains in _sensitive_header\'s enclosing expression so its grouping and evaluation order stay intact.
        or "secret" in parts
        # What: apply the or api in parts and key portion of the enclosing predicate; why: this clause remains in _sensitive_header\'s enclosing expression so its grouping and evaluation order stay intact.
        or ("api" in parts and "key" in parts)
    # What: complete the _sensitive_header signature with name; why: _sensitive_header groups the supplied clauses as one _sensitive_header signature before its value is consumed.
    )


# What: define _headers around values; why: its direct callers call _headers for headers and rely on this exact input and result contract.
def _headers(values: Mapping[str, str]) -> dict[str, str]:
    # What: initialize result as an empty runtime accumulator; why: _headers appends or maps entries into it during result key redacted if sensitive header key else before consuming the aggregate.
    result: dict[str, str] = {}
    # What: iterate across list and items and values to perform result and key and sensitive header and str and value; why: _headers repeats the body only while or for the loop header admits an iteration.
    for key, value in list(values.items())[:64]:
        # What: compute result entry from sensitive header and key and str and value and redacted; why: return result later reads result entry, so _headers must retain the computed value under that name.
        result[key] = "[REDACTED]" if _sensitive_header(key) else str(value)[:1024]
    # What: return result from _headers; why: _headers exposes result so its caller can continue with the function\'s computed outcome.
    return result


# What: generate dataclass initialization and value semantics for ActivityRecord; why: ActivityRecord acts as a typed state record with consistent construction, comparison, and representation.
@dataclass(frozen=True)
# What: define ActivityRecord as the owner of public and from_public; why: daemon callers use this class boundary so those methods share one activity record state invariant.
class ActivityRecord:
    # What: compute id from the named fixture input; why: id self id later reads id, so activity must retain the computed value under that name.
    id: int
    # What: compute timestamp from the named fixture input; why: timestamp self timestamp later reads timestamp, so activity must retain the computed value under that name.
    timestamp: float
    # What: compute model from the named fixture input; why: model self model later reads model, so activity must retain the computed value under that name.
    model: str
    # What: compute route from the named fixture input; why: route self route later reads route, so activity must retain the computed value under that name.
    route: str
    # What: compute method from the named fixture input; why: method self method later reads method, so activity must retain the computed value under that name.
    method: str
    # What: compute status from the named fixture input; why: status self status later reads status, so activity must retain the computed value under that name.
    status: int
    # What: compute duration s from the named fixture input; why: duration s self duration s later reads duration s, so activity must retain the computed value under that name.
    duration_s: float
    # What: compute ttft s from the named fixture input; why: ttft s self ttft s later reads ttft s, so activity must retain the computed value under that name.
    ttft_s: float | None
    # What: compute response bytes from the named fixture input; why: response bytes self response bytes later reads response bytes, so activity must retain the computed value under that name.
    response_bytes: int
    # What: compute cancelled from the named fixture input; why: cancelled self cancelled later reads cancelled, so activity must retain the computed value under that name.
    cancelled: bool
    # What: compute session id from the named fixture input; why: session id self session id later reads session id, so activity must retain the computed value under that name.
    session_id: str | None
    # What: compute has capture from the named fixture input; why: has capture self has capture later reads has capture, so activity must retain the computed value under that name.
    has_capture: bool

    # What: define public around the current object state; why: its direct callers call public for public and rely on this exact input and result contract.
    def public(self) -> dict:
        # What: return id and timestamp and model and route from public; why: public exposes id and timestamp and model and route so its caller can continue with the function\'s computed outcome.
        return {
            # What: map the id field as id; why: ActivityRecord.public carries id into "id": self.id.
            "id": self.id,
            # What: map the timestamp field as timestamp; why: ActivityRecord.public carries timestamp into "timestamp": self.timestamp.
            "timestamp": self.timestamp,
            # What: map the model field as model; why: ActivityRecord.public sends this field through "model": self.model so the router selects the canonical model or alias for upstream dispatch.
            "model": self.model,
            # What: map the route field as route; why: ActivityRecord.public carries route into "route": self.route.
            "route": self.route,
            # What: map the method field as method; why: ActivityRecord.public carries method into "method": self.method.
            "method": self.method,
            # What: map the status field as status; why: ActivityRecord.public carries status into "status": self.status.
            "status": self.status,
            # What: map the duration s field as duration s; why: ActivityRecord.public carries duration s into "durationS": self.duration_s.
            "durationS": self.duration_s,
            # What: map the ttft s field as ttft s; why: ActivityRecord.public carries ttft s into "ttftS": self.ttft_s.
            "ttftS": self.ttft_s,
            # What: map the response bytes field as response bytes; why: ActivityRecord.public carries response bytes into "responseBytes": self.response_bytes.
            "responseBytes": self.response_bytes,
            # What: map the cancelled field as cancelled; why: ActivityRecord.public carries cancelled into "cancelled": self.cancelled.
            "cancelled": self.cancelled,
            # What: map the session id field as session id; why: ActivityRecord.public carries session id into "sessionId": self.session_id.
            "sessionId": self.session_id,
            # What: map the has capture field as has capture; why: ActivityRecord.public carries has capture into "hasCapture": self.has_capture.
            "hasCapture": self.has_capture,
        # What: complete the enclosing predicate mapping with id and timestamp and model and route and method; why: ActivityRecord.public groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
        }

    # What: bind from_public to the class rather than an instance; why: factory and parser callers construct from_public from class-level state without requiring an existing object.
    @classmethod
    # What: define from_public around item; why: the registered API client call from_public for from public and rely on this exact input and result contract.
    def from_public(cls, item: dict) -> "ActivityRecord":
        # What: gate on isinstance and item and dict before value error; why: from_public admits value error only for this predicate and excludes the opposite state.
        if not isinstance(item, dict):
            # What: raise ValueError for the caller; why:  ActivityRecord.from_public stops this rejected path before it can mutate state, dispatch work, or report success.
            raise ValueError("activity row must be an object")
        # What: compute integer fields from id and status and response bytes; why: if any type item get key is later reads integer fields, so from_public must retain the computed value under that name.
        integer_fields = ("id", "status", "responseBytes")
        # What: gate on any and int and key and integer fields and type before value error; why: from_public admits value error only for this predicate and excludes the opposite state.
        if any(type(item.get(key)) is not int for key in integer_fields):
            # What: raise ValueError for the caller; why:  ActivityRecord.from_public stops this rejected path before it can mutate state, dispatch work, or report success.
            raise ValueError("activity integer field is invalid")
        # What: gate on bool and type and get and item before value error; why: from_public admits value error only for this predicate and excludes the opposite state.
        if type(item.get("cancelled")) is not bool:
            # What: raise ValueError for the caller; why:  ActivityRecord.from_public stops this rejected path before it can mutate state, dispatch work, or report success.
            raise ValueError("activity cancellation field is invalid")
        # What: iterate across the computed value to perform value and get and key and item; why: from_public repeats the body only while or for the loop header admits an iteration.
        for key, maximum in (("model", 128), ("route", 256), ("method", 16)):
            # What: compute value from get and key and item; why: if not isinstance value str or later reads value, so from_public must retain the computed value under that name.
            value = item.get(key)
            # What: gate on value and maximum and isinstance and str and len before value error; why: from_public admits value error only for this predicate and excludes the opposite state.
            if not isinstance(value, str) or not value or len(value) > maximum:
                # What: raise ValueError for the caller; why:  ActivityRecord.from_public stops this rejected path before it can mutate state, dispatch work, or report success.
                raise ValueError("activity string field is invalid")
        # What: compute numeric from get and item and timestamp and duration s; why: if any type value not in later reads numeric, so from_public must retain the computed value under that name.
        numeric = (item.get("timestamp"), item.get("durationS"))
        # What: gate on any and value and numeric and type and int before value error; why: from_public admits value error only for this predicate and excludes the opposite state.
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in numeric):
            # What: raise ValueError for the caller; why:  ActivityRecord.from_public stops this rejected path before it can mutate state, dispatch work, or report success.
            raise ValueError("activity timing field is invalid")
        # What: compute ttft from get and item and ttft s; why: if ttft is not and later reads ttft, so from_public must retain the computed value under that name.
        ttft = item.get("ttftS")
        # What: gate on ttft and type and int and float and isfinite before value error; why: from_public admits value error only for this predicate and excludes the opposite state.
        if ttft is not None and (
            # What: call type with ttft; why: from_public consumes the type return value while evaluating type(ttft) not in (int, float) or not math.isfinite(ttft) or ttft < 0.
            type(ttft) not in (int, float) or not math.isfinite(ttft) or ttft < 0
        # What: complete the enclosing predicate with ttft is not and type ttft not in int; why: ActivityRecord.from_public groups the supplied clauses as one enclosing predicate expression before its value is consumed.
        ):
            # What: raise ValueError for the caller; why:  ActivityRecord.from_public stops this rejected path before it can mutate state, dispatch work, or report success.
            raise ValueError("activity TTFT field is invalid")
        # What: compute session id from get and item and session id; why: if session id is not and later reads session id, so from_public must retain the computed value under that name.
        session_id = item.get("sessionId")
        # What: gate on session id and any and isinstance and str and len before value error; why: from_public admits value error only for this predicate and excludes the opposite state.
        if session_id is not None and (
            # What: call isinstance with session id and str; why: from_public invokes isinstance while performing or len session id; the call advances that operation through its result or side effect.
            not isinstance(session_id, str)
            # What: call len with session id; why: from_public invokes len while performing or any char not in abcdef; the call advances that operation through its result or side effect.
            or len(session_id) != 16
            # What: call any with char and session id and abcdef; why: from_public consumes the any return value while evaluating or any(char not in "0123456789abcdef" for char in session_id).
            or any(char not in "0123456789abcdef" for char in session_id)
        # What: complete the enclosing predicate with session id is not and not isinstance session id str or; why: ActivityRecord.from_public groups the supplied clauses as one enclosing predicate expression before its value is consumed.
        ):
            # What: raise ValueError for the caller; why:  ActivityRecord.from_public stops this rejected path before it can mutate state, dispatch work, or report success.
            raise ValueError("activity session field is invalid")
        # What: gate on item before value error; why: from_public admits value error only for this predicate and excludes the opposite state.
        if (
            # What: apply the item id or item response bytes portion of the enclosing predicate; why: this clause remains in from_public\'s enclosing expression so its grouping and evaluation order stay intact.
            item["id"] < 1 or item["responseBytes"] < 0
            # What: apply the or not item status portion of the enclosing predicate; why: this clause remains in from_public\'s enclosing expression so its grouping and evaluation order stay intact.
            or not 100 <= item["status"] <= 599
            # What: apply the or item timestamp or item duration s portion of the enclosing predicate; why: this clause remains in from_public\'s enclosing expression so its grouping and evaluation order stay intact.
            or item["timestamp"] < 0 or item["durationS"] < 0
        # What: complete the enclosing predicate with if item id 1 or item response bytes 0 or; why: ActivityRecord.from_public groups the supplied clauses as one enclosing predicate expression before its value is consumed.
        ):
            # What: raise ValueError for the caller; why:  ActivityRecord.from_public stops this rejected path before it can mutate state, dispatch work, or report success.
            raise ValueError("activity row is out of range")
        # What: return session id and int and float and str from from_public; why: from_public exposes session id and int and float and str so its caller can continue with the function\'s computed outcome.
        return cls(
            # What: supply id to int; why: from_public binds this int and item and id value to int's id input.
            id=int(item["id"]),
            # What: supply timestamp to float; why: from_public binds this float and item and timestamp value to float's timestamp input.
            timestamp=float(item["timestamp"]),
            # What: supply model to str; why: from_public binds this str and item and model value to str's model input.
            model=str(item["model"]),
            # What: supply route to str; why: from_public binds this str and item and route value to str's route input.
            route=str(item["route"]),
            # What: supply method to str; why: from_public binds this str and item and method value to str's method input.
            method=str(item["method"]),
            # What: supply status to int; why: from_public binds this int and item and status value to int's status input.
            status=int(item["status"]),
            # What: supply duration s to float; why: from_public binds this float and item and duration s value to float's duration s input.
            duration_s=float(item["durationS"]),
            # What: supply ttft s to float; why: from_public binds this float and get and item and ttft s and ttft s value to float's ttft s input.
            ttft_s=float(item["ttftS"]) if item.get("ttftS") is not None else None,
            # What: supply response bytes to int; why: from_public binds this int and item and response bytes value to int's response bytes input.
            response_bytes=int(item["responseBytes"]),
            # What: supply cancelled to bool; why: from_public binds this bool and item and cancelled value to bool's cancelled input.
            cancelled=bool(item["cancelled"]),
            # What: supply session id to cls; why: from_public binds this session id value to cls's session id input.
            session_id=session_id,
            # What: supply has capture to cls; why: from_public binds this false value to cls's has capture input.
            has_capture=False,
        # What: complete the cls call with id and timestamp and model and route and method; why: ActivityRecord.from_public groups the supplied clauses as one cls call before its value is consumed.
        )


# What: define ActivityStore as the owner of __init__ and reconfigure and capture_item_limit and record and list; why: daemon callers use this class boundary so those methods share one activity store state invariant.
class ActivityStore:
    """Thread-safe bounded rows plus a byte-budgeted capture LRU."""
# What: document thread safe bounded rows plus a byte budgeted in the ActivityStore docstring; why: introspection and maintainers read this exact docstring fragment to understand activity store behavior without executing it.

    # What: define __init__ around max entries and capture budget bytes and persistence path and session headers; why: its direct callers call __init__ for init and rely on this exact input and result contract.
    def __init__(
        # What: declare the self input for __init__; why: __init__ consumes self during self lock threading lock, so callers must bind it with the other signature inputs.
        self, max_entries: int, capture_budget_bytes: int, persistence_path: str | None = None,
        # What: declare the session headers input for __init__; why: __init__ consumes session headers during self session headers session headers, so callers must bind it with the other signature inputs.
        session_headers: tuple[str, ...] = (),
    # What: complete the enclosing predicate with group delimiter; why: ActivityStore.__init__ groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ) -> None:
        # What: compute lock from lock and threading; why: the enclosing return or state update later reads lock, so __init__ must retain the computed value under that name.
        self._lock = threading.Lock()
        # What: compute next id from 1; why: the enclosing return or state update later reads next id, so __init__ must retain the computed value under that name.
        self._next_id = 1
        # What: compute records from deque; why: the enclosing return or state update later reads records, so __init__ must retain the computed value under that name.
        self._records: deque[ActivityRecord] = deque()
        # What: compute captures from ordered dict; why: the enclosing return or state update later reads captures, so __init__ must retain the computed value under that name.
        self._captures: OrderedDict[int, tuple[int, dict]] = OrderedDict()
        # What: compute capture bytes from 0; why: the enclosing return or state update later reads capture bytes, so __init__ must retain the computed value under that name.
        self._capture_bytes = 0
        # What: compute max entries from max entries; why: the enclosing return or state update later reads max entries, so __init__ must retain the computed value under that name.
        self._max_entries = max_entries
        # What: compute capture budget from capture budget bytes; why: the enclosing return or state update later reads capture budget, so __init__ must retain the computed value under that name.
        self._capture_budget = capture_budget_bytes
        # What: compute persistence path from persistence path; why: the enclosing return or state update later reads persistence path, so __init__ must retain the computed value under that name.
        self._persistence_path = persistence_path
        # What: compute persisted rows from 0; why: the enclosing return or state update later reads persisted rows, so __init__ must retain the computed value under that name.
        self._persisted_rows = 0
        # What: compute persistence error from the named fixture input; why: the enclosing return or state update later reads persistence error, so __init__ must retain the computed value under that name.
        self._persistence_error: str | None = None
        # What: compute rewrite required from false; why: the enclosing return or state update later reads rewrite required, so __init__ must retain the computed value under that name.
        self._rewrite_required = False
        # What: compute session headers from session headers; why: the enclosing return or state update later reads session headers, so __init__ must retain the computed value under that name.
        self._session_headers = session_headers
        # What: call self._load with the declared inputs; why: __init__ invokes self._load while performing the enclosing return; the call advances that operation through its result or side effect.
        self._load()

    # What: define reconfigure around max entries and capture budget bytes and session headers; why: its direct callers call reconfigure for reconfigure and rely on this exact input and result contract.
    def reconfigure(
        # What: declare the self input for reconfigure; why: reconfigure consumes self during with self lock, so callers must bind it with the other signature inputs.
        self, max_entries: int, capture_budget_bytes: int,
        # What: declare the session headers input for reconfigure; why: reconfigure consumes session headers during if session headers is not, so callers must bind it with the other signature inputs.
        session_headers: tuple[str, ...] | None = None,
    # What: complete the enclosing predicate with group delimiter; why: ActivityStore.reconfigure groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ) -> None:
        # What: enter the lock managed context before self max entries max entries; why: reconfigure releases this resource or lock after self max entries max entries on both success and failure paths.
        with self._lock:
            # What: compute max entries from max entries; why: the enclosing return or state update later reads max entries, so reconfigure must retain the computed value under that name.
            self._max_entries = max_entries
            # What: compute capture budget from capture budget bytes; why: the enclosing return or state update later reads capture budget, so reconfigure must retain the computed value under that name.
            self._capture_budget = capture_budget_bytes
            # What: gate on session headers before session headers and session headers; why: reconfigure admits session headers and session headers only for this predicate and excludes the opposite state.
            if session_headers is not None:
                # What: compute session headers from session headers; why: the enclosing return or state update later reads session headers, so reconfigure must retain the computed value under that name.
                self._session_headers = session_headers
            # What: iterate across max entries and len and records to perform removed and popleft and records; why: reconfigure repeats the body only while or for the loop header admits an iteration.
            while len(self._records) > max_entries:
                # What: compute removed from popleft and records; why: self drop capture locked removed id later reads removed, so reconfigure must retain the computed value under that name.
                removed = self._records.popleft()
                # What: call self._drop_capture_locked with id and removed; why: reconfigure invokes self._drop_capture_locked while performing while self capture bytes capture budget bytes and self captures; the call advances that operation through its result or side effect.
                self._drop_capture_locked(removed.id)
            # What: iterate across captures and capture bytes and capture budget bytes to perform value and popitem and size and captures; why: reconfigure repeats the body only while or for the loop header admits an iteration.
            while self._capture_bytes > capture_budget_bytes and self._captures:
                # What: compute and size and from popitem and captures and false; why: the enclosing return or state update later reads and size and, so reconfigure must retain the computed value under that name.
                _, (size, _) = self._captures.popitem(last=False)
                # What: compute capture bytes from size; why: the enclosing return or state update later reads capture bytes, so reconfigure must retain the computed value under that name.
                self._capture_bytes -= size
            # What: gate on persistence path before compact locked; why: reconfigure admits compact locked only for this predicate and excludes the opposite state.
            if self._persistence_path is not None:
                # What: call self._compact_locked with the declared inputs; why: reconfigure invokes self._compact_locked while performing the enclosing return; the call advances that operation through its result or side effect.
                self._compact_locked()

    # What: expose capture_item_limit as a read-only computed property; why: callers read capture_item_limit through attribute access while its getter retains control of the derived value.
    @property
    # What: define capture_item_limit around the current object state; why: the registered API client call capture_item_limit for capture item limit and rely on this exact input and result contract.
    def capture_item_limit(self) -> int:
        # What: enter the lock managed context before return min self capture budget; why: capture_item_limit releases this resource or lock after return min self capture budget on both success and failure paths.
        with self._lock:
            # What: return min and capture budget and 1024 and 1024 from capture_item_limit; why: capture_item_limit exposes min and capture budget and 1024 and 1024 so its caller can continue with the function\'s computed outcome.
            return min(self._capture_budget, 1024 * 1024)

    # What: define record around model and route and method and status and started and ttft s and response bytes and cancelled and request headers and request body and response headers and response body; why: its direct callers call record for record and rely on this exact input and result contract.
    def record(
        # What: declare the self input for record; why: record consumes self during with self lock, so callers must bind it with the other signature inputs.
        self, *, model: str, route: str, method: str, status: int,
        # What: declare the started input for record; why: record consumes started during duration max time monotonic started, so callers must bind it with the other signature inputs.
        started: float, ttft_s: float | None, response_bytes: int, cancelled: bool,
        # What: declare the request headers input for record; why: record consumes request headers during lowered headers key lower value for key value, so callers must bind it with the other signature inputs.
        request_headers: Mapping[str, str], request_body: bytes,
        # What: declare the response headers input for record; why: record consumes response headers during response headers headers response headers, so callers must bind it with the other signature inputs.
        response_headers: Mapping[str, str], response_body: bytes | None,
    # What: complete the enclosing predicate with dict; why: ActivityStore.record groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ) -> dict:
        # What: compute ended from time; why: id row id timestamp ended model model later reads ended, so record must retain the computed value under that name.
        ended = time.time()
        # What: compute duration from max and started and monotonic and time and 0 0; why: status status duration s round duration later reads duration, so record must retain the computed value under that name.
        duration = max(0.0, time.monotonic() - started)
        # What: compute lowered headers from value and lower and key and items; why: hashlib sha256 str lowered headers header encode utf 8 later reads lowered headers, so record must retain the computed value under that name.
        lowered_headers = {key.lower(): value for key, value in request_headers.items()}
        # What: compute session id from next and header and session headers and hexdigest; why: session id session id has capture has capture later reads session id, so record must retain the computed value under that name.
        session_id = next(
            # What: complete the next call with header; why:  ActivityStore.record groups the supplied clauses as one next call before its value is consumed.
            (
                # What: call operation.hexdigest with the declared inputs; why: record invokes operation.hexdigest while performing for header in self session headers if lowered headers get; the call advances that operation through its result or side effect.
                hashlib.sha256(str(lowered_headers[header]).encode("utf-8")).hexdigest()[:16]
                # What: call lowered_headers.get with header; why: record consumes the lowered_headers.get return value while evaluating for header in self._session_headers if lowered_headers.get(header).
                for header in self._session_headers if lowered_headers.get(header)
            # What: complete the next call with header; why:  ActivityStore.record groups the supplied clauses as one next call before its value is consumed.
            ),
            # What: apply the grouped expression portion of session id; why: record uses this clause to evaluate session id as one grouped value.
            None,
        # What: complete the next call with header; why:  ActivityStore.record groups the supplied clauses as one next call before its value is consumed.
        )
        # What: enter the lock managed context before row id self next id; why: record releases this resource or lock after row id self next id on both success and failure paths.
        with self._lock:
            # What: compute row id from next id; why: id row id later reads row id, so record must retain the computed value under that name.
            row_id = self._next_id
            # What: compute next id from 1; why: the enclosing return or state update later reads next id, so record must retain the computed value under that name.
            self._next_id += 1
            # What: compute has capture from false; why: has capture later reads has capture, so record must retain the computed value under that name.
            has_capture = False
            # What: gate on capture budget and cancelled and response body and len and request body before capture and row id and route and method and headers; why: record admits capture and row id and route and method and headers only for this predicate and excludes the opposite state.
            if (
                # What: apply the self capture budget portion of the enclosing predicate; why: this clause remains in record\'s enclosing expression so its grouping and evaluation order stay intact.
                self._capture_budget > 0
                # What: apply the and not cancelled portion of the enclosing predicate; why: this clause remains in record\'s enclosing expression so its grouping and evaluation order stay intact.
                and not cancelled
                # What: apply the and response body is not portion of the enclosing predicate; why: this clause remains in record\'s enclosing expression so its grouping and evaluation order stay intact.
                and response_body is not None
                # What: call len with request body; why: record consumes the len return value while evaluating and len(request_body) + len(response_body) <= self._capture_budget.
                and len(request_body) + len(response_body) <= self._capture_budget
            # What: complete the enclosing predicate with if self capture budget 0 and not cancelled and response body is; why: ActivityStore.record groups the supplied clauses as one enclosing predicate expression before its value is consumed.
            ):
                # What: compute capture from row id and route and method and headers; why: size len json dumps capture separators encode later reads capture, so record must retain the computed value under that name.
                capture = {
                    # What: map the id field as row id; why: ActivityStore.record carries id through capture into size len json dumps capture separators encode utf 8.
                    "id": row_id,
                    # What: map the route field as route; why: ActivityStore.record carries route through capture into size len json dumps capture separators encode utf 8.
                    "route": route,
                    # What: map the method field as method; why: ActivityStore.record carries method through capture into size len json dumps capture separators encode utf 8.
                    "method": method,
                    # What: map the request headers field as headers and request headers; why: ActivityStore.record carries request headers through capture into size len json dumps capture separators encode utf 8.
                    "requestHeaders": _headers(request_headers),
                    # What: map the request body base64 field as decode and b64encode and request body and base64 and ascii; why: ActivityStore.record carries request body base64 through capture into size len json dumps capture separators encode utf 8.
                    "requestBodyBase64": base64.b64encode(request_body).decode("ascii"),
                    # What: map the response headers field as headers and response headers; why: ActivityStore.record carries response headers through capture into size len json dumps capture separators encode utf 8.
                    "responseHeaders": _headers(response_headers),
                    # What: map the response body base64 field as decode and b64encode and response body and base64 and ascii; why: ActivityStore.record carries response body base64 through capture into size len json dumps capture separators encode utf 8.
                    "responseBodyBase64": base64.b64encode(response_body).decode("ascii"),
                # What: complete the capture mapping with id and route and method and request headers and request body base64; why: ActivityStore.record groups the supplied clauses as one capture mapping before its value is consumed.
                }
                # What: compute size from len and encode and dumps and capture; why: if size self capture budget later reads size, so record must retain the computed value under that name.
                size = len(json.dumps(capture, separators=(",", ":")).encode("utf-8"))
                # What: gate on size and capture budget before captures and capture bytes and old size and capture budget and value; why: record admits captures and capture bytes and old size and capture budget and value only for this predicate and excludes the opposite state.
                if size <= self._capture_budget:
                    # What: iterate across captures and capture budget and capture bytes and size to perform value and popitem and old size and captures; why: record repeats the body only while or for the loop header admits an iteration.
                    while self._capture_bytes + size > self._capture_budget and self._captures:
                        # What: compute and old size and from popitem and captures and false; why: the enclosing return or state update later reads and old size and, so record must retain the computed value under that name.
                        _, (old_size, _) = self._captures.popitem(last=False)
                        # What: compute capture bytes from old size; why: self capture bytes size later reads capture bytes, so record must retain the computed value under that name.
                        self._capture_bytes -= old_size
                    # What: compute captures entry from size and capture; why: the enclosing return or state update later reads captures entry, so record must retain the computed value under that name.
                    self._captures[row_id] = (size, capture)
                    # What: compute capture bytes from size; why: the enclosing return or state update later reads capture bytes, so record must retain the computed value under that name.
                    self._capture_bytes += size
                    # What: compute has capture from true; why: session id session id has capture has capture later reads has capture, so record must retain the computed value under that name.
                    has_capture = True
            # What: compute record from activity record and row id and ended and model; why: self records append record later reads record, so record must retain the computed value under that name.
            record = ActivityRecord(
                # What: supply id to ActivityRecord; why: record binds this row id value to ActivityRecord's id input.
                id=row_id, timestamp=ended, model=model, route=route, method=method,
                # What: supply status to round; why: record binds this status value to round's status input.
                status=status, duration_s=round(duration, 6),
                # What: supply ttft s to round; why: record binds this ttft s and round and 6 value to round's ttft s input.
                ttft_s=round(ttft_s, 6) if ttft_s is not None else None,
                # What: supply response bytes to ActivityRecord; why: record binds this response bytes value to ActivityRecord's response bytes input.
                response_bytes=response_bytes, cancelled=cancelled,
                # What: supply session id to ActivityRecord; why: record binds this session id value to ActivityRecord's session id input.
                session_id=session_id, has_capture=has_capture,
            # What: complete the ActivityRecord call with id and timestamp and model and route and method; why: ActivityStore.record groups the supplied clauses as one ActivityRecord call before its value is consumed.
            )
            # What: call self._records.append with record; why: record invokes self._records.append while performing while len self records self max entries; the call advances that operation through its result or side effect.
            self._records.append(record)
            # What: iterate across max entries and len and records to perform removed and popleft and records; why: record repeats the body only while or for the loop header admits an iteration.
            while len(self._records) > self._max_entries:
                # What: compute removed from popleft and records; why: self drop capture locked removed id later reads removed, so record must retain the computed value under that name.
                removed = self._records.popleft()
                # What: call self._drop_capture_locked with id and removed; why: record invokes self._drop_capture_locked while performing self append locked record; the call advances that operation through its result or side effect.
                self._drop_capture_locked(removed.id)
            # What: call self._append_locked with record; why: record invokes self._append_locked while performing return record public; the call advances that operation through its result or side effect.
            self._append_locked(record)
            # What: return public and record from record; why: record exposes public and record so its caller can continue with the function\'s computed outcome.
            return record.public()

    # What: define list around limit and before id and model; why: its direct callers call list for list and rely on this exact input and result contract.
    def list(self, *, limit: int = 100, before_id: int | None = None, model: str | None = None) -> dict:
        # What: enter the lock managed context before rows row for row in reversed; why: list releases this resource or lock after rows row for row in reversed on both success and failure paths.
        with self._lock:
            # What: compute rows from row and reversed and records and before id; why: for row in rows limit later reads rows, so list must retain the computed value under that name.
            rows = [row for row in reversed(self._records)
                    # What: apply the if before id is or row id before id portion of rows; why: list uses this clause to evaluate rows as one grouped value.
                    if (before_id is None or row.id < before_id) and (model is None or row.model == model)]
            # What: initialize data as an empty runtime accumulator; why: ActivityStore.list appends or maps entries into it during data append item before consuming the aggregate.
            data = []
            # What: iterate across rows and limit to perform item and public and row; why: list repeats the body only while or for the loop header admits an iteration.
            for row in rows[:limit]:
                # What: compute item from public and row; why: item has capture row id in self captures later reads item, so list must retain the computed value under that name.
                item = row.public()
                # What: compute item entry from id and captures and row; why: data append item later reads item entry, so list must retain the computed value under that name.
                item["hasCapture"] = row.id in self._captures
                # What: call data.append with item; why: list invokes data.append while performing return; the call advances that operation through its result or side effect.
                data.append(item)
            # What: return data and len and persistence locked and limit from list; why: list exposes data and len and persistence locked and limit so its caller can continue with the function\'s computed outcome.
            return {
                # What: map the data field as data; why: ActivityStore.list carries data into "data": data.
                "data": data,
                # What: map the count field as len and data; why: ActivityStore.list carries count into "count": len(data).
                "count": len(data),
                # What: map the next before id field as limit and len and rows and data and id; why: ActivityStore.list carries next before id into "nextBeforeId": data[-1]["id"] if len(rows) > limit else None.
                "nextBeforeId": data[-1]["id"] if len(rows) > limit else None,
                # What: map the persistence field as persistence locked; why: ActivityStore.list carries persistence into "persistence": self._persistence_locked().
                "persistence": self._persistence_locked(),
            # What: complete the enclosing predicate mapping with data and count and next before id and persistence; why: ActivityStore.list groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
            }

    # What: define stats around model; why: its direct callers call stats for stats and rely on this exact input and result contract.
    def stats(self, *, model: str | None = None) -> dict:
        # What: enter the lock managed context before rows row for row in self records; why: stats releases this resource or lock after rows row for row in self records on both success and failure paths.
        with self._lock:
            # What: compute rows from row and records and model; why: count len rows later reads rows, so stats must retain the computed value under that name.
            rows = [row for row in self._records if model is None or row.model == model]
            # What: compute count from len and rows; why: count count later reads count, so stats must retain the computed value under that name.
            count = len(rows)
            # What: return count and sum and persistence locked and cancelled from stats; why: stats exposes count and sum and persistence locked and cancelled so its caller can continue with the function\'s computed outcome.
            return {
                # What: map the count field as count; why: ActivityStore.stats carries count into "count": count.
                "count": count,
                # What: map the cancelled field as sum and cancelled and row and rows; why: ActivityStore.stats carries cancelled into "cancelled": sum(row.cancelled for row in rows).
                "cancelled": sum(row.cancelled for row in rows),
                # What: map the errors field as sum and status and row and rows and 400; why: ActivityStore.stats carries errors into "errors": sum(row.status >= 400 for row in rows).
                "errors": sum(row.status >= 400 for row in rows),
                # What: map the response bytes field as sum and response bytes and row and rows; why: ActivityStore.stats carries response bytes into "responseBytes": sum(row.response_bytes for row in rows).
                "responseBytes": sum(row.response_bytes for row in rows),
                # What: map the average duration s field as count and round and sum and duration s; why: ActivityStore.stats carries average duration s into "averageDurationS": round(sum(row.duration_s for row in rows) / count, 6.
                "averageDurationS": round(sum(row.duration_s for row in rows) / count, 6) if count else None,
                # What: map the persistence field as persistence locked; why: ActivityStore.stats carries persistence into "persistence": self._persistence_locked().
                "persistence": self._persistence_locked(),
            # What: complete the enclosing predicate mapping with count and cancelled and errors and response bytes and average duration s; why: ActivityStore.stats groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
            }

    # What: define capture around row id; why: its direct callers call capture for capture and rely on this exact input and result contract.
    def capture(self, row_id: int) -> dict | None:
        # What: enter the lock managed context before item self captures get row id; why: capture releases this resource or lock after item self captures get row id on both success and failure paths.
        with self._lock:
            # What: compute item from get and row id and captures; why: if item is later reads item, so capture must retain the computed value under that name.
            item = self._captures.get(row_id)
            # What: gate on item before the computed value; why: capture admits the computed value only for this predicate and excludes the opposite state.
            if item is None:
                # What: return no value from capture; why: capture returns no value to callers that depend on its completed result.
                return None
            # What: call self._captures.move_to_end with row id; why: capture invokes self._captures.move_to_end while performing return dict item; the call advances that operation through its result or side effect.
            self._captures.move_to_end(row_id)
            # What: return dict and item and 1 from capture; why: capture exposes dict and item and 1 so its caller can continue with the function\'s computed outcome.
            return dict(item[1])

    # What: define _drop_capture_locked around row id; why: its direct callers call _drop_capture_locked for drop capture locked and rely on this exact input and result contract.
    def _drop_capture_locked(self, row_id: int) -> None:
        # What: compute item from pop and row id and captures; why: if item is not later reads item, so _drop_capture_locked must retain the computed value under that name.
        item = self._captures.pop(row_id, None)
        # What: gate on item before capture bytes and item; why: _drop_capture_locked admits capture bytes and item only for this predicate and excludes the opposite state.
        if item is not None:
            # What: compute capture bytes from item and 0; why: the enclosing return or state update later reads capture bytes, so _drop_capture_locked must retain the computed value under that name.
            self._capture_bytes -= item[0]

    # What: define _persistence_locked around the current object state; why: its direct callers call _persistence_locked for persistence locked and rely on this exact input and result contract.
    def _persistence_locked(self) -> dict:
        # What: return persistence error and persistence path and enabled and healthy and error from _persistence_locked; why: _persistence_locked exposes persistence error and persistence path and enabled and healthy and error so its caller can continue with the function\'s computed outcome.
        return {
            # What: map the enabled field as persistence path; why: ActivityStore._persistence_locked carries enabled into "enabled": self._persistence_path is not None.
            "enabled": self._persistence_path is not None,
            # What: map the healthy field as persistence path and persistence error; why: ActivityStore._persistence_locked carries healthy into "healthy": self._persistence_path is None or self._persistence_error is.
            "healthy": self._persistence_path is None or self._persistence_error is None,
            # What: map the error field as persistence error; why: ActivityStore._persistence_locked carries error into "error": self._persistence_error.
            "error": self._persistence_error,
        # What: complete the enclosing predicate mapping with enabled and healthy and error; why: ActivityStore._persistence_locked groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
        }

    # What: define _load around the current object state; why: its direct callers call _load for load and rely on this exact input and result contract.
    def _load(self) -> None:
        # What: gate on persistence path before the computed value; why: _load admits the computed value only for this predicate and excludes the opposite state.
        if self._persistence_path is None:
            # What: return no value from _load; why: _load returns no value to callers that depend on its completed result.
            return
        # What: compute invalid from false; why: invalid later reads invalid, so _load must retain the computed value under that name.
        invalid = False
        # What: compute last id from 0; why: if row id last id later reads last id, so _load must retain the computed value under that name.
        last_id = 0
        # What: establish the handler boundary for the protected operation; why: ActivityStore._load routes failures to file not found error and oserror while preserving cleanup and success flow.
        try:
            # What: enter the open managed context before while line source readline max persisted row chars; why: _load releases this resource or lock after while line source readline max persisted row chars on both success and failure paths.
            with open(self._persistence_path, encoding="utf-8") as source:
                # What: iterate across line and readline and source and max persisted row chars to perform max persisted row chars and invalid and len and line and readline; why: _load repeats the body only while or for the loop header admits an iteration.
                while line := source.readline(_MAX_PERSISTED_ROW_CHARS + 1):
                    # What: gate on max persisted row chars and len and line before invalid; why: _load admits invalid only for this predicate and excludes the opposite state.
                    if len(line) > _MAX_PERSISTED_ROW_CHARS:
                        # What: compute invalid from true; why: invalid later reads invalid, so _load must retain the computed value under that name.
                        invalid = True
                        # What: iterate across line and endswith to perform line and readline and source and max persisted row chars; why: _load repeats the body only while or for the loop header admits an iteration.
                        while line and not line.endswith("\n"):
                            # What: compute line from readline and source and max persisted row chars and 1; why: row activity record from public json loads line later reads line, so _load must retain the computed value under that name.
                            line = source.readline(_MAX_PERSISTED_ROW_CHARS + 1)
                        # What: apply the continue portion of the enclosing predicate; why: this clause remains in _load\'s enclosing expression so its grouping and evaluation order stay intact.
                        continue
                    # What: establish the handler boundary for the protected operation; why: ActivityStore._load routes failures to key error and type error and value error and jsondecode error and json while preserving cleanup and success flow.
                    try:
                        # What: compute row from from public and activity record and loads and line; why: if row id last id later reads row, so _load must retain the computed value under that name.
                        row = ActivityRecord.from_public(json.loads(line))
                        # What: gate on id and last id and row before value error; why: _load admits value error only for this predicate and excludes the opposite state.
                        if row.id <= last_id:
                            # What: raise ValueError for the caller; why: ActivityStore._load stops this rejected path before it can mutate state, dispatch work, or report success.
                            raise ValueError("activity IDs must increase")
                    # What: handle key error and type error and value error and jsondecode error and json by invalid true; why: ActivityStore._load converts that failure into this concrete recovery, response, or cleanup behavior.
                    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                        # What: compute invalid from true; why: if invalid or self persisted rows self max entries later reads invalid, so _load must retain the computed value under that name.
                        invalid = True
                        # What: apply the continue portion of the enclosing predicate; why: this clause remains in _load\'s enclosing expression so its grouping and evaluation order stay intact.
                        continue
                    # What: call self._records.append with row; why: _load invokes self._records.append while performing last id row id; the call advances that operation through its result or side effect.
                    self._records.append(row)
                    # What: compute last id from id and row; why: the enclosing return or state update later reads last id, so _load must retain the computed value under that name.
                    last_id = row.id
                    # What: compute persisted rows from 1; why: if invalid or self persisted rows self max entries later reads persisted rows, so _load must retain the computed value under that name.
                    self._persisted_rows += 1
                    # What: compute next id from max and next id and id and row and 1; why: the enclosing return or state update later reads next id, so _load must retain the computed value under that name.
                    self._next_id = max(self._next_id, row.id + 1)
                    # What: iterate across max entries and len and records to perform popleft and records; why: _load repeats the body only while or for the loop header admits an iteration.
                    while len(self._records) > self._max_entries:
                        # What: call self._records.popleft with the declared inputs; why: _load invokes self._records.popleft while performing except file not found error; the call advances that operation through its result or side effect.
                        self._records.popleft()
        # What: handle file not found error by return; why: ActivityStore._load converts that failure into this concrete recovery, response, or cleanup behavior.
        except FileNotFoundError:
            # What: return no value from _load; why: _load returns no value to callers that depend on its completed result.
            return
        # What: handle oserror by self persistence error load failed; why: ActivityStore._load converts that failure into this concrete recovery, response, or cleanup behavior.
        except OSError:
            # What: compute persistence error from load failed; why: the enclosing return or state update later reads persistence error, so _load must retain the computed value under that name.
            self._persistence_error = "load_failed"
            # What: compute rewrite required from true; why: the enclosing return or state update later reads rewrite required, so _load must retain the computed value under that name.
            self._rewrite_required = True
            # What: return no value from _load; why: _load returns no value to callers that depend on its completed result.
            return
        # What: gate on invalid and persisted rows and max entries before compact locked; why: _load admits compact locked only for this predicate and excludes the opposite state.
        if invalid or self._persisted_rows > self._max_entries:
            # What: call self._compact_locked with the declared inputs; why: _load invokes self._compact_locked while performing the enclosing return; the call advances that operation through its result or side effect.
            self._compact_locked()

    # What: define _append_locked around record; why: its direct callers call _append_locked for append locked and rely on this exact input and result contract.
    def _append_locked(self, record: ActivityRecord) -> None:
        # What: gate on persistence path before the computed value; why: _append_locked admits the computed value only for this predicate and excludes the opposite state.
        if self._persistence_path is None:
            # What: return no value from _append_locked; why: _append_locked returns no value to callers that depend on its completed result.
            return
        # What: gate on rewrite required before compact locked; why: _append_locked admits compact locked only for this predicate and excludes the opposite state.
        if self._rewrite_required:
            # What: call self._compact_locked with the declared inputs; why: _append_locked invokes self._compact_locked while performing return; the call advances that operation through its result or side effect.
            self._compact_locked()
            # What: return no value from _append_locked; why: _append_locked returns no value to callers that depend on its completed result.
            return
        # What: establish the handler boundary for the protected operation; why: ActivityStore._append_locked routes failures to oserror while preserving cleanup and success flow.
        try:
            # What: enter the open managed context before target write json dumps record public separators n; why: _append_locked releases this resource or lock after target write json dumps record public separators n on both success and failure paths.
            with open(self._persistence_path, "a", encoding="utf-8", newline="\n") as target:
                # What: preserve the exact target write json dumps record public separators n literal fragment; why: _append_locked passes this fragment verbatim through target.write(json.dumps(record.public(), separators=(",", ":")) + "\n"), because changing it would alter a protocol payload, serialized fixture, or p.
                target.write(json.dumps(record.public(), separators=(",", ":")) + "\n")
                # What: call target.flush with the declared inputs; why: _append_locked invokes target.flush while performing os fsync target fileno; the call advances that operation through its result or side effect.
                target.flush()
                # What: call os.fsync with fileno and target; why: _append_locked invokes os.fsync while performing self persisted rows; the call advances that operation through its result or side effect.
                os.fsync(target.fileno())
            # What: compute persisted rows from 1; why: if self persisted rows max self max entries later reads persisted rows, so _append_locked must retain the computed value under that name.
            self._persisted_rows += 1
            # What: compute persistence error from the named fixture input; why: self persistence error write failed later reads persistence error, so _append_locked must retain the computed value under that name.
            self._persistence_error = None
            # What: gate on persisted rows and max and max entries before compact locked; why: _append_locked admits compact locked only for this predicate and excludes the opposite state.
            if self._persisted_rows > max(2, self._max_entries * 2):
                # What: call self._compact_locked with the declared inputs; why: _append_locked invokes self._compact_locked while performing except oserror; the call advances that operation through its result or side effect.
                self._compact_locked()
        # What: handle oserror by self persistence error write failed; why: ActivityStore._append_locked converts that failure into this concrete recovery, response, or cleanup behavior.
        except OSError:
            # What: compute persistence error from write failed; why: the enclosing return or state update later reads persistence error, so _append_locked must retain the computed value under that name.
            self._persistence_error = "write_failed"

    # What: define _compact_locked around the current object state; why: its direct callers call _compact_locked for compact locked and rely on this exact input and result contract.
    def _compact_locked(self) -> None:
        # What: gate on persistence path before the computed value; why: _compact_locked admits the computed value only for this predicate and excludes the opposite state.
        if self._persistence_path is None:
            # What: return no value from _compact_locked; why: _compact_locked returns no value to callers that depend on its completed result.
            return
        # What: compute temporary from persistence path and tmp; why: with open temporary w encoding utf 8 later reads temporary, so _compact_locked must retain the computed value under that name.
        temporary = self._persistence_path + ".tmp"
        # What: establish the handler boundary for the protected operation; why: ActivityStore._compact_locked routes failures to oserror while preserving cleanup and success flow.
        try:
            # What: enter the open managed context before for record in self records; why: _compact_locked releases this resource or lock after for record in self records on both success and failure paths.
            with open(temporary, "w", encoding="utf-8", newline="\n") as target:
                # What: iterate across records to perform write and target and dumps and json and public; why: _compact_locked repeats the body only while or for the loop header admits an iteration.
                for record in self._records:
                    # What: preserve the exact target write json dumps record public separators n literal fragment; why: _compact_locked passes this fragment verbatim through target.write(json.dumps(record.public(), separators=(",", ":")) + "\n"), because changing it would alter a protocol payload, serialized fixture.
                    target.write(json.dumps(record.public(), separators=(",", ":")) + "\n")
                # What: call target.flush with the declared inputs; why: _compact_locked invokes target.flush while performing os fsync target fileno; the call advances that operation through its result or side effect.
                target.flush()
                # What: call os.fsync with fileno and target; why: _compact_locked invokes os.fsync while performing os replace temporary self persistence path; the call advances that operation through its result or side effect.
                os.fsync(target.fileno())
            # What: call os.replace with temporary and persistence path; why: _compact_locked invokes os.replace while performing self persisted rows len self records; the call advances that operation through its result or side effect.
            os.replace(temporary, self._persistence_path)
            # What: compute persisted rows from len and records; why: the enclosing return or state update later reads persisted rows, so _compact_locked must retain the computed value under that name.
            self._persisted_rows = len(self._records)
            # What: compute persistence error from the named fixture input; why: self persistence error compact failed later reads persistence error, so _compact_locked must retain the computed value under that name.
            self._persistence_error = None
            # What: compute rewrite required from false; why: the enclosing return or state update later reads rewrite required, so _compact_locked must retain the computed value under that name.
            self._rewrite_required = False
        # What: handle oserror by self persistence error compact failed; why: ActivityStore._compact_locked converts that failure into this concrete recovery, response, or cleanup behavior.
        except OSError:
            # What: compute persistence error from compact failed; why: the enclosing return or state update later reads persistence error, so _compact_locked must retain the computed value under that name.
            self._persistence_error = "compact_failed"
            # What: establish the handler boundary for the protected operation; why: ActivityStore._compact_locked routes failures to oserror while preserving cleanup and success flow.
            try:
                # What: call os.unlink with temporary; why: _compact_locked invokes os.unlink while performing except oserror; the call advances that operation through its result or side effect.
                os.unlink(temporary)
            # What: handle oserror by pass; why: ActivityStore._compact_locked converts that failure into this concrete recovery, response, or cleanup behavior.
            except OSError:
                # What: ignore the anticipated exception handled by this branch; why: _compact_locked continues its retry or cleanup path instead of re-raising that transient failure.
                pass
