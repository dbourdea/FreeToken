"""Measure one real Qwen Q4_K_M full-layer prefill transfer with exact byte parity.

The benchmark loads the actual pinned primary expert banks from the checked Q4_K_M
GGUF, creates the same two-buffer ``OffloadMoeCache`` used by serving, and times
only the first full expert-layer prefetch.  ``legacy`` uses the established
per-bank ``Tensor.copy_`` route.  ``fused`` requires the opt-in mapped-host
multi-bank route, then compares every destination byte against a saved legacy
reference.  It is a component gate, not an API throughput claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

import torch

from freetoken.distributed import set_tp_info, try_get_tp_info
from freetoken.models.qwen3_5_moe.config import parse_gguf_config
from freetoken.models.qwen3_5_moe.gguf import load_q4_k_q5_k_expert_sources
from freetoken.moe.offload_cache import OffloadMoeCache
from freetoken.utils import cached_load_hf_config


def parse_args() -> argparse.Namespace:
    """Parse an explicit model, mode, timing shape, and immutable evidence paths."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="absolute Q4_K_M GGUF path")
    parser.add_argument("--mode", choices=("legacy", "fused"), required=True)
    parser.add_argument("--layer", type=int, default=0, help="MoE layer to transfer")
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--repetitions", type=int, default=30)
    parser.add_argument("--reference", type=Path, help="legacy byte-reference torch file")
    parser.add_argument("--save-reference", type=Path, help="destination for legacy byte reference")
    parser.add_argument("--json", type=Path, required=True, help="result JSON path")
    return parser.parse_args()


def copy_once(cache: OffloadMoeCache, layer_id: int) -> tuple[torch.Tensor, ...]:
    """Run one isolated prefill transfer and wait until every copied byte is readable."""

    cache.begin_prefill()
    cache.prefetch_prefill_layer(layer_id)
    views = cache.wait_prefill_layer(layer_id)
    # The current stream's synchronization converts the asynchronous copy-stream
    # dependency into a timing boundary without changing the production copy path.
    torch.cuda.synchronize(cache.device)
    result = tuple(view.detach().cpu().clone() for view in views)
    cache.release_prefill_layer(layer_id)
    torch.cuda.synchronize(cache.device)
    return result


def digest(tensors: tuple[torch.Tensor, ...]) -> str:
    """Return a stable compact digest of the exact destination bytes for evidence."""

    checksum = hashlib.sha256()
    for tensor in tensors:
        checksum.update(tensor.numpy().tobytes())
    return checksum.hexdigest()


def main() -> int:
    """Load real banks, time the selected path, and enforce requested parity evidence."""

    args = parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("this component gate requires the native ROCm GPU")
    if args.warmup < 0 or args.repetitions < 1:
        raise ValueError("warmup must be non-negative and repetitions must be positive")

    # This standalone component process does not create the engine's distributed
    # bootstrap.  The GGUF bank loader still validates the same TP=1 contract as
    # serving, so establish that explicit one-device context before loading it.
    if try_get_tp_info() is None:
        set_tp_info(rank=0, size=1)

    device = torch.device("cuda", torch.cuda.current_device())
    config = parse_gguf_config(cached_load_hf_config(args.model))
    if not 0 <= args.layer < config.num_layers:
        raise ValueError(f"layer {args.layer} outside [0, {config.num_layers})")
    sources = load_q4_k_q5_k_expert_sources(args.model, config)
    cache = OffloadMoeCache(
        num_layers=config.num_layers,
        num_experts=config.num_experts,
        cache_size=2 * config.num_experts,
        device=device,
        prefill_overlap=True,
        quant_format="q4_k_q5_k",
    )
    cache.set_bank_sources(sources.primary)
    if args.mode == "fused" and not cache._prefill_fused_mapped_copy_active:
        raise RuntimeError(
            "fused mode was requested but the mapped-host copy plan is unavailable; "
            "set FREETOKEN_PREFILL_FUSED_MAPPED_COPY=1 with a valid fused copy plan"
        )
    if args.mode == "legacy" and cache._prefill_fused_mapped_copy_active:
        raise RuntimeError("legacy mode requires FREETOKEN_PREFILL_FUSED_MAPPED_COPY=0")

    # Warm the exact extension and transfer path before timing, then keep all
    # repeated operations on the same real source layer and cache geometry.
    for _ in range(args.warmup):
        copy_once(cache, args.layer)
    samples_ms: list[float] = []
    output: tuple[torch.Tensor, ...] | None = None
    for _ in range(args.repetitions):
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        output = copy_once(cache, args.layer)
        end.record()
        end.synchronize()
        samples_ms.append(float(start.elapsed_time(end)))
    assert output is not None

    parity = None
    if args.reference is not None:
        reference = tuple(torch.load(args.reference, map_location="cpu", weights_only=True))
        if len(reference) != len(output):
            raise AssertionError(f"bank count differs: reference={len(reference)} output={len(output)}")
        parity = all(torch.equal(expected, observed) for expected, observed in zip(reference, output))
        if not parity:
            raise AssertionError("fused prefill copy changed one or more destination bytes")
    if args.save_reference is not None:
        # The controller owns the unique artifact directory itself, while this
        # benchmark owns only the named file within it.
        args.save_reference.parent.mkdir(parents=True, exist_ok=True)
        torch.save(output, args.save_reference)

    total_bytes = sum(tensor.nbytes for tensor in output)
    median_ms = statistics.median(samples_ms)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(
            {
                "mode": args.mode,
                "model": args.model,
                "layer": args.layer,
                "num_experts": config.num_experts,
                "bank_shapes": [list(tensor.shape) for tensor in output],
                "bytes_per_full_layer": total_bytes,
                "samples_ms": samples_ms,
                "median_ms": median_ms,
                "bandwidth_gbps": total_bytes / (median_ms * 1e6),
                "sha256": digest(output),
                "exact_byte_parity": parity,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"median_ms": median_ms, "bytes": total_bytes, "parity": parity}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
