from __future__ import annotations

from datetime import datetime, timezone
import threading
import time

from freetoken.daemon.performance import PerformanceMonitor


def test_performance_history_is_one_hour_bounded_and_filterable():
    clock = [1_700_000_000.0]
    values = [10, 20, 30]
    monitor = PerformanceMonitor(
        lambda: {
            "ramBytes": values.pop(0), "vramBytes": 7,
            "ramAvailable": True, "vramAvailable": False,
            "ramSource": "test-pss", "vramSource": None,
            "pids": [123],
        },
        every_s=1800,
        wall_now=lambda: clock[0],
    )
    for timestamp in (1_700_000_000.0, 1_700_001_800.0, 1_700_003_600.0):
        clock[0] = timestamp
        monitor.sample_once()

    result = monitor.current()
    assert [row["ram_bytes"] for row in result["sys_stats"]] == [20, 30]
    assert result["gpu_stats"] == []
    assert result["retentionS"] == 3600
    assert "pids" not in result["sys_stats"][0]
    assert result["sys_stats"][0]["scope"] == "engine-process-tree"

    after = datetime.fromtimestamp(1_700_001_800.0, timezone.utc)
    assert [row["ram_bytes"] for row in monitor.current(after=after)["sys_stats"]] == [30]


def test_performance_probe_failure_is_generic_and_recovers():
    fail = [True]

    def sample():
        if fail[0]:
            raise RuntimeError("private probe detail")
        return {}

    monitor = PerformanceMonitor(sample)
    monitor.sample_once()
    assert monitor.current()["error"] == "sample_failed"
    fail[0] = False
    monitor.sample_once()
    assert monitor.current()["healthy"] is True
    assert monitor.current()["error"] is None


def test_performance_sampler_stops_and_reconfigures_without_old_generation_resuming():
    sampled = threading.Event()
    calls = []

    def sample():
        calls.append(len(calls))
        sampled.set()
        return {}

    monitor = PerformanceMonitor(sample, every_s=0.01)
    monitor.start()
    assert sampled.wait(1)
    monitor.reconfigure(0.02, False)
    sampled.clear()
    assert sampled.wait(1)
    monitor.stop()
    stopped_at = len(calls)
    time.sleep(0.05)
    assert len(calls) == stopped_at
