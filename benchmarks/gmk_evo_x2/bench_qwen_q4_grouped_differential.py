#!/usr/bin/env python3
"""Locate the first numerical divergence in Qwen Q4 grouped MoE prefill.

The existing grouped Q4_K and Q5_K matrix path has materially higher component
throughput than the qualified vector path, but it changes deterministic model
output.  This GPU component harness runs the two paths against the same actual
Qwen Q4_K_M packed expert layer, deterministic BF16 activations, and fixed
top-k routing.  It separates four values: Q4 gate/up output, SwiGLU output,
Q5 down output fed by the same vector intermediate, and the complete grouped
result.  The resulting evidence identifies the first projection that differs
without treating a component time as an API TPS result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch

from freetoken.distributed import set_tp_info, try_get_tp_info
from freetoken.kernel.gguf import ggml_moe_a8_vec
from freetoken.layers.activation import silu_and_mul
from freetoken.models.gguf.dequant import GGML_Q4_K, GGML_Q5_K
from freetoken.models.qwen3_5_moe.config import parse_gguf_config
from freetoken.models.qwen3_5_moe.gguf import load_q4_k_q5_k_expert_sources
from freetoken.moe.fused_q4_k_q5_k import _grouped_moe_a8
from freetoken.moe.offload_cache import OffloadMoeCache
from freetoken.utils import cached_load_hf_config


def _args() -> argparse.Namespace:
    """Parse immutable inputs and reject unsafe artifact reuse."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path, help="qualified Qwen Q4_K_M GGUF")
    parser.add_argument("--json", required=True, type=Path, help="new JSON result artifact")
    parser.add_argument("--layer", type=int, default=0, help="routed expert layer to materialize")
    parser.add_argument("--tokens", type=int, default=1024, help="deterministic prefill-shaped activation rows")
    parser.add_argument(
        "--route-pattern",
        choices=("cyclic", "single-expert"),
        default="cyclic",
        help="deterministic expert routing used to distinguish route handling from dot-product arithmetic",
    )
    args = parser.parse_args()
    if not args.model.is_file():
        parser.error("--model must be an existing GGUF file")
    if args.json.exists():
        parser.error("refusing to overwrite an existing evidence artifact")
    if args.tokens <= 1:
        parser.error("--tokens must exceed one because this is a grouped-prefill differential")
    if not torch.cuda.is_available():
        parser.error("a native ROCm/HIP PyTorch GPU is required")
    return args


def _digest(value: torch.Tensor) -> str:
    """Return a SHA-256 digest of exact contiguous CPU storage bytes."""

    return hashlib.sha256(value.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()


def _difference(reference: torch.Tensor, candidate: torch.Tensor) -> dict[str, object]:
    """Describe exact-storage and floating-point differences for one tensor pair."""

    expected = reference.detach().cpu().contiguous()
    observed = candidate.detach().cpu().contiguous()
    delta = (expected.float() - observed.float()).abs()
    return {
        "reference_sha256": _digest(expected),
        "candidate_sha256": _digest(observed),
        "storage_equal": bool(torch.equal(expected, observed)),
        "maximum_absolute_difference": float(delta.max().item()),
        "mean_absolute_difference": float(delta.mean().item()),
    }


def _materialize_layer(model: Path, layer: int) -> tuple[torch.Tensor, torch.Tensor, int, int, int, OffloadMoeCache]:
    """Return one actual Qwen expert layer in the same double-buffer cache used by serving."""

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
    return gate_up, down, int(config.hidden_size), int(config.num_experts), int(config.num_experts_per_tok), cache


def _topk_ids(tokens: int, top_k: int, expert_count: int, pattern: str, device: torch.device) -> torch.Tensor:
    """Build route ids with either mixed-expert coverage or one repeated expert.

    The cyclic pattern exercises the normal grouped sort and scatter behavior.
    The single-expert pattern leaves the same number of tokens and top-k routes
    intact while removing cross-expert ordering as a possible source of error.
    """

    if pattern == "cyclic":
        routes = torch.arange(tokens * top_k, dtype=torch.int32, device=device)
        return routes.remainder(expert_count).reshape(tokens, top_k).contiguous()
    if pattern == "single-expert":
        return torch.zeros((tokens, top_k), dtype=torch.int32, device=device)
    raise ValueError(f"unsupported route pattern: {pattern}")


def main() -> int:
    """Execute vector and grouped projections, compare them, and write raw evidence."""

    args = _args()
    gate_up_weights, down_weights, hidden_size, expert_count, top_k, cache = _materialize_layer(args.model, args.layer)
    device = gate_up_weights.device
    generator = torch.Generator(device=device).manual_seed(20260902)
    hidden_states = torch.randn((args.tokens, hidden_size), dtype=torch.bfloat16, device=device, generator=generator)
    topk_ids = _topk_ids(args.tokens, top_k, expert_count, args.route_pattern, device)
    topk_weights = torch.full((args.tokens, top_k), 1.0 / top_k, dtype=torch.float32, device=device)

    # The reference is the exact qualified vector route used in normal serving.
    vector_gate_up = ggml_moe_a8_vec(hidden_states, gate_up_weights, topk_ids, top_k, int(GGML_Q4_K), gate_up_weights.shape[1], args.tokens)
    vector_intermediate = silu_and_mul(vector_gate_up)
    vector_down = ggml_moe_a8_vec(vector_intermediate, down_weights, topk_ids, 1, int(GGML_Q5_K), down_weights.shape[1], args.tokens * top_k)
    vector_final = (vector_down.reshape(args.tokens, top_k, hidden_size) * topk_weights.reshape(args.tokens, top_k, 1).to(vector_down.dtype)).sum(dim=1)

    # First isolate Q4 gate/up. The helper owns sorting and scatter but returns
    # the same flattened route order expected by the unchanged SwiGLU operator.
    grouped_gate_up = _grouped_moe_a8(hidden_states, gate_up_weights, topk_ids, int(GGML_Q4_K), gate_up_weights.shape[1], top_k)
    grouped_intermediate = silu_and_mul(grouped_gate_up)

    # Feed the vector intermediate into grouped Q5 down to isolate the down
    # projection from any upstream Q4 gate/up rounding difference.
    down_route_ids = topk_ids.reshape(args.tokens * top_k, 1).contiguous()
    grouped_down_from_vector = _grouped_moe_a8(vector_intermediate, down_weights, down_route_ids, int(GGML_Q5_K), down_weights.shape[1], 1)
    grouped_down_from_grouped = _grouped_moe_a8(grouped_intermediate, down_weights, down_route_ids, int(GGML_Q5_K), down_weights.shape[1], 1)
    grouped_final = (grouped_down_from_grouped.reshape(args.tokens, top_k, hidden_size) * topk_weights.reshape(args.tokens, top_k, 1).to(grouped_down_from_grouped.dtype)).sum(dim=1)
    torch.cuda.synchronize(device)

    result = {
        "schema_version": 2,
        "classification": "real-weight grouped-versus-vector numerical differential, not API TPS",
        "model": str(args.model.resolve()),
        "layer": args.layer,
        "tokens": args.tokens,
        "route_pattern": args.route_pattern,
        "top_k": top_k,
        "num_experts": expert_count,
        "weight_shapes": {"gate_up": list(gate_up_weights.shape), "down": list(down_weights.shape)},
        "device": torch.cuda.get_device_name(device),
        "hip": torch.version.hip,
        "torch": torch.__version__,
        "gate_up": _difference(vector_gate_up, grouped_gate_up),
        "intermediate": _difference(vector_intermediate, grouped_intermediate),
        "down_same_vector_intermediate": _difference(vector_down, grouped_down_from_vector),
        "down_with_grouped_intermediate": _difference(vector_down, grouped_down_from_grouped),
        "final": _difference(vector_final, grouped_final),
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    del cache
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
