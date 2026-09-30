# What: enable postponed evaluation of annotations; why: type hints in test_performance can reference runtime types without eager imports or forward-reference failures.
from __future__ import annotations

# What: arrange from datetime import datetime timezone for the scenario; why: test performance requires this concrete input or helper state before exercising the behavior under test.
from datetime import datetime, timezone
# What: import threading for test performance sampler stops and reconfigures without old generation resuming using threading; why: test_performance_sampler_stops_and_reconfigures_without_old_generation_resuming uses threading event, making that imported dependency available to its named operation.
import threading
# What: import time for test performance sampler stops and reconfigures without old generation resuming using time; why: test_performance_sampler_stops_and_reconfigures_without_old_generation_resuming uses time sleep, making that imported dependency available to its named operation.
import time

# What: arrange from freetoken daemon performance import PerformanceMonitor for the scenario; why: test performance requires this concrete input or helper state before exercising the behavior under test.
from freetoken.daemon.performance import PerformanceMonitor


# What: define the test_performance_history_is_one_hour_bounded_and_filterable test around local fixtures; why: this test groups the arrange, act, and assertions that protect the performance history is one hour bounded and filterable outcome.
def test_performance_history_is_one_hour_bounded_and_filterable():
    # What: arrange clock as 1700000000 0; why: the performance history is one hour bounded and filterable test consumes this named precondition before exercising the behavior.
    clock = [1_700_000_000.0]
    # What: arrange values as 10 and 20 and 30; why: the performance history is one hour bounded and filterable test consumes this named precondition before exercising the behavior.
    values = [10, 20, 30]
    # What: act by calling PerformanceMonitor and capture monitor; why: the performance history is one hour bounded and filterable test asserts the response, state, or failure produced by this call.
    monitor = PerformanceMonitor(
        # What: arrange the lambda portion of monitor; why: the performance history is one hour bounded and filterable scenario uses this clause to evaluate monitor as one grouped value.
        lambda: {
            # What: arrange the ram bytes field as pop and values and 0; why: test_performance_history_is_one_hour_bounded_and_filterable carries ram bytes through monitor into monitor sample once.
            "ramBytes": values.pop(0), "vramBytes": 7,
            # What: arrange the ram available field as true; why: test_performance_history_is_one_hour_bounded_and_filterable carries ram available through monitor into monitor sample once.
            "ramAvailable": True, "vramAvailable": False,
            # What: arrange the ram source field as test pss; why: test_performance_history_is_one_hour_bounded_and_filterable carries ram source through monitor into monitor sample once.
            "ramSource": "test-pss", "vramSource": None,
            # What: arrange the pids field as 123; why: test_performance_history_is_one_hour_bounded_and_filterable carries pids through monitor into monitor sample once.
            "pids": [123],
        # What: arrange the monitor mapping with ram bytes and vram bytes and ram available and vram available and ram source; why: test_performance_history_is_one_hour_bounded_and_filterable groups the supplied clauses as one monitor mapping before its value is consumed.
        },
        # What: arrange every s to PerformanceMonitor; why: the performance history is one hour bounded and filterable scenario binds this 1800 value to PerformanceMonitor's every s input.
        every_s=1800,
        # What: arrange wall now to PerformanceMonitor; why: the performance history is one hour bounded and filterable scenario binds this clock and 0 value to PerformanceMonitor's wall now input.
        wall_now=lambda: clock[0],
    # What: arrange the PerformanceMonitor call with every s and wall now; why: test_performance_history_is_one_hour_bounded_and_filterable groups the supplied clauses as one PerformanceMonitor call before its value is consumed.
    )
    # What: act across the computed value to perform timestamp and clock; why: the performance history is one hour bounded and filterable scenario repeats the body only while or for the loop header admits an iteration.
    for timestamp in (1_700_000_000.0, 1_700_001_800.0, 1_700_003_600.0):
        # What: arrange clock entry as timestamp; why: the performance history is one hour bounded and filterable test consumes this named precondition before exercising the behavior.
        clock[0] = timestamp
        # What: act by calling monitor.sample_once with the declared inputs; why: the performance history is one hour bounded and filterable scenario observes the monitor.sample_once return value during result monitor current.
        monitor.sample_once()

    # What: act by calling monitor.current and capture result; why: the performance history is one hour bounded and filterable test asserts the response, state, or failure produced by this call.
    result = monitor.current()
    # What: assert that row ram bytes for row in result equals 20 30; why: this assertion protects the performance history is one hour bounded and filterable regression after the test's arranged inputs and exercised call.
    assert [row["ram_bytes"] for row in result["sys_stats"]] == [20, 30]
    # What: assert that result gpu stats equals group delimiter; why: this assertion protects the performance history is one hour bounded and filterable regression after the test's arranged inputs and exercised call.
    assert result["gpu_stats"] == []
    # What: assert that result retention s equals 3600; why: this assertion protects the performance history is one hour bounded and filterable regression after the test's arranged inputs and exercised call.
    assert result["retentionS"] == 3600
    # What: assert that pids is absent from result sys stats 0; why: this assertion protects the performance history is one hour bounded and filterable regression after the test's arranged inputs and exercised call.
    assert "pids" not in result["sys_stats"][0]
    # What: assert that result sys stats 0 scope equals engine process tree; why: this assertion protects the performance history is one hour bounded and filterable regression after the test's arranged inputs and exercised call.
    assert result["sys_stats"][0]["scope"] == "engine-process-tree"

    # What: act by calling datetime.fromtimestamp and capture after; why: the performance history is one hour bounded and filterable test asserts the response, state, or failure produced by this call.
    after = datetime.fromtimestamp(1_700_001_800.0, timezone.utc)
    # What: assert that row ram bytes for row in monitor current equals 30; why: this assertion protects the performance history is one hour bounded and filterable regression after the test's arranged inputs and exercised call.
    assert [row["ram_bytes"] for row in monitor.current(after=after)["sys_stats"]] == [30]


# What: define the test_performance_probe_failure_is_generic_and_recovers test around local fixtures; why: this test groups the arrange, act, and assertions that protect the performance probe failure is generic and recovers outcome.
def test_performance_probe_failure_is_generic_and_recovers():
    # What: arrange fail as true; why: the performance probe failure is generic and recovers test consumes this named precondition before exercising the behavior.
    fail = [True]

    # What: define the sample test helper around captured fixture state; why: the performance probe failure is generic and recovers scenario calls this helper to produce or observe the exact behavior checked by its assertions.
    def sample():
        # What: act on fail before runtime error; why: the performance probe failure is generic and recovers scenario admits runtime error only for this predicate and excludes the opposite state.
        if fail[0]:
            # What: raise RuntimeError for the caller; why: sample stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RuntimeError("private probe detail")
        # What: return no value from the sample test helper; why: the performance probe failure is generic and recovers scenario uses this helper result in its subsequent act or assertion.
        return {}

    # What: act by calling PerformanceMonitor and capture monitor; why: the performance probe failure is generic and recovers test asserts the response, state, or failure produced by this call.
    monitor = PerformanceMonitor(sample)
    # What: act by calling monitor.sample_once with the declared inputs; why: the performance probe failure is generic and recovers scenario observes the monitor.sample_once return value during assert monitor current error sample failed.
    monitor.sample_once()
    # What: assert that monitor current error equals sample failed; why: this assertion protects the performance probe failure is generic and recovers regression after the test's arranged inputs and exercised call.
    assert monitor.current()["error"] == "sample_failed"
    # What: arrange fail entry as false; why: the performance probe failure is generic and recovers test consumes this named precondition before exercising the behavior.
    fail[0] = False
    # What: act by calling monitor.sample_once with the declared inputs; why: the performance probe failure is generic and recovers scenario observes the monitor.sample_once return value during assert monitor current healthy is.
    monitor.sample_once()
    # What: assert that monitor current healthy is true; why: this assertion protects the performance probe failure is generic and recovers regression after the test's arranged inputs and exercised call.
    assert monitor.current()["healthy"] is True
    # What: assert that monitor current error is group delimiter; why: this assertion protects the performance probe failure is generic and recovers regression after the test's arranged inputs and exercised call.
    assert monitor.current()["error"] is None


# What: define the test_performance_sampler_stops_and_reconfigures_without_old_generation_resuming test around local fixtures; why: this test groups the arrange, act, and assertions that protect the performance sampler stops and reconfigures without old generation resuming outcome.
def test_performance_sampler_stops_and_reconfigures_without_old_generation_resuming():
    # What: act by calling threading.Event and capture sampled; why: the performance sampler stops and reconfigures without old generation resuming test asserts the response, state, or failure produced by this call.
    sampled = threading.Event()
    # What: arrange calls as the fixture input; why: the performance sampler stops and reconfigures without old generation resuming test consumes this named precondition before exercising the behavior.
    calls = []

    # What: define the sample test helper around captured fixture state; why: the performance sampler stops and reconfigures without old generation resuming scenario calls this helper to produce or observe the exact behavior checked by its assertions.
    def sample():
        # What: act by calling calls.append with len and calls; why: the performance sampler stops and reconfigures without old generation resuming scenario observes the calls.append return value during sampled set.
        calls.append(len(calls))
        # What: act by calling sampled.set with the declared inputs; why: the performance sampler stops and reconfigures without old generation resuming scenario observes the sampled.set return value during return.
        sampled.set()
        # What: return no value from the sample test helper; why: the performance sampler stops and reconfigures without old generation resuming scenario uses this helper result in its subsequent act or assertion.
        return {}

    # What: act by calling PerformanceMonitor and capture monitor; why: the performance sampler stops and reconfigures without old generation resuming test asserts the response, state, or failure produced by this call.
    monitor = PerformanceMonitor(sample, every_s=0.01)
    # What: act by calling monitor.start with the declared inputs; why: the performance sampler stops and reconfigures without old generation resuming scenario observes the monitor.start return value during assert sampled wait.
    monitor.start()
    # What: assert that sampled wait 1; why: this assertion protects the performance sampler stops and reconfigures without old generation resuming regression after the test's arranged inputs and exercised call.
    assert sampled.wait(1)
    # What: act by calling monitor.reconfigure with 0 02 and false; why: the performance sampler stops and reconfigures without old generation resuming scenario observes the monitor.reconfigure return value during sampled clear.
    monitor.reconfigure(0.02, False)
    # What: act by calling sampled.clear with the declared inputs; why: the performance sampler stops and reconfigures without old generation resuming scenario observes the sampled.clear return value during assert sampled wait.
    sampled.clear()
    # What: assert that sampled wait 1; why: this assertion protects the performance sampler stops and reconfigures without old generation resuming regression after the test's arranged inputs and exercised call.
    assert sampled.wait(1)
    # What: act by calling monitor.stop with the declared inputs; why: the performance sampler stops and reconfigures without old generation resuming scenario observes the monitor.stop return value during stopped at len calls.
    monitor.stop()
    # What: act by calling len and capture stopped at; why: the performance sampler stops and reconfigures without old generation resuming test asserts the response, state, or failure produced by this call.
    stopped_at = len(calls)
    # What: act by calling time.sleep with 0 05; why: the performance sampler stops and reconfigures without old generation resuming scenario observes the time.sleep return value during assert len calls stopped at.
    time.sleep(0.05)
    # What: assert that len calls equals stopped at; why: this assertion protects the performance sampler stops and reconfigures without old generation resuming regression after the test's arranged inputs and exercised call.
    assert len(calls) == stopped_at
