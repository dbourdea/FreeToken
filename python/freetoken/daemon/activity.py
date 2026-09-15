"""Bounded inference activity and opt-in redacted request/response captures."""

from __future__ import annotations

import base64
from collections import OrderedDict, deque
from dataclasses import dataclass
import hashlib
import json
import math
import os
import threading
import time
from typing import Mapping


_SENSITIVE_HEADERS = {
    "authorization", "proxy-authorization", "cookie", "set-cookie", "x-api-key", "x-ft-token",
}
_MAX_PERSISTED_ROW_CHARS = 8192


def _sensitive_header(name: str) -> bool:
    normalized = name.lower().replace("_", "-")
    parts = normalized.split("-")
    return (
        normalized in _SENSITIVE_HEADERS
        or "token" in parts
        or "secret" in parts
        or ("api" in parts and "key" in parts)
    )


def _headers(values: Mapping[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in list(values.items())[:64]:
        result[key] = "[REDACTED]" if _sensitive_header(key) else str(value)[:1024]
    return result


@dataclass(frozen=True)
class ActivityRecord:
    id: int
    timestamp: float
    model: str
    route: str
    method: str
    status: int
    duration_s: float
    ttft_s: float | None
    response_bytes: int
    cancelled: bool
    session_id: str | None
    has_capture: bool

    def public(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "model": self.model,
            "route": self.route,
            "method": self.method,
            "status": self.status,
            "durationS": self.duration_s,
            "ttftS": self.ttft_s,
            "responseBytes": self.response_bytes,
            "cancelled": self.cancelled,
            "sessionId": self.session_id,
            "hasCapture": self.has_capture,
        }

    @classmethod
    def from_public(cls, item: dict) -> "ActivityRecord":
        if not isinstance(item, dict):
            raise ValueError("activity row must be an object")
        integer_fields = ("id", "status", "responseBytes")
        if any(type(item.get(key)) is not int for key in integer_fields):
            raise ValueError("activity integer field is invalid")
        if type(item.get("cancelled")) is not bool:
            raise ValueError("activity cancellation field is invalid")
        for key, maximum in (("model", 128), ("route", 256), ("method", 16)):
            value = item.get(key)
            if not isinstance(value, str) or not value or len(value) > maximum:
                raise ValueError("activity string field is invalid")
        numeric = (item.get("timestamp"), item.get("durationS"))
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in numeric):
            raise ValueError("activity timing field is invalid")
        ttft = item.get("ttftS")
        if ttft is not None and (
            type(ttft) not in (int, float) or not math.isfinite(ttft) or ttft < 0
        ):
            raise ValueError("activity TTFT field is invalid")
        session_id = item.get("sessionId")
        if session_id is not None and (
            not isinstance(session_id, str)
            or len(session_id) != 16
            or any(char not in "0123456789abcdef" for char in session_id)
        ):
            raise ValueError("activity session field is invalid")
        if (
            item["id"] < 1 or item["responseBytes"] < 0
            or not 100 <= item["status"] <= 599
            or item["timestamp"] < 0 or item["durationS"] < 0
        ):
            raise ValueError("activity row is out of range")
        return cls(
            id=int(item["id"]),
            timestamp=float(item["timestamp"]),
            model=str(item["model"]),
            route=str(item["route"]),
            method=str(item["method"]),
            status=int(item["status"]),
            duration_s=float(item["durationS"]),
            ttft_s=float(item["ttftS"]) if item.get("ttftS") is not None else None,
            response_bytes=int(item["responseBytes"]),
            cancelled=bool(item["cancelled"]),
            session_id=session_id,
            has_capture=False,
        )


class ActivityStore:
    """Thread-safe bounded rows plus a byte-budgeted capture LRU."""

    def __init__(
        self, max_entries: int, capture_budget_bytes: int, persistence_path: str | None = None,
        session_headers: tuple[str, ...] = (),
    ) -> None:
        self._lock = threading.Lock()
        self._next_id = 1
        self._records: deque[ActivityRecord] = deque()
        self._captures: OrderedDict[int, tuple[int, dict]] = OrderedDict()
        self._capture_bytes = 0
        self._max_entries = max_entries
        self._capture_budget = capture_budget_bytes
        self._persistence_path = persistence_path
        self._persisted_rows = 0
        self._persistence_error: str | None = None
        self._rewrite_required = False
        self._session_headers = session_headers
        self._load()

    def reconfigure(
        self, max_entries: int, capture_budget_bytes: int,
        session_headers: tuple[str, ...] | None = None,
    ) -> None:
        with self._lock:
            self._max_entries = max_entries
            self._capture_budget = capture_budget_bytes
            if session_headers is not None:
                self._session_headers = session_headers
            while len(self._records) > max_entries:
                removed = self._records.popleft()
                self._drop_capture_locked(removed.id)
            while self._capture_bytes > capture_budget_bytes and self._captures:
                _, (size, _) = self._captures.popitem(last=False)
                self._capture_bytes -= size
            if self._persistence_path is not None:
                self._compact_locked()

    @property
    def capture_item_limit(self) -> int:
        with self._lock:
            return min(self._capture_budget, 1024 * 1024)

    def record(
        self, *, model: str, route: str, method: str, status: int,
        started: float, ttft_s: float | None, response_bytes: int, cancelled: bool,
        request_headers: Mapping[str, str], request_body: bytes,
        response_headers: Mapping[str, str], response_body: bytes | None,
    ) -> dict:
        ended = time.time()
        duration = max(0.0, time.monotonic() - started)
        lowered_headers = {key.lower(): value for key, value in request_headers.items()}
        session_id = next(
            (
                hashlib.sha256(str(lowered_headers[header]).encode("utf-8")).hexdigest()[:16]
                for header in self._session_headers if lowered_headers.get(header)
            ),
            None,
        )
        with self._lock:
            row_id = self._next_id
            self._next_id += 1
            has_capture = False
            if (
                self._capture_budget > 0
                and not cancelled
                and response_body is not None
                and len(request_body) + len(response_body) <= self._capture_budget
            ):
                capture = {
                    "id": row_id,
                    "route": route,
                    "method": method,
                    "requestHeaders": _headers(request_headers),
                    "requestBodyBase64": base64.b64encode(request_body).decode("ascii"),
                    "responseHeaders": _headers(response_headers),
                    "responseBodyBase64": base64.b64encode(response_body).decode("ascii"),
                }
                size = len(json.dumps(capture, separators=(",", ":")).encode("utf-8"))
                if size <= self._capture_budget:
                    while self._capture_bytes + size > self._capture_budget and self._captures:
                        _, (old_size, _) = self._captures.popitem(last=False)
                        self._capture_bytes -= old_size
                    self._captures[row_id] = (size, capture)
                    self._capture_bytes += size
                    has_capture = True
            record = ActivityRecord(
                id=row_id, timestamp=ended, model=model, route=route, method=method,
                status=status, duration_s=round(duration, 6),
                ttft_s=round(ttft_s, 6) if ttft_s is not None else None,
                response_bytes=response_bytes, cancelled=cancelled,
                session_id=session_id, has_capture=has_capture,
            )
            self._records.append(record)
            while len(self._records) > self._max_entries:
                removed = self._records.popleft()
                self._drop_capture_locked(removed.id)
            self._append_locked(record)
            return record.public()

    def list(self, *, limit: int = 100, before_id: int | None = None, model: str | None = None) -> dict:
        with self._lock:
            rows = [row for row in reversed(self._records)
                    if (before_id is None or row.id < before_id) and (model is None or row.model == model)]
            data = []
            for row in rows[:limit]:
                item = row.public()
                item["hasCapture"] = row.id in self._captures
                data.append(item)
            return {
                "data": data,
                "count": len(data),
                "nextBeforeId": data[-1]["id"] if len(rows) > limit else None,
                "persistence": self._persistence_locked(),
            }

    def stats(self, *, model: str | None = None) -> dict:
        with self._lock:
            rows = [row for row in self._records if model is None or row.model == model]
            count = len(rows)
            return {
                "count": count,
                "cancelled": sum(row.cancelled for row in rows),
                "errors": sum(row.status >= 400 for row in rows),
                "responseBytes": sum(row.response_bytes for row in rows),
                "averageDurationS": round(sum(row.duration_s for row in rows) / count, 6) if count else None,
                "persistence": self._persistence_locked(),
            }

    def capture(self, row_id: int) -> dict | None:
        with self._lock:
            item = self._captures.get(row_id)
            if item is None:
                return None
            self._captures.move_to_end(row_id)
            return dict(item[1])

    def _drop_capture_locked(self, row_id: int) -> None:
        item = self._captures.pop(row_id, None)
        if item is not None:
            self._capture_bytes -= item[0]

    def _persistence_locked(self) -> dict:
        return {
            "enabled": self._persistence_path is not None,
            "healthy": self._persistence_path is None or self._persistence_error is None,
            "error": self._persistence_error,
        }

    def _load(self) -> None:
        if self._persistence_path is None:
            return
        invalid = False
        last_id = 0
        try:
            with open(self._persistence_path, encoding="utf-8") as source:
                while line := source.readline(_MAX_PERSISTED_ROW_CHARS + 1):
                    if len(line) > _MAX_PERSISTED_ROW_CHARS:
                        invalid = True
                        while line and not line.endswith("\n"):
                            line = source.readline(_MAX_PERSISTED_ROW_CHARS + 1)
                        continue
                    try:
                        row = ActivityRecord.from_public(json.loads(line))
                        if row.id <= last_id:
                            raise ValueError("activity IDs must increase")
                    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                        invalid = True
                        continue
                    self._records.append(row)
                    last_id = row.id
                    self._persisted_rows += 1
                    self._next_id = max(self._next_id, row.id + 1)
                    while len(self._records) > self._max_entries:
                        self._records.popleft()
        except FileNotFoundError:
            return
        except OSError:
            self._persistence_error = "load_failed"
            self._rewrite_required = True
            return
        if invalid or self._persisted_rows > self._max_entries:
            self._compact_locked()

    def _append_locked(self, record: ActivityRecord) -> None:
        if self._persistence_path is None:
            return
        if self._rewrite_required:
            self._compact_locked()
            return
        try:
            with open(self._persistence_path, "a", encoding="utf-8", newline="\n") as target:
                target.write(json.dumps(record.public(), separators=(",", ":")) + "\n")
                target.flush()
                os.fsync(target.fileno())
            self._persisted_rows += 1
            self._persistence_error = None
            if self._persisted_rows > max(2, self._max_entries * 2):
                self._compact_locked()
        except OSError:
            self._persistence_error = "write_failed"

    def _compact_locked(self) -> None:
        if self._persistence_path is None:
            return
        temporary = self._persistence_path + ".tmp"
        try:
            with open(temporary, "w", encoding="utf-8", newline="\n") as target:
                for record in self._records:
                    target.write(json.dumps(record.public(), separators=(",", ":")) + "\n")
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary, self._persistence_path)
            self._persisted_rows = len(self._records)
            self._persistence_error = None
            self._rewrite_required = False
        except OSError:
            self._persistence_error = "compact_failed"
            try:
                os.unlink(temporary)
            except OSError:
                pass
