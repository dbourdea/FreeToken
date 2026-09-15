"""Bounded periodic history for the owned engine process tree only."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import threading
import time
from typing import Callable


class PerformanceMonitor:
    """Sample a privacy-bounded probe for at most one hour."""

    def __init__(
        self, sample_fn: Callable[[], dict], *, every_s: float = 5.0,
        disabled: bool = False, wall_now: Callable[[], float] = time.time,
    ) -> None:
        self._sample_fn = sample_fn
        self._wall_now = wall_now
        self._lock = threading.Lock()
        self._stop: threading.Event | None = None
        self._thread: threading.Thread | None = None
        self._started = False
        self._rows: deque[dict] = deque()
        self._error: str | None = None
        self._every_s = every_s
        self._disabled = disabled
        self._capacity = max(1, int(3600 / every_s))

    def start(self) -> None:
        with self._lock:
            self._started = True
            if self._disabled or self._thread is not None:
                return
            stop = threading.Event()
            self._stop = stop
            self._thread = threading.Thread(
                target=self._run, args=(stop,), name="ft-daemon-performance", daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._started = False
            thread = self._thread
            self._thread = None
            stop = self._stop
            self._stop = None
            if stop is not None:
                stop.set()
        if thread is not None:
            thread.join(timeout=max(1.0, min(self._every_s, 5.0)))

    def reconfigure(self, every_s: float, disabled: bool) -> None:
        with self._lock:
            changed = every_s != self._every_s or disabled != self._disabled
            restart = self._started
        if not changed:
            return
        self.stop()
        with self._lock:
            self._every_s = every_s
            self._disabled = disabled
            self._capacity = max(1, int(3600 / every_s))
            self._rows.clear()
            self._error = None
        if restart:
            self.start()

    def sample_once(self) -> None:
        try:
            measured = self._sample_fn()
            row = {
                "timestamp": datetime.fromtimestamp(
                    self._wall_now(), timezone.utc
                ).isoformat().replace("+00:00", "Z"),
                "scope": "engine-process-tree",
                "ram_bytes": int(measured.get("ramBytes", 0)),
                "vram_bytes": int(measured.get("vramBytes", 0)),
                "ram_available": bool(measured.get("ramAvailable", False)),
                "vram_available": bool(measured.get("vramAvailable", False)),
                "ram_source": measured.get("ramSource"),
                "vram_source": measured.get("vramSource"),
            }
        except Exception:  # noqa: BLE001 - monitoring must never break routing
            with self._lock:
                self._error = "sample_failed"
            return
        with self._lock:
            self._rows.append(row)
            while len(self._rows) > self._capacity:
                self._rows.popleft()
            self._error = None

    def current(self, *, after: datetime | None = None) -> dict:
        cutoff = after.timestamp() if after is not None else None
        with self._lock:
            rows = [dict(row) for row in self._rows]
            state = {
                "enabled": not self._disabled,
                "everyS": self._every_s,
                "retentionS": 3600,
                "healthy": self._error is None,
                "error": self._error,
            }
        if cutoff is not None:
            rows = [
                row for row in rows
                if datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")).timestamp()
                > cutoff
            ]
        return {**state, "sys_stats": rows, "gpu_stats": []}

    def _run(self, stop: threading.Event) -> None:
        while not stop.wait(self._every_s):
            self.sample_once()
