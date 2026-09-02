#!/usr/bin/env python3
"""Measure the exact Qwen3.6 Q4_K and Q5_K routed-MoE kernels on GMKtec EVO-X2.

This screening benchmark reads real packed rows from the qualified Qwen3.6
Q4_K_M GGUF instead of manufacturing bytes.  It copies eight actual experts
from one selected MoE layer to the accelerator, uses deterministic routes, and
calls FreeToken's production ``ggml_moe_a8_vec`` binding.  The gate/up call has
the model's Q4_K 512-to-2,048 shape; the down call has its Q5_K
2,048-to-512 shape.  GPU event time is useful for selecting a kernel candidate
but is never a substitute for the quality-gated OpenAI API measurement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch

from freetoken.kernel.gguf import ggml_moe_a8_vec
from freetoken.models.gguf.dequant import GGML_Q4_K, GGML_Q5_K
from freetoken.models.gguf.reader import GgufTensor, iter_gguf_tensors


# The qualified Qwen model has 256 experts and routes eight experts per token.
DEFAULT_EXPERT_COUNT = 256
DEFAULT_TOP_K = 8
DEFAULT_LAYER = 0


def _parse_args() -> argparse.Namespace:
    """Read explicit benchmark controls and refuse implicit model selection."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path, help="qualified Q4_K_M GGUF")
    parser.add_argument("--layer", type=int, default=DEFAULT_LAYER, help="MoE layer to sample")
    parser.add_argument("--warmup", type=int, default=30, help="unmeasured production-kernel calls")
    parser.add_argument("--repetitions", type=int, default=300, help="timed calls per projection")
    parser.add_argument("--json", type=Path, required=True, help="new JSON artifact path")
    parser.add_argument(
        "--save-output",
        type=Path,
        help="new torch artifact path for the three CPU comparison tensors",
    )
    parser.add_argument(
        "--reference-output",
        type=Path,
        help="existing torch artifact whose three outputs must match this run",
    )
    return parser.parse_args()


def _require_inputs(args: argparse.Namespace) -> None:
    """Validate every input before mapping model data or reserving the GPU."""

    if not args.model.is_file():
        raise FileNotFoundError(f"GGUF model is missing: {args.model}")
    if args.layer < 0:
        raise ValueError("--layer must be non-negative")
    if args.warmup <= 0 or args.repetitions <= 0:
        raise ValueError("--warmup and --repetitions must be positive")
    if args.json.exists():
        raise FileExistsError(f"refusing to overwrite artifact: {args.json}")
    if args.save_output is not None and args.save_output.exists():
        raise FileExistsError(f"refusing to overwrite output artifact: {args.save_output}")
    if args.reference_output is not None and not args.reference_output.is_file():
        raise FileNotFoundError(f"reference output is missing: {args.reference_output}")
    if not torch.cuda.is_available():
        raise RuntimeError("this benchmark requires a CUDA or HIP PyTorch device")


def _tensor_map(model: Path) -> dict[str, GgufTensor]:
    """Index GGUF tensor records once while retaining their zero-copy packed views."""

    return {tensor.name: tensor for tensor in iter_gguf_tensors(str(model))}


def _expert_bank(tensor: GgufTensor, device: torch.device) -> torch.Tensor:
    """Copy exactly eight real expert banks to GPU in FreeToken's packed layout.

    The qualified tensors expose torch shape ``[experts, rows, columns]`` and a
    packed CPU view ``[experts * rows, row_bytes]``.  Reshaping is metadata-only;
    selecting the first eight experts bounds device memory while retaining the
    quantization bytes used by the real model.
    """

    experts, rows, _columns = tensor.shape
    if experts != DEFAULT_EXPERT_COUNT:
        raise ValueError(f"expected {DEFAULT_EXPERT_COUNT} experts, got {experts} in {tensor.name}")
    packed = tensor.packed().reshape(experts, rows, -1)
    return packed[:DEFAULT_TOP_K].contiguous().to(device=device, non_blocking=False)


def _event_time_us(kernel, repetitions: int, device: torch.device) -> float:
    """Return synchronized average device time in microseconds for one call."""

    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    torch.cuda.synchronize(device)
    start.record()
    for _ in range(repetitions):
        kernel()
    end.record()
    end.synchronize()
    return start.elapsed_time(end) * 1000.0 / repetitions


def _finite(tensor: torch.Tensor, label: str) -> None:
    """Fail closed if an experimental kernel creates an invalid floating result."""

    if not torch.isfinite(tensor).all():
        raise RuntimeError(f"{label} produced non-finite output")


def _cpu_output(tensor: torch.Tensor) -> torch.Tensor:
    """Detach one GPU result as a contiguous CPU BF16 tensor for comparison."""

    return tensor.detach().to(device="cpu").contiguous()


def _sha256(tensor: torch.Tensor) -> str:
    """Return a stable digest of exactly the stored tensor bytes."""

    return hashlib.sha256(tensor.view(torch.uint8).numpy().tobytes()).hexdigest()


def _compare_outputs(
    candidate: dict[str, torch.Tensor], reference_path: Path | None
) -> dict[str, object] | None:
    """Validate every real-projection output against an optional baseline record."""

    if reference_path is None:
        return None
    reference = torch.load(reference_path, map_location="cpu", weights_only=True)
    if not isinstance(reference, dict) or set(reference) != set(candidate):
        raise ValueError("reference output must contain exactly gate, up, and down tensors")
    metrics: dict[str, dict[str, float]] = {}
    for name, output in candidate.items():
        expected = reference[name]
        if not isinstance(expected, torch.Tensor):
            raise TypeError(f"reference {name} is not a tensor")
        torch.testing.assert_close(output, expected, rtol=0.001, atol=0.01)
        difference = (output.float() - expected.float()).abs()
        metrics[name] = {
            "maximum_absolute_difference": float(difference.max().item()),
            "mean_absolute_difference": float(difference.mean().item()),
        }
    return {
        "reference_output": str(reference_path.resolve()),
        "rtol": 0.001,
        "atol": 0.01,
        "projections": metrics,
    }


def main() -> int:
    """Load true packed experts, warm both projections, and write one evidence file."""

    args = _parse_args()
    _require_inputs(args)
    device = torch.device("cuda")
    tensors = _tensor_map(args.model)
    prefix = f"blk.{args.layer}."
    gate_name = prefix + "ffn_gate_exps.weight"
    up_name = prefix + "ffn_up_exps.weight"
    down_name = prefix + "ffn_down_exps.weight"
    missing = [name for name in (gate_name, up_name, down_name) if name not in tensors]
    if missing:
        raise KeyError(f"GGUF lacks required MoE tensors: {missing}")

    # Qwen stores gate and up separately, so screen each real Q4_K bank.  The
    # production fused path uses the same routed-vector binding for both banks.
    gate = _expert_bank(tensors[gate_name], device)
    up = _expert_bank(tensors[up_name], device)
    down = _expert_bank(tensors[down_name], device)
    if tensors[gate_name].ggml_type != GGML_Q4_K or tensors[up_name].ggml_type != GGML_Q4_K:
        raise ValueError("Qwen gate/up tensors must be Q4_K for this benchmark")
    if tensors[down_name].ggml_type != GGML_Q5_K:
        raise ValueError("Qwen down tensor must be Q5_K for this benchmark")

    # One decoded token selects each copied expert once, matching Qwen's top-k
    # cardinality while avoiding any router or scheduler work in this screen.
    route_ids = torch.arange(DEFAULT_TOP_K, dtype=torch.int32, device=device).reshape(1, -1)
    hidden = torch.randn(1, 512, dtype=torch.bfloat16, device=device)
    intermediate = torch.randn(DEFAULT_TOP_K, 2048, dtype=torch.bfloat16, device=device)

    def gate_call() -> torch.Tensor:
        return ggml_moe_a8_vec(hidden, gate, route_ids, DEFAULT_TOP_K, int(GGML_Q4_K), 2048, 1)

    def up_call() -> torch.Tensor:
        return ggml_moe_a8_vec(hidden, up, route_ids, DEFAULT_TOP_K, int(GGML_Q4_K), 2048, 1)

    def down_call() -> torch.Tensor:
        return ggml_moe_a8_vec(intermediate, down, route_ids, 1, int(GGML_Q5_K), 512, DEFAULT_TOP_K)

    for _ in range(args.warmup):
        gate_output = gate_call()
        up_output = up_call()
        down_output = down_call()
    torch.cuda.synchronize(device)
    _finite(gate_output, "Q4_K gate")
    _finite(up_output, "Q4_K up")
    _finite(down_output, "Q5_K down")
    # Preserve the identical CPU tensors used for the parity check.  Event
    # timing remains separate below, so artifact transfer cannot affect it.
    outputs = {
        "gate": _cpu_output(gate_output),
        "up": _cpu_output(up_output),
        "down": _cpu_output(down_output),
    }
    parity = _compare_outputs(outputs, args.reference_output)

    result = {
        "schema_version": 1,
        "model": str(args.model.resolve()),
        "layer": args.layer,
        "device": torch.cuda.get_device_name(device),
        "hip": torch.version.hip,
        "torch": torch.__version__,
        "experts_copied": DEFAULT_TOP_K,
        "top_k": DEFAULT_TOP_K,
        "warmup": args.warmup,
        "repetitions": args.repetitions,
        "gate_q4k_us": _event_time_us(gate_call, args.repetitions, device),
        "up_q4k_us": _event_time_us(up_call, args.repetitions, device),
        "down_q5k_us": _event_time_us(down_call, args.repetitions, device),
        "gate_shape": list(gate_output.shape),
        "up_shape": list(up_output.shape),
        "down_shape": list(down_output.shape),
        "output_sha256": {name: _sha256(output) for name, output in outputs.items()},
        "parity": parity,
    }
    result["three_projection_us"] = result["gate_q4k_us"] + result["up_q4k_us"] + result["down_q5k_us"]
    args.json.parent.mkdir(parents=True, exist_ok=True)
    if args.save_output is not None:
        args.save_output.parent.mkdir(parents=True, exist_ok=True)
        torch.save(outputs, args.save_output)
    args.json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
