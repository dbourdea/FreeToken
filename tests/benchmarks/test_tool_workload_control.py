"""Unit tests for the bounded tool-workload SSE reconstruction contract."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import patch


# Load the standalone benchmark file by path because benchmark controls are
# deliberately runnable scripts rather than installed package modules.
_SCRIPT = Path(__file__).parents[2] / "benchmarks" / "gmk_evo_x2" / "run_tool_workload_control.py"
_SPEC = importlib.util.spec_from_file_location("tool_workload_control", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
tool_workload_control = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(tool_workload_control)


class _FakeResponse:
    """Minimal context-managed iterable that emulates urllib's SSE response."""

    def __init__(self, lines: list[str]) -> None:
        self._lines = [line.encode("utf-8") for line in lines]

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def __iter__(self):
        return iter(self._lines)


def test_stream_request_reconstructs_fragmented_tool_call_and_usage() -> None:
    """Tool argument fragments, finish reason, and usage survive an SSE stream."""
    lines = [
        "data: " + json.dumps({"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call-1", "type": "function", "function": {"name": "read_fixture", "arguments": '{"path": '}}]}, "finish_reason": None}]}) + "\n",
        "data: " + json.dumps({"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '"calculator.py"}'}}]}, "finish_reason": "tool_calls"}]}) + "\n",
        "data: " + json.dumps({"choices": [], "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10}}) + "\n",
        "data: [DONE]\n",
    ]
    with patch.object(tool_workload_control.urllib.request, "urlopen", return_value=_FakeResponse(lines)):
        body, _, _, timing = tool_workload_control.request_json(
            "http://example.invalid/v1", {"model": "test", "messages": []}
        )
    choice = body["choices"][0]
    call = choice["message"]["tool_calls"][0]
    assert choice["finish_reason"] == "tool_calls"
    assert call["id"] == "call-1"
    assert call["function"] == {"name": "read_fixture", "arguments": '{"path": "calculator.py"}'}
    assert body["usage"]["total_tokens"] == 10
    assert timing["first_tool_call_seconds"] is not None
    assert timing["visible_events"] == []


def test_stream_request_records_visible_ttft_events() -> None:
    """Visible content remains separate from tool-call latency and can form TTFT."""
    lines = [
        'data: {"choices":[{"delta":{"content":"PATCH"},"finish_reason":null}]}\n',
        'data: {"choices":[{"delta":{"content":"_APPLIED"},"finish_reason":"stop"}]}\n',
        'data: {"choices":[],"usage":{"prompt_tokens":5,"completion_tokens":2,"total_tokens":7}}\n',
        'data: [DONE]\n',
    ]
    with patch.object(tool_workload_control.urllib.request, "urlopen", return_value=_FakeResponse(lines)):
        body, started, finished, timing = tool_workload_control.request_json(
            "http://example.invalid/v1", {"model": "test", "messages": []}
        )
    observation = tool_workload_control.observe("visible", body, started, finished, timing)
    assert observation["content"] == "PATCH_APPLIED"
    assert observation["ttft_seconds"] is not None
    assert len(observation["token_gap_seconds"]) == 1
    assert observation["first_tool_call_seconds"] is None
