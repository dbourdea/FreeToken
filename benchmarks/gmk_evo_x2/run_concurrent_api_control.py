#!/usr/bin/env python3
"""Measure simultaneous GMKtec EVO-X2 streamed requests without changing server state.

The existing scheduler baseline measures one warm request at a time.  This
control releases a fixed number of requests together, preserves each raw
response and timing stream, and reports individual latency, aggregate decode
throughput, and aggregate prompt-prefill throughput. Prompt-prefill TPS uses
the API usage prompt-token count and the elapsed time until every request has
received its first visible output token. It is a local GMKtec EVO-X2 control,
not a reproduction of an upstream agent workload. The program never starts,
stops, or reconfigures a server.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


DEFAULT_PROMPT = (
    "The scheduler manages incoming inference requests by prioritizing, batching, "
    "and assigning them to available compute resources to optimize throughput and latency. "
) * 48


@dataclass(frozen=True)
class StreamObservation:
    """One visible SSE fragment and the monotonic time at which it arrived."""

    offset_seconds: float
    content: str


def nearest_rank_percentile(values: list[float], percentile: float) -> float | None:
    """Return an observed tail value without interpolating an unmeasured result."""

    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, int(len(ordered) * percentile + 0.999999999) - 1)]


def numeric_summary(values: list[float]) -> dict[str, float | None]:
    """Report central and tail values while retaining the measured maximum."""

    if not values:
        return {key: None for key in ("mean", "median", "minimum", "maximum", "stdev", "p50", "p95", "p99")}
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "minimum": min(values),
        "maximum": max(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else None,
        "p50": nearest_rank_percentile(values, 0.50),
        "p95": nearest_rank_percentile(values, 0.95),
        "p99": nearest_rank_percentile(values, 0.99),
    }


def load_tokenizer(path: Path) -> Any:
    """Load the checkpoint tokenizer locally so generated-token counts are real."""

    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)


def iter_sse_events(response: Any, started_at: float) -> Iterable[tuple[float, str]]:
    """Yield every server-sent data payload with its receive timestamp."""

    for raw_line in response:
        offset = time.perf_counter() - started_at
        line = raw_line.decode("utf-8", errors="strict").rstrip("\r\n")
        if line.startswith("data:"):
            yield offset, line[5:].lstrip()


def stream_completion(args: argparse.Namespace) -> tuple[list[StreamObservation], str, float, float, list[str], dict[str, Any] | None]:
    """Issue one greedy fixed-length request without relying on remote source files."""

    body = {
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 0.0,
        "top_p": 1.0,
        "top_k": 1,
        "max_tokens": args.max_tokens,
        "reasoning_effort": "none",
        "ignore_eos": True,
    }
    request = urllib.request.Request(
        args.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    started = time.perf_counter()
    observations: list[StreamObservation] = []
    errors: list[str] = []
    usage: dict[str, Any] | None = None
    completed = False
    try:
        with urllib.request.urlopen(request, timeout=args.timeout_seconds) as response:
            for offset, event_data in iter_sse_events(response, started):
                if event_data == "[DONE]":
                    completed = True
                    continue
                try:
                    event = json.loads(event_data)
                except json.JSONDecodeError as error:
                    errors.append(f"invalid JSON SSE event: {error}")
                    continue
                if isinstance(event.get("error"), dict):
                    errors.append(f"server error event: {event['error']}")
                if isinstance(event.get("usage"), dict):
                    usage = event["usage"]
                for choice in event.get("choices", []):
                    delta = choice.get("delta", {})
                    content = delta.get("reasoning_content") or delta.get("content")
                    if content:
                        observations.append(StreamObservation(offset, str(content)))
    except urllib.error.HTTPError as error:
        errors.append(f"HTTP {error.code}: {error.read().decode('utf-8', errors='replace')}")
    except urllib.error.URLError as error:
        errors.append(f"transport failure: {error}")
    finished = time.perf_counter()
    if not completed:
        errors.append("stream ended without [DONE]")
    return observations, "".join(item.content for item in observations), started, finished, errors, usage


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse fixed workload, concurrency, and immutable artifact inputs."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:1919/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--tokenizer", required=True, type=Path)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--expected-host", default="david-Gmktec-x2-2")
    parser.add_argument("--concurrency", required=True, type=int)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument(
        "--sample-variation",
        choices=("none", "prefix_nonce"),
        default="none",
        help="Use a unique early prefix for each request so repeated prompts cannot share a full cache entry.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    args = parser.parse_args(argv)
    if args.concurrency < 1:
        parser.error("--concurrency must be positive")
    if args.rounds < 1:
        parser.error("--rounds must be positive")
    if args.max_tokens < 2:
        parser.error("--max-tokens must be at least two for TPS")
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    return args


def require_expected_host(expected_host: str) -> str:
    """Fail closed to keep concurrency traffic on the declared GMKtec EVO-X2 host."""

    actual_host = socket.gethostname().lower()
    expected_short = expected_host.lower().split(".", 1)[0]
    if actual_host not in {expected_host.lower(), expected_short}:
        raise RuntimeError(f"refusing concurrent control on {actual_host!r}; expected {expected_host!r}")
    return actual_host


def request_args(args: argparse.Namespace, prompt: str) -> argparse.Namespace:
    """Build the compatible greedy throughput request consumed by shared code."""

    return argparse.Namespace(
        base_url=args.base_url,
        model=args.model,
        prompt=prompt,
        max_tokens=args.max_tokens,
        timeout_seconds=args.timeout_seconds,
        reasoning_effort="none",
        mode="throughput",
        expected_text="",
    )


def usage_prompt_tokens(usage: dict[str, Any] | None) -> int | None:
    """Return the server-reported prompt token count only when it is usable.

    The server owns the exact chat-template formatting, so API usage is more
    accurate than tokenizing the raw user message locally. A missing or invalid
    value makes the request unsuitable for a prefill-TPS measurement.
    """

    value = usage.get("prompt_tokens") if isinstance(usage, dict) else None
    return value if isinstance(value, int) and value > 0 else None


def usage_cached_tokens(usage: dict[str, Any] | None) -> int | None:
    """Extract the optional API-reported cache hit count without guessing.

    The cache-neutral mode uses this only as an integrity gate. A missing field
    remains visible in the raw usage record, while a positive value proves that
    the per-request nonce was insufficient for this server's cache semantics.
    """

    details = usage.get("prompt_tokens_details") if isinstance(usage, dict) else None
    value = details.get("cached_tokens") if isinstance(details, dict) else None
    return value if isinstance(value, int) and value >= 0 else None


def run_round(args: argparse.Namespace, tokenizer: Any, round_index: int) -> dict[str, Any]:
    """Release one synchronized request group and retain every request result."""

    barrier = threading.Barrier(args.concurrency)
    suite_started = time.perf_counter()

    def one_request(request_index: int) -> dict[str, Any]:
        """Wait for the group, then record one independent streamed completion."""

        prompt = args.prompt
        if args.sample_variation == "prefix_nonce":
            # This nonce is deliberately before the fixed prompt. A radix cache
            # can still reuse system/template tokens, but it cannot reuse the
            # expensive user-prompt prefix from an earlier client or round.
            prompt = f"Concurrent cold prefix nonce: c{round_index}-r{request_index}\n{args.prompt}"
        workload_args = request_args(args, prompt)
        barrier.wait(timeout=30.0)
        observations, text, started, finished, errors, usage = stream_completion(workload_args)
        generated_tokens = len(tokenizer.encode(text, add_special_tokens=False))
        prompt_tokens = usage_prompt_tokens(usage)
        cached_tokens = usage_cached_tokens(usage)
        ttft = observations[0].offset_seconds if observations else None
        last = observations[-1].offset_seconds if observations else None
        first_output_offset = started - suite_started + ttft if ttft is not None else None
        prefill_tps = prompt_tokens / ttft if prompt_tokens is not None and ttft is not None and ttft > 0 else None
        decode_seconds = last - ttft if ttft is not None and last is not None else None
        decode_tps = (
            (generated_tokens - 1) / decode_seconds
            if generated_tokens > 1 and decode_seconds is not None and decode_seconds > 0
            else None
        )
        gaps = [
            observations[index].offset_seconds - observations[index - 1].offset_seconds
            for index in range(1, len(observations))
        ]
        if not observations:
            errors.append("stream contained no content events")
        if prefill_tps is None:
            errors.append("server did not provide a positive prompt-token count and TTFT for prefill TPS")
        if decode_tps is None:
            errors.append("fewer than two generated tokens or no positive decode interval")
        if args.sample_variation == "prefix_nonce" and cached_tokens not in {0, None}:
            errors.append(f"cache-neutral request reported cached_tokens={cached_tokens}")
        return {
            "request_index": request_index,
            "started_offset_seconds": started - suite_started,
            "finished_offset_seconds": finished - suite_started,
            "wall_seconds": finished - started,
            "ttft_seconds": ttft,
            "first_output_offset_seconds": first_output_offset,
            "prompt_tokens": prompt_tokens,
            "cached_tokens": cached_tokens,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "prefill_tps": prefill_tps,
            "decode_seconds": decode_seconds,
            "decode_tps": decode_tps,
            "generated_tokens": generated_tokens,
            "usage": usage,
            "response_text": text,
            "content_events": [
                {"offset_seconds": item.offset_seconds, "content": item.content}
                for item in observations
            ],
            "token_gap_seconds": gaps,
            "token_gap_summary_seconds": numeric_summary(gaps),
            "errors": errors,
            "status": "passed" if not errors else "failed",
        }

    with ThreadPoolExecutor(max_workers=args.concurrency, thread_name_prefix="gmk_evo_x2-load") as executor:
        requests = list(executor.map(one_request, range(1, args.concurrency + 1)))
    suite_finished = time.perf_counter()
    successful = [request for request in requests if request["status"] == "passed"]
    first_start = min((request["started_offset_seconds"] for request in requests), default=None)
    last_finish = max((request["finished_offset_seconds"] for request in requests), default=None)
    span = last_finish - first_start if first_start is not None and last_finish is not None else None
    aggregate_tokens = sum(request["generated_tokens"] for request in successful)
    first_output_offsets = [request["first_output_offset_seconds"] for request in successful if request["first_output_offset_seconds"] is not None]
    prefill_span = max(first_output_offsets) - first_start if first_output_offsets and first_start is not None else None
    aggregate_prompt_tokens = sum(request["prompt_tokens"] for request in successful if request["prompt_tokens"] is not None)
    return {
        "round_index": round_index,
        "started_epoch_seconds": suite_started,
        "wall_seconds": suite_finished - suite_started,
        "requests": requests,
        "summary": {
            "successful_requests": len(successful),
            "requested_requests": args.concurrency,
            "aggregate_generated_tokens": aggregate_tokens,
            "aggregate_tps": aggregate_tokens / span if span and span > 0 else None,
            "aggregate_prompt_tokens": aggregate_prompt_tokens,
            "prefill_span_seconds": prefill_span,
            "aggregate_prefill_tps": (
                aggregate_prompt_tokens / prefill_span
                if prefill_span is not None and prefill_span > 0 and aggregate_prompt_tokens > 0
                else None
            ),
            "prefill_tps": numeric_summary([request["prefill_tps"] for request in successful if request["prefill_tps"] is not None]),
            "decode_tps": numeric_summary([request["decode_tps"] for request in successful if request["decode_tps"] is not None]),
            "ttft_seconds": numeric_summary([request["ttft_seconds"] for request in successful if request["ttft_seconds"] is not None]),
            "token_gap_seconds": numeric_summary([gap for request in successful for gap in request["token_gap_seconds"]]),
        },
        "status": "passed" if len(successful) == args.concurrency else "failed",
    }


def main(argv: list[str] | None = None) -> int:
    """Write the complete concurrent evidence package and propagate failures."""

    args = parse_args(sys.argv[1:] if argv is None else argv)
    host = require_expected_host(args.expected_host)
    if args.artifact.exists():
        raise FileExistsError(f"refusing to overwrite existing artifact: {args.artifact}")
    tokenizer = load_tokenizer(args.tokenizer)
    rounds = [run_round(args, tokenizer, index) for index in range(1, args.rounds + 1)]
    aggregate_tps = [item["summary"]["aggregate_tps"] for item in rounds if item["summary"]["aggregate_tps"] is not None]
    aggregate_prefill_tps = [
        item["summary"]["aggregate_prefill_tps"]
        for item in rounds
        if item["summary"]["aggregate_prefill_tps"] is not None
    ]
    all_prefill_tps = [
        request["prefill_tps"]
        for item in rounds
        for request in item["requests"]
        if request["prefill_tps"] is not None
    ]
    all_ttft = [request["ttft_seconds"] for item in rounds for request in item["requests"] if request["ttft_seconds"] is not None]
    all_gaps = [gap for item in rounds for request in item["requests"] for gap in request["token_gap_seconds"]]
    artifact = {
        "schema_version": 1,
        "classification": "GMKtec EVO-X2 concurrent API control, not paper replication",
        "host": host,
        "request": {
            "base_url": args.base_url,
            "model": args.model,
            "concurrency": args.concurrency,
            "rounds": args.rounds,
            "max_tokens": args.max_tokens,
            "prompt": args.prompt,
            "sample_variation": args.sample_variation,
            "reasoning_effort": "none",
            "temperature": 0.0,
            "top_p": 1.0,
            "top_k": 1,
            "ignore_eos": True,
        },
        "rounds": rounds,
        "summary": {
            "successful_rounds": sum(item["status"] == "passed" for item in rounds),
            "requested_rounds": args.rounds,
            "aggregate_tps": numeric_summary(aggregate_tps),
            "aggregate_prefill_tps": numeric_summary(aggregate_prefill_tps),
            "prefill_tps": numeric_summary(all_prefill_tps),
            "ttft_seconds": numeric_summary(all_ttft),
            "token_gap_seconds": numeric_summary(all_gaps),
            "p99_ttft_seconds": nearest_rank_percentile(all_ttft, 0.99),
            "p99_token_gap_seconds": nearest_rank_percentile(all_gaps, 0.99),
        },
        "status": "passed" if all(item["status"] == "passed" for item in rounds) else "failed",
    }
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": artifact["status"], "summary": artifact["summary"]}, sort_keys=True))
    return 0 if artifact["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
