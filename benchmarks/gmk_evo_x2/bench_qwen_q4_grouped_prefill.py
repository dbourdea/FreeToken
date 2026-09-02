#!/usr/bin/env python3
"""Compare real Qwen Q4_K_M long-prefill MoE vector and grouped HIP kernels.

The benchmark materializes the actual first Qwen routed-expert layer through the
same two-slot ``OffloadMoeCache`` used by serving, then runs the production
Q4_K/Q5_K fused expert function on a deterministic long-prompt-shaped activation
batch.  ``vector`` preserves the accepted production dispatch.  ``grouped``
enables only the experimental route-sort plus matrix-style dispatch.  The gate
saves the reference output, checks numerical equivalence, and records warmup
and device-time samples.  It is a real-weight component screen, not API TPS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
from pathlib import Path

import torch

from freetoken.distributed import set_tp_info, try_get_tp_info
from freetoken.models.qwen3_5_moe.config import parse_gguf_config
from freetoken.models.qwen3_5_moe.gguf import load_q4_k_q5_k_expert_sources
from freetoken.moe.fused_q4_k_q5_k import fused_experts_gguf_q4_k_q5_k
from freetoken.moe.offload_cache import OffloadMoeCache
from freetoken.utils import cached_load_hf_config


_GROUPED_PREFILL_MIN_TOKENS_ENV = "FREETOKEN_Q4_GROUPED_PREFILL_MIN_TOKENS"
_GROUPED_PREFILL_MODE_ENV = "FREETOKEN_Q4_GROUPED_PREFILL_MODE"
_MOE_K_TWO_ROWS_ENV = "FREETOKEN_GGUF_MOE_K_TWO_ROWS"
_MOE_K_THREE_ROWS_ENV = "FREETOKEN_GGUF_MOE_K_THREE_ROWS"
_MOE_K_FOUR_ROWS_ENV = "FREETOKEN_GGUF_MOE_K_FOUR_ROWS"
_Q4_K_FOUR_ROWS_ENV = "FREETOKEN_GGUF_Q4_K_FOUR_ROWS"
_Q5_K_FOUR_ROWS_ENV = "FREETOKEN_GGUF_Q5_K_FOUR_ROWS"
_MOE_K_TWO_ROWS_MIN_BLOCKS_ENV = "FREETOKEN_GGUF_MOE_K_TWO_ROWS_MIN_BLOCKS"
_Q4_K_TWO_ROWS_MIN_BLOCKS_ENV = "FREETOKEN_GGUF_Q4_K_TWO_ROWS_MIN_BLOCKS"
_Q5_K_TWO_ROWS_MIN_BLOCKS_ENV = "FREETOKEN_GGUF_Q5_K_TWO_ROWS_MIN_BLOCKS"


def parse_args() -> argparse.Namespace:
    """Parse immutable model/evidence locations and bounded timing parameters."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--mode", choices=("vector", "grouped"), required=True)
    parser.add_argument(
        "--grouped-mode",
        choices=("both", "gate_up", "down"),
        default="both",
        help="When --mode grouped, select the grouped Q4 gate/up, Q5 down, or both projections.",
    )
    parser.add_argument(
        "--vector-two-rows",
        action="store_true",
        help=(
            "Opt into the HIP Q4_K/Q5_K two-output-row vector candidate. "
            "This is valid only with --mode vector and exists solely for an "
            "isolated real-weight parity and device-time gate."
        ),
    )
    parser.add_argument(
        "--vector-three-rows",
        action="store_true",
        help=(
            "Opt into the HIP Q4_K/Q5_K three-output-row vector candidate. "
            "This is an isolated exact-output component experiment and is "
            "never selected by the normal serving configuration."
        ),
    )
    parser.add_argument(
        "--vector-four-rows",
        action="store_true",
        help=(
            "Opt into the HIP Q4_K/Q5_K four-output-row vector candidate. "
            "It is an isolated exact-output component experiment and is "
            "never selected by the normal serving configuration."
        ),
    )
    parser.add_argument(
        "--vector-four-rows-q4-only",
        action="store_true",
        help=(
            "Apply the four-output-row HIP candidate only to Q4_K while Q5_K "
            "uses the generic vector kernel. This is an isolated exact-output "
            "component screen and is never a normal serving default."
        ),
    )
    parser.add_argument(
        "--two-rows-min-blocks",
        choices=("1", "2"),
        default="1",
        help=(
            "Compiler residency target for --vector-two-rows. Two is an "
            "isolated occupancy candidate; one remains the qualified default."
        ),
    )
    parser.add_argument(
        "--q4-two-rows-min-blocks", choices=("1", "2"),
        help="Optional Q4_K-specific residency target; defaults to --two-rows-min-blocks.",
    )
    parser.add_argument(
        "--q5-two-rows-min-blocks", choices=("1", "2"),
        help="Optional Q5_K-specific residency target; defaults to --two-rows-min-blocks.",
    )
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--tokens", type=int, default=1024)
    parser.add_argument("--warmup", type=int, default=8)
    parser.add_argument("--repetitions", type=int, default=20)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--save-output", type=Path)
    parser.add_argument("--reference-output", type=Path)
    parser.add_argument("--rtol", type=float, default=0.001)
    parser.add_argument("--atol", type=float, default=0.01)
    args = parser.parse_args()
    if not args.model.is_file():
        parser.error("model must be an existing GGUF file")
    if args.tokens <= 1 or args.warmup < 1 or args.repetitions < 1:
        parser.error("tokens must exceed one and warmup/repetitions must be positive")
    if args.json.exists() or (args.save_output and args.save_output.exists()):
        parser.error("refusing to overwrite an existing component artifact")
    if args.reference_output and not args.reference_output.is_file():
        parser.error("reference output is missing")
    if args.rtol < 0 or args.atol < 0 or not torch.cuda.is_available():
        parser.error("tolerances must be non-negative and the native ROCm GPU must be available")
    if (args.vector_two_rows or args.vector_three_rows or args.vector_four_rows or args.vector_four_rows_q4_only) and args.mode != "vector":
        parser.error("row-sharing vector options are valid only with --mode vector")
    if sum((args.vector_two_rows, args.vector_three_rows, args.vector_four_rows, args.vector_four_rows_q4_only)) > 1:
        parser.error("select at most one row-sharing vector candidate")
    if (
        args.two_rows_min_blocks != "1"
        or args.q4_two_rows_min_blocks not in (None, "1")
        or args.q5_two_rows_min_blocks not in (None, "1")
    ) and not (args.vector_two_rows or args.vector_three_rows or args.vector_four_rows or args.vector_four_rows_q4_only):
        parser.error("--two-rows-min-blocks=2 requires a row-sharing vector candidate")
    return args


def digest(tensor: torch.Tensor) -> str:
    """Return a stable hash of exact output storage for artifact comparison."""

    return hashlib.sha256(tensor.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()


def materialize_layer(
    model: Path, layer: int
) -> tuple[torch.Tensor, torch.Tensor, int, int, int, OffloadMoeCache]:
    """Load one real primary Q4/Q5 expert layer into serving-equivalent GPU banks.

    The cache call intentionally runs outside the timed interval.  This separates
    streamed-bank transfer from the hypothesis under test: vector versus grouped
    packed-expert math after the full layer is already resident on the device.
    Returned views remain valid for this short-lived benchmark process.
    """

    if try_get_tp_info() is None:
        set_tp_info(rank=0, size=1)
    config = parse_gguf_config(cached_load_hf_config(str(model)))
    if not 0 <= layer < config.num_layers:
        raise ValueError(f"layer {layer} outside [0, {config.num_layers})")
    sources = load_q4_k_q5_k_expert_sources(str(model), config)
    cache = OffloadMoeCache(
        num_layers=config.num_layers,
        num_experts=config.num_experts,
        cache_size=2 * config.num_experts,
        device=torch.device("cuda", torch.cuda.current_device()),
        prefill_overlap=True,
        quant_format="q4_k_q5_k",
    )
    cache.set_bank_sources(sources.primary)
    cache.begin_prefill()
    cache.prefetch_prefill_layer(layer)
    gate_up, down = cache.wait_prefill_layer(layer)
    torch.cuda.synchronize(cache.device)
    # Keep cache alive by attaching it to the returned view objects.  PyTorch
    # tensors permit Python attributes only indirectly, so return the cache as
    # a live local captured by the caller through this tuple's final object.
    return (
        gate_up,
        down,
        int(config.hidden_size),
        int(config.num_experts),
        int(config.num_experts_per_tok),
        cache,
    )


def main() -> int:
    """Run component timing, enforce output parity, and write durable evidence."""

    args = parse_args()
    grouped_threshold = args.tokens if args.mode == "grouped" else 0
    os.environ[_GROUPED_PREFILL_MIN_TOKENS_ENV] = str(grouped_threshold)
    os.environ[_GROUPED_PREFILL_MODE_ENV] = args.grouped_mode
    # The environment value is consumed by the native HIP wrapper at launch
    # time, keeping this candidate unavailable to normal server processes.
    os.environ[_MOE_K_TWO_ROWS_ENV] = "1" if args.vector_two_rows else "0"
    os.environ[_MOE_K_THREE_ROWS_ENV] = "1" if args.vector_three_rows else "0"
    os.environ[_MOE_K_FOUR_ROWS_ENV] = "1" if args.vector_four_rows else "0"
    # Set both format selectors explicitly so the component process never
    # inherits a stale parent value. The all-format candidate enables both;
    # the Q4-only candidate enables only the profiled Q4_K projection.
    os.environ[_Q4_K_FOUR_ROWS_ENV] = "1" if (args.vector_four_rows or args.vector_four_rows_q4_only) else "0"
    os.environ[_Q5_K_FOUR_ROWS_ENV] = "1" if args.vector_four_rows else "0"
    os.environ[_MOE_K_TWO_ROWS_MIN_BLOCKS_ENV] = args.two_rows_min_blocks
    os.environ[_Q4_K_TWO_ROWS_MIN_BLOCKS_ENV] = (
        args.q4_two_rows_min_blocks or args.two_rows_min_blocks
    )
    os.environ[_Q5_K_TWO_ROWS_MIN_BLOCKS_ENV] = (
        args.q5_two_rows_min_blocks or args.two_rows_min_blocks
    )
    gate_up, down, hidden_size, num_experts, top_k, cache = materialize_layer(args.model, args.layer)
    device = gate_up.device
    generator = torch.Generator(device=device)
    generator.manual_seed(20260902)
    activations = torch.randn(
        (args.tokens, hidden_size), dtype=torch.bfloat16, device=device, generator=generator
    )
    # Use every actual expert across the batch.  This creates a deterministic
    # long-prefill worklist without substituting synthetic weights or a reduced
    # expert set, while retaining the model's real top-k cardinality.
    flat_routes = torch.arange(args.tokens * top_k, device=device, dtype=torch.int32)
    topk_ids = (flat_routes.remainder(num_experts)).reshape(args.tokens, top_k).contiguous()
    topk_weights = torch.full(
        (args.tokens, top_k), 1.0 / top_k, dtype=torch.float32, device=device
    )

    def kernel() -> torch.Tensor:
        """Execute precisely the production fused Q4_K/Q5_K expert function."""

        return fused_experts_gguf_q4_k_q5_k(
            activations, gate_up, down, topk_weights, topk_ids, "silu"
        )

    for _ in range(args.warmup):
        output = kernel()
    torch.cuda.synchronize(device)
    if not torch.isfinite(output).all():
        raise RuntimeError("Q4_K/Q5_K prefill component produced non-finite output")

    samples_ms: list[float] = []
    for _ in range(args.repetitions):
        start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
        start.record()
        output = kernel()
        end.record()
        end.synchronize()
        samples_ms.append(float(start.elapsed_time(end)))
    output_cpu = output.detach().cpu().contiguous()
    parity: dict[str, object] | None = None
    if args.reference_output:
        reference = torch.load(args.reference_output, map_location="cpu", weights_only=True).contiguous()
        torch.testing.assert_close(output_cpu, reference, rtol=args.rtol, atol=args.atol)
        delta = (output_cpu.float() - reference.float()).abs()
        parity = {
            "reference_sha256": digest(reference),
            "rtol": args.rtol,
            "atol": args.atol,
            "maximum_absolute_difference": float(delta.max().item()),
            "mean_absolute_difference": float(delta.mean().item()),
        }
    if args.save_output:
        args.save_output.parent.mkdir(parents=True, exist_ok=True)
        torch.save(output_cpu, args.save_output)
    result = {
        "schema_version": 1,
        "classification": "real-weight Q4_K/Q5_K MoE component screen, not API TPS",
        "mode": args.mode,
        "model": str(args.model.resolve()),
        "layer": args.layer,
        "tokens": args.tokens,
        "top_k": top_k,
        "num_experts": num_experts,
        "weight_shapes": {"gate_up": list(gate_up.shape), "down": list(down.shape)},
        "warmup": args.warmup,
        "repetitions": args.repetitions,
        "device": torch.cuda.get_device_name(device),
        "hip": torch.version.hip,
        "torch": torch.__version__,
        "grouped_prefill_min_tokens": grouped_threshold,
        "grouped_prefill_mode": args.grouped_mode if args.mode == "grouped" else "vector",
        "moe_k_two_rows": args.vector_two_rows,
        "moe_k_three_rows": args.vector_three_rows,
        "moe_k_four_rows": args.vector_four_rows,
        "q4_k_four_rows": args.vector_four_rows_q4_only or args.vector_four_rows,
        "q5_k_four_rows": args.vector_four_rows,
        "moe_k_two_rows_min_blocks": int(args.two_rows_min_blocks),
        "q4_k_two_rows_min_blocks": int(args.q4_two_rows_min_blocks or args.two_rows_min_blocks),
        "q5_k_two_rows_min_blocks": int(args.q5_two_rows_min_blocks or args.two_rows_min_blocks),
        "samples_ms": samples_ms,
        "median_device_ms": statistics.median(samples_ms),
        "output_sha256": digest(output_cpu),
        "parity": parity,
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Keep the cache alive through all output copies and result serialization.
    del cache
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
