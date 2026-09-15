"""Bounded inference activity and opt-in redacted request/response captures."""

from __future__ import annotations

import base64
from collections import OrderedDict, deque
from dataclasses import dataclass
import json
import threading
import time
from typing import Mapping


_SENSITIVE_HEADERS = {
    "authorization", "proxy-authorization", "cookie", "set-cookie", "x-api-key", "x-ft-token",
}


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
            "hasCapture": self.has_capture,
        }


class ActivityStore:
    """Thread-safe bounded rows plus a byte-budgeted capture LRU."""

    def __init__(self, max_entries: int, capture_budget_bytes: int) -> None:
        self._lock = threading.Lock()
        self._next_id = 1
        self._records: deque[ActivityRecord] = deque()
        self._captures: OrderedDict[int, tuple[int, dict]] = OrderedDict()
        self._capture_bytes = 0
        self._max_entries = max_entries
        self._capture_budget = capture_budget_bytes

    def reconfigure(self, max_entries: int, capture_budget_bytes: int) -> None:
        with self._lock:
            self._max_entries = max_entries
            self._capture_budget = capture_budget_bytes
            while len(self._records) > max_entries:
                removed = self._records.popleft()
                self._drop_capture_locked(removed.id)
            while self._capture_bytes > capture_budget_bytes and self._captures:
                _, (size, _) = self._captures.popitem(last=False)
                self._capture_bytes -= size

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
                row_id, ended, model, route, method, status, round(duration, 6),
                round(ttft_s, 6) if ttft_s is not None else None,
                response_bytes, cancelled, has_capture,
            )
            self._records.append(record)
            while len(self._records) > self._max_entries:
                removed = self._records.popleft()
                self._drop_capture_locked(removed.id)
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
            return {"data": data, "count": len(data), "nextBeforeId": data[-1]["id"] if len(rows) > limit else None}

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
