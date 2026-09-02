#!/usr/bin/env python3
"""Gate a dense Q8_0 HIP launch geometry with real Qwen GGUF tensor bytes.

This component benchmark deliberately isolates the production dense vector
binding. It maps one named Q8_0 tensor from the qualified Qwen GGUF, invokes
the normal FreeToken Q8_0 kernel with a fixed BF16 decoded-token vector, and
records synchronized device time. A candidate may write a CPU reference output
or compare against one, but this program never reports API throughput because
model loading, routing, scheduling, HTTP, and tokenization are out of scope.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch

from freetoken.kernel.gguf import ggml_mul_mat_vec_a8
from freetoken.models.gguf.dequant import GGML_Q8_0
from freetoken.models.gguf.reader import GgufTensor, iter_gguf_tensors


def _args() -> argparse.Namespace:
    """Parse immutable artifact paths and reject unsafe or incomplete inputs."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path, help="qualified Q4_K_M GGUF")
    parser.add_argument("--tensor", required=True, help="named two-dimensional Q8_0 tensor")
    parser.add_argument("--json", required=True, type=Path, help="new JSON result path")
    parser.add_argument("--save-output", type=Path, help="new CPU output tensor path")
    parser.add_argument("--reference-output", type=Path, help="existing CPU output required for parity")
    parser.add_argument("--warmup", type=int, default=30, help="unscored warm calls")
    parser.add_argument("--repetitions", type=int, default=300, help="synchronized timed calls")
    args = parser.parse_args()
    if not args.model.is_file():
        parser.error(f"model is missing: {args.model}")
    if args.json.exists() or (args.save_output is not None and args.save_output.exists()):
        parser.error("refusing to overwrite an evidence artifact")
    if args.reference_output is not None and not args.reference_output.is_file():
        parser.error(f"reference output is missing: {args.reference_output}")
    if args.warmup <= 0 or args.repetitions <= 0:
        parser.error("--warmup and --repetitions must be positive")
    if not torch.cuda.is_available():
        parser.error("a CUDA or HIP PyTorch device is required")
    return args


def _tensor(model: Path, name: str) -> GgufTensor:
    """Return exactly one named tensor without changing its GGUF packing."""

    for tensor in iter_gguf_tensors(str(model)):
        if tensor.name == name:
            # ``GgufTensor`` exposes its logical dimensions through ``shape``
            # rather than a NumPy-style ``ndim`` attribute. Checking the
            # length prevents a packed one-dimensional payload from reaching
            # the dense vector binding with an invalid row or column contract.
            if tensor.ggml_type != GGML_Q8_0 or len(tensor.shape) != 2:
                raise ValueError(f"{name} must be a two-dimensional Q8_0 tensor")
            return tensor
    raise KeyError(f"GGUF does not contain {name}")


def _time_us(call, repetitions: int, device: torch.device) -> float:
    """Return average synchronized GPU elapsed time in microseconds."""

    start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
    torch.cuda.synchronize(device)
    start.record()
    for _ in range(repetitions):
        call()
    end.record()
    end.synchronize()
    return start.elapsed_time(end) * 1000.0 / repetitions


def _digest(value: torch.Tensor) -> str:
    """Hash the exact BF16 storage bytes rather than a rounded conversion."""

    return hashlib.sha256(value.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()


def main() -> int:
    """Run warmup, exact tensor parity, and post-parity device timing."""

    args = _args()
    device = torch.device("cuda")
    source = _tensor(args.model, args.tensor)
    rows, columns = source.shape
    packed = source.packed().contiguous().to(device=device, non_blocking=False)
    activation = torch.randn(1, columns, dtype=torch.bfloat16, device=device)

    def call() -> torch.Tensor:
        # The production binding receives packed weight first and derives the
        # input width from that payload. Passing only its four public arguments
        # keeps this component call identical to normal model execution.
        return ggml_mul_mat_vec_a8(packed, activation, int(GGML_Q8_0), rows)

    for _ in range(args.warmup):
        output = call()
    torch.cuda.synchronize(device)
    if not torch.isfinite(output).all():
        raise RuntimeError("candidate produced a non-finite dense Q8_0 output")
    cpu_output = output.detach().to(device="cpu").contiguous()
    parity: dict[str, float] | None = None
    if args.reference_output is not None:
        expected = torch.load(args.reference_output, map_location="cpu", weights_only=True)
        torch.testing.assert_close(cpu_output, expected, rtol=0.001, atol=0.01)
        difference = (cpu_output.float() - expected.float()).abs()
        parity = {
            "maximum_absolute_difference": float(difference.max().item()),
            "mean_absolute_difference": float(difference.mean().item()),
        }
    if args.save_output is not None:
        args.save_output.parent.mkdir(parents=True, exist_ok=True)
        torch.save(cpu_output, args.save_output)
    result = {
        "schema_version": 1,
        "model": str(args.model.resolve()),
        "tensor": source.name,
        "shape": [rows, columns],
        "device": torch.cuda.get_device_name(device),
        "hip": torch.version.hip,
        "torch": torch.__version__,
        "warmup": args.warmup,
        "repetitions": args.repetitions,
        "device_time_us": _time_us(call, args.repetitions, device),
        "output_sha256": _digest(cpu_output),
        "parity": parity,
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
