"""Mixed Q4_K/Q5_K GGUF routed-expert execution for Qwen3.6 MoE checkpoints.

The GGUF model recipe names this combination ``Q4_K_M``, but its tensor table
stores the gate and up expert projections as Q4_K and the down projection as
Q5_K.  The borrowed HIP GGML kernels dispatch one quant type per matrix, so
this module intentionally launches one packed Q4_K MoE GEMV followed by one
packed Q5_K MoE GEMV.  Neither weight is dequantized to a persistent bf16 copy.
"""

from __future__ import annotations

import os

import torch

from freetoken.layers.activation import silu_and_mul
from freetoken.models.gguf.dequant import GGML_Q4_K, GGML_Q5_K


# This switch is deliberately opt-in.  The packed vector kernels are the
# production reference until the grouped path proves exact output quality and
# repeatable API performance on the target ROCm system.  A value of zero, the
# default, disables the experimental dispatch entirely.
_GROUPED_PREFILL_MIN_TOKENS_ENV = "FREETOKEN_Q4_GROUPED_PREFILL_MIN_TOKENS"
_GROUPED_PREFILL_MODE_ENV = "FREETOKEN_Q4_GROUPED_PREFILL_MODE"


def _grouped_prefill_min_tokens() -> int:
    """Return the opt-in prompt-token threshold for grouped Q4/Q5 MoE work.

    The grouped kernel amortizes route sorting and matrix-style launches only
    across a sufficiently long prompt.  Decode has one token and therefore
    cannot select this route.  Parsing occurs per call so an isolated benchmark
    can change the process environment before constructing a model, while a
    malformed setting fails loudly rather than silently changing inference.
    """
    raw_value = os.environ.get(_GROUPED_PREFILL_MIN_TOKENS_ENV, "0").strip()
    try:
        minimum_tokens = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            f"{_GROUPED_PREFILL_MIN_TOKENS_ENV} must be a non-negative integer, "
            f"got {raw_value!r}"
        ) from exc
    if minimum_tokens < 0:
        raise RuntimeError(
            f"{_GROUPED_PREFILL_MIN_TOKENS_ENV} must be a non-negative integer, "
            f"got {minimum_tokens}"
        )
    return minimum_tokens


def _grouped_prefill_mode() -> str:
    """Return the explicitly selected grouped projection subset.

    The full grouped path changes both quantized projections at once.  Keeping
    gate/up-only and down-only modes available for isolated component screens
    lets the campaign locate numerical divergence before exposing a candidate
    to an API quality gate.  The production default stays ``both`` because the
    surrounding minimum-token switch remains disabled by default.
    """

    mode = os.environ.get(_GROUPED_PREFILL_MODE_ENV, "both").strip().lower()
    if mode not in {"both", "gate_up", "down"}:
        raise RuntimeError(
            f"{_GROUPED_PREFILL_MODE_ENV} must be one of both, gate_up, or down, got {mode!r}"
        )
    return mode


def _grouped_moe_a8(
    activations: torch.Tensor,
    packed_experts: torch.Tensor,
    route_ids: torch.Tensor,
    quant_type: int,
    output_width: int,
    routes_per_token: int,
) -> torch.Tensor:
    """Run one packed GGUF grouped MoE projection without changing route order.

    ``ggml_moe_a8`` consumes expert-grouped work for efficient matrix-style
    prefill, whereas the caller owns activations in original token order.  The
    route-alignment helper creates a padded worklist whose entries are flattened
    original route indices.  The native kernel uses those indices when writing
    its result, so the returned tensor remains ordered as
    ``[token * routes_per_token + route, output_width]``.  This is the same
    layout produced by ``ggml_moe_a8_vec`` and is therefore safe to feed into
    Qwen's unchanged SwiGLU and router-weight reduction once equivalence is
    established by the benchmark gate.
    """
    from freetoken.kernel.gguf import ggml_moe_a8, ggml_moe_get_block_size
    from freetoken.kernel.moe_impl import moe_align_block_size_triton

    if route_ids.dtype != torch.int32 or not route_ids.is_contiguous():
        raise ValueError("grouped GGUF MoE requires contiguous int32 route ids")
    if packed_experts.ndim != 3:
        raise ValueError("grouped GGUF MoE requires [experts, rows, packed-bytes] weights")

    block_size = int(ggml_moe_get_block_size(int(quant_type)))
    if block_size <= 0:
        raise RuntimeError(f"GGUF MoE has no grouped block size for quant type {quant_type}")
    sorted_token_ids, expert_ids, num_tokens_post_padded = moe_align_block_size_triton(
        route_ids,
        block_size,
        int(packed_experts.shape[0]),
    )
    return ggml_moe_a8(
        activations,
        packed_experts,
        sorted_token_ids,
        expert_ids,
        num_tokens_post_padded,
        int(quant_type),
        int(output_width),
        int(routes_per_token),
        int(activations.shape[0]),
    )


def fused_experts_gguf_q4_k_q5_k(
    hidden_states: torch.Tensor,
    gate_up_q4_k: torch.Tensor,
    down_q5_k: torch.Tensor,
    topk_weights: torch.Tensor,
    topk_ids: torch.Tensor,
    activation: str,
) -> torch.Tensor:
    """Run packed Q4_K gate/up then packed Q5_K down over routed experts.

    ``topk_ids`` already name the materialized GGUF expert-cache slots.  Qwen
    uses SwiGLU, so only ``silu`` is accepted here.  Explicit validation prevents
    a future model family from silently receiving Qwen's activation semantics.
    """
    if activation != "silu":
        raise ValueError(
            "Qwen mixed GGUF experts require the checkpoint's silu SwiGLU activation, "
            f"got {activation!r}"
        )
    tokens = hidden_states.shape[0]
    top_k = topk_ids.shape[1]
    fused_width = gate_up_q4_k.shape[1]
    hidden_size = down_q5_k.shape[1]
    grouped_minimum = _grouped_prefill_min_tokens()
    # A decode step has exactly one activation row.  Keep it on the established
    # vector kernel even if an operator intentionally sets a threshold of one:
    # the grouped route is a prefill-only hypothesis, not a decode experiment.
    use_grouped_prefill = grouped_minimum > 0 and tokens > 1 and tokens >= grouped_minimum
    grouped_mode = _grouped_prefill_mode() if use_grouped_prefill else "both"
    if use_grouped_prefill and grouped_mode in {"both", "gate_up"}:
        # Gate/up routes retain Qwen's original top-k layout.  The grouped
        # helper performs sorting internally but writes results back to that
        # original flattened route position.
        gate_up = _grouped_moe_a8(
            hidden_states,
            gate_up_q4_k,
            topk_ids,
            int(GGML_Q4_K),
            fused_width,
            top_k,
        )
    else:
        from freetoken.kernel.gguf import ggml_moe_a8_vec

        gate_up = ggml_moe_a8_vec(
            hidden_states, gate_up_q4_k, topk_ids, top_k, int(GGML_Q4_K), fused_width, tokens
        )
    intermediate = silu_and_mul(gate_up)
    if use_grouped_prefill and grouped_mode in {"both", "down"}:
        # Each gate/up route becomes one independent down projection.  Reshape
        # the expert ids to one route per activation while keeping flattened
        # token-major ordering, which is exactly the output order required for
        # the following router-weighted reduction.
        down_route_ids = topk_ids.reshape(tokens * top_k, 1).contiguous()
        output = _grouped_moe_a8(
            intermediate,
            down_q5_k,
            down_route_ids,
            int(GGML_Q5_K),
            hidden_size,
            1,
        )
    else:
        from freetoken.kernel.gguf import ggml_moe_a8_vec

        output = ggml_moe_a8_vec(
            intermediate, down_q5_k, topk_ids, 1, int(GGML_Q5_K), hidden_size, tokens * top_k
        )
    output = output.reshape(tokens, top_k, hidden_size)
    return (output * topk_weights.reshape(tokens, top_k, 1).to(output.dtype)).sum(dim=1)


__all__ = ["fused_experts_gguf_q4_k_q5_k"]
