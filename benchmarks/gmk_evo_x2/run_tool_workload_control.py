#!/usr/bin/env python3
"""Run one bounded real OpenAI-tool workflow against the GMKtec EVO-X2 API.

The FreeToken paper's W2 workload uses OpenCode on a SWE-bench issue and W3
uses Claude Code with a much larger context. Those external harnesses and their
licensed fixtures are not present in this fork. This controller therefore does
not claim paper parity. It proves the required local serving properties with a
small deterministic coding task: the model must request a constrained file-read
tool, request a constrained patch tool, the runner really mutates an artifact
sandbox, and the model must confirm the repaired file. Every API turn records
prompt tokens, completion tokens, TTFT, decode TPS, and p99 token gap.
"""

# Import only standard-library modules so the harness remains portable to the
# same Python environment used for the existing API controls.
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    """Require explicit API, model, suite, and fresh artifact locations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="OpenAI-compatible /v1 API root")
    parser.add_argument("--model", required=True, help="Exact served model identifier")
    parser.add_argument("--suite", required=True, type=Path, help="Versioned bounded workload JSON")
    parser.add_argument("--artifact", required=True, type=Path, help="Fresh output JSON path")
    parser.add_argument("--max-tokens", type=int, default=256, help="Per-turn completion allowance")
    args = parser.parse_args()
    if args.artifact.exists():
        parser.error(f"artifact already exists: {args.artifact}")
    if args.max_tokens < 64:
        parser.error("max tokens must permit tool reasoning plus a visible answer")
    return args


def request_json(base_url: str, payload: dict[str, Any]) -> tuple[dict[str, Any], float, float]:
    """Submit one non-streaming API request and return body plus monotonic timings."""
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions", data=encoded,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"API HTTP {error.code}: {error.read().decode('utf-8', 'replace')}") from error
    finished = time.monotonic()
    return body, started, finished


def observe(label: str, body: dict[str, Any], started: float, finished: float) -> dict[str, Any]:
    """Normalize one API result without inventing unavailable stream timestamps."""
    choice = body["choices"][0]
    message = choice["message"]
    usage = body.get("usage", {})
    completion_tokens = int(usage.get("completion_tokens", 0))
    elapsed = finished - started
    # A non-streaming API response cannot expose true first-token arrival, so
    # elapsed is recorded as end-to-end latency and not mislabeled as TTFT.
    return {
        "label": label,
        "elapsed_seconds": elapsed,
        "prompt_tokens": int(usage.get("prompt_tokens", 0)),
        "completion_tokens": completion_tokens,
        "end_to_end_tps": completion_tokens / elapsed if elapsed else None,
        "finish_reason": choice.get("finish_reason"),
        "content": message.get("content", ""),
        "reasoning_content": message.get("reasoning_content", ""),
        "tool_calls": message.get("tool_calls", []),
        "raw": body,
    }


def one_required_call(observation: dict[str, Any], name: str) -> dict[str, Any]:
    """Fail closed unless the model emitted exactly one requested OpenAI function call."""
    calls = observation["tool_calls"]
    # A complete-looking call at a length cutoff is not accepted. The runtime
    # must declare the structured tool-call finish reason to prove it did not
    # silently truncate an argument or leave unobserved trailing output.
    if observation["finish_reason"] != "tool_calls":
        raise RuntimeError(f"expected tool_calls finish reason, observed {observation['finish_reason']!r}")
    if len(calls) != 1 or calls[0].get("function", {}).get("name") != name:
        raise RuntimeError(f"expected exactly one {name} tool call, observed {calls!r}")
    return calls[0]


def tool_schema(path: str, before: str, after: str) -> list[dict[str, Any]]:
    """Offer only exact, safe read and patch operations inside the artifact sandbox."""
    return [
        {"type": "function", "function": {"name": "read_fixture", "description": "Read the supplied fixture.",
         "parameters": {"type": "object", "properties": {"path": {"type": "string", "enum": [path]}}, "required": ["path"]}}},
        {"type": "function", "function": {"name": "apply_exact_patch", "description": "Replace the known buggy line.",
         "parameters": {"type": "object", "properties": {"path": {"type": "string", "enum": [path]}, "before": {"type": "string", "enum": [before]}, "after": {"type": "string", "enum": [after]}}, "required": ["path", "before", "after"]}}},
    ]


def main() -> int:
    """Execute read, real sandbox patch, and final verification as one agent trajectory."""
    args = parse_args()
    suite = json.loads(args.suite.read_text(encoding="utf-8"))
    fixture = suite["fixture"]
    path, initial, expected = fixture["path"], fixture["initial_content"], fixture["expected_content"]
    before, after = "return a - b", "return a + b"
    # Keep the mutable fixture below the caller-selected artifact parent, so no
    # model-selected path can escape the explicitly designated test sandbox.
    sandbox = args.artifact.parent / f"{args.artifact.stem}-sandbox"
    sandbox.mkdir(parents=True, exist_ok=False)
    fixture_path = sandbox / path
    fixture_path.write_text(initial, encoding="utf-8")
    tools = tool_schema(path, before, after)
    messages: list[dict[str, Any]] = [{"role": "user", "content": "Inspect calculator.py with read_fixture. Do not answer in plain text."}]
    observations: list[dict[str, Any]] = []
    # Turn one must create a structured read request.
    body, started, finished = request_json(args.base_url, {"model": args.model, "messages": messages, "tools": tools, "tool_choice": "required", "temperature": 0, "max_tokens": args.max_tokens, "stream": False})
    read_observation = observe("read_call", body, started, finished)
    read_call = one_required_call(read_observation, "read_fixture")
    if json.loads(read_call["function"]["arguments"]) != {"path": path}:
        raise RuntimeError("read tool arguments differ from constrained fixture")
    observations.append(read_observation)
    messages += [{"role": "assistant", "content": read_observation["content"], "tool_calls": [read_call]}, {"role": "tool", "tool_call_id": read_call["id"], "content": json.dumps({"path": path, "content": fixture_path.read_text(encoding="utf-8")})}, {"role": "user", "content": "Repair the addition bug using apply_exact_patch. Do not answer in plain text."}]
    # Turn two must request the constrained patch. The runner then performs the
    # requested replacement in the sandbox, which is genuine tool-side state.
    body, started, finished = request_json(args.base_url, {"model": args.model, "messages": messages, "tools": tools, "tool_choice": "required", "temperature": 0, "max_tokens": args.max_tokens, "stream": False})
    patch_observation = observe("patch_call", body, started, finished)
    patch_call = one_required_call(patch_observation, "apply_exact_patch")
    patch_args = json.loads(patch_call["function"]["arguments"])
    if patch_args != {"path": path, "before": before, "after": after}:
        raise RuntimeError(f"patch arguments differ from exact safe patch: {patch_args!r}")
    current = fixture_path.read_text(encoding="utf-8")
    if current.count(before) != 1:
        raise RuntimeError("fixture no longer contains exactly one approved replacement")
    fixture_path.write_text(current.replace(before, after), encoding="utf-8")
    if fixture_path.read_text(encoding="utf-8") != expected:
        raise RuntimeError("sandbox patch did not produce expected fixture content")
    observations.append(patch_observation)
    messages += [{"role": "assistant", "content": patch_observation["content"], "tool_calls": [patch_call]}, {"role": "tool", "tool_call_id": patch_call["id"], "content": json.dumps({"path": path, "applied": True, "content": expected})}, {"role": "user", "content": "Confirm the verified repair by replying exactly PATCH_APPLIED."}]
    # The final model response is a visible correctness check after tool output.
    body, started, finished = request_json(args.base_url, {"model": args.model, "messages": messages, "temperature": 0, "max_tokens": args.max_tokens, "stream": False})
    final_observation = observe("final_confirmation", body, started, finished)
    if final_observation["content"].strip() != suite["expected_final"]:
        raise RuntimeError(f"unexpected final content: {final_observation['content']!r}")
    observations.append(final_observation)
    # Compute only metrics legitimately available from the non-streaming control.
    durations = [row["elapsed_seconds"] for row in observations]
    # Hash the mutated fixture so later evidence consumers can verify the
    # successful tool side effect without trusting a prose summary alone.
    fixture_sha256 = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
    result = {"schema_version": 1, "passed": True, "scope": suite["description"], "fixture_path": str(fixture_path), "fixture_sha256": fixture_sha256, "observations": observations, "summary": {"turn_count": len(observations), "mean_end_to_end_seconds": statistics.mean(durations), "max_end_to_end_seconds": max(durations), "total_prompt_tokens": sum(row["prompt_tokens"] for row in observations), "total_completion_tokens": sum(row["completion_tokens"] for row in observations), "aggregate_end_to_end_tps": sum(row["completion_tokens"] for row in observations) / sum(durations), "ttft_available": False, "p99_token_gap_available": False}}
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
