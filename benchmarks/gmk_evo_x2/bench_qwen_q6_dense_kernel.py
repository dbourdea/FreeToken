#!/usr/bin/env python3
"""Measure one real packed Q6_K Qwen dense vector projection on GMKtec EVO-X2.

This is the Q6_K counterpart to the established Q8_0 component screen.  It
maps a named original GGUF tensor, invokes the production one-token HIP binding,
and saves numerical parity plus average device time.  It is deliberately not
an API TPS benchmark: model load, prompt processing, routing, HTTP, and JIT
setup are excluded from the timed interval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch

from freetoken.kernel.gguf import ggml_mul_mat_vec_a8
from freetoken.models.gguf.dequant import GGML_Q6_K
from freetoken.models.gguf.reader import GgufTensor, iter_gguf_tensors


def parse_args() -> argparse.Namespace:
    """Read all immutable paths, timing counts, and parity tolerances."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--tensor", required=True)
    parser.add_argument("--warmup", type=int, default=30)
    parser.add_argument("--repetitions", type=int, default=300)
    parser.add_argument("--json", required=True, type=Path)
    parser.add_argument("--save-output", type=Path)
    parser.add_argument("--reference-output", type=Path)
    parser.add_argument("--rtol", type=float, default=0.001)
    parser.add_argument("--atol", type=float, default=0.01)
    args = parser.parse_args()
    if not args.model.is_file() or args.warmup <= 0 or args.repetitions <= 0:
        parser.error("model must exist and timing counts must be positive")
    if args.json.exists() or (args.save_output and args.save_output.exists()):
        parser.error("refusing to overwrite an existing artifact")
    if args.reference_output and not args.reference_output.is_file():
        parser.error("reference output is missing")
    if args.rtol < 0 or args.atol < 0 or not torch.cuda.is_available():
        parser.error("tolerances must be non-negative and HIP must be available")
    return args


def find_tensor(model: Path, name: str) -> GgufTensor:
    """Return a requested packed tensor without altering its GGUF bytes."""

    for tensor in iter_gguf_tensors(str(model)):
        if tensor.name == name:
            return tensor
    raise KeyError(f"GGUF tensor not found: {name}")


def digest(tensor: torch.Tensor) -> str:
    """Hash exact contiguous storage bytes without BF16 format conversion."""

    return hashlib.sha256(tensor.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()


def mean_device_us(kernel, repetitions: int, device: torch.device) -> float:
    """Time only synchronized production-kernel launches in microseconds."""

    start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
    torch.cuda.synchronize(device)
    start.record()
    for _ in range(repetitions):
        kernel()
    end.record()
    end.synchronize()
    return start.elapsed_time(end) * 1000.0 / repetitions


def main() -> int:
    """Run the real Q6_K screen and persist all parity and timing evidence."""

    args = parse_args()
    tensor = find_tensor(args.model, args.tensor)
    if tensor.ggml_type != GGML_Q6_K or len(tensor.shape) != 2:
        raise ValueError(f"{tensor.name} must be a two-dimensional Q6_K tensor")
    out_features, in_features = (int(value) for value in tensor.shape)
    device = torch.device("cuda")
    weight = tensor.packed().contiguous().to(device=device, non_blocking=False)
    generator = torch.Generator(device=device)
    generator.manual_seed(20260902)
    activation = torch.randn((1, in_features), dtype=torch.bfloat16, device=device, generator=generator)

    def kernel() -> torch.Tensor:
        """Invoke the production Q6_K one-token vector dispatch."""

        return ggml_mul_mat_vec_a8(weight, activation, int(GGML_Q6_K), out_features)

    for _ in range(args.warmup):
        output = kernel()
    torch.cuda.synchronize(device)
    if not torch.isfinite(output).all():
        raise RuntimeError("Q6_K dense kernel produced non-finite output")
    output_cpu = output.detach().cpu().contiguous()
    parity = None
    if args.reference_output:
        reference = torch.load(args.reference_output, map_location="cpu", weights_only=True).contiguous()
        torch.testing.assert_close(output_cpu, reference, rtol=args.rtol, atol=args.atol)
        delta = (output_cpu.float() - reference.float()).abs()
        parity = {"reference_sha256": digest(reference), "rtol": args.rtol, "atol": args.atol,
                  "maximum_absolute_difference": float(delta.max().item()),
                  "mean_absolute_difference": float(delta.mean().item())}
    if args.save_output:
        args.save_output.parent.mkdir(parents=True, exist_ok=True)
        torch.save(output_cpu, args.save_output)
    result = {"schema_version": 1, "classification": "real-weight dense Q6_K HIP kernel screen, not API TPS",
              "model": str(args.model.resolve()), "tensor": tensor.name, "weight_shape": [out_features, in_features],
              "packed_weight_shape": list(weight.shape), "output_shape": list(output.shape), "quantization": "Q6_K",
              "warmup": args.warmup, "repetitions": args.repetitions, "device": torch.cuda.get_device_name(device),
              "hip": torch.version.hip, "torch": torch.__version__, "mean_device_us": mean_device_us(kernel, args.repetitions, device),
              "output_sha256": digest(output_cpu), "parity": parity}
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
