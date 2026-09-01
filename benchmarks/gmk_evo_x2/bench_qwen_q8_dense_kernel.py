#!/usr/bin/env python3
"""Measure one real packed Q8_0 Qwen dense vector projection on GMKtec EVO-X2.

The benchmark maps an explicitly named tensor from the qualified Q4_K_M GGUF,
copies its original packed Q8_0 rows to the HIP device, and invokes the exact
production ``ggml_mul_mat_vec_a8`` binding with one BF16 decoded-token vector.
It is a kernel-selection screen, not an API TPS result: it excludes model load,
tokenization, routing, scheduling, HTTP, and one-time extension compilation.
The resulting JSON evidence is intended to reject unsafe or slower component
ports before they consume an isolated full-service test window.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from freetoken.kernel.gguf import ggml_mul_mat_vec_a8
from freetoken.models.gguf.dequant import GGML_Q8_0
from freetoken.models.gguf.reader import GgufTensor, iter_gguf_tensors


def parse_args() -> argparse.Namespace:
    """Require every performance-affecting input and artifact destination."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path, help="qualified Q4_K_M GGUF")
    parser.add_argument(
        "--tensor",
        required=True,
        help="one two-dimensional GGUF Q8_0 tensor, such as blk.0.attn_qkv.weight",
    )
    parser.add_argument("--warmup", type=int, default=30, help="unmeasured production-kernel calls")
    parser.add_argument("--repetitions", type=int, default=300, help="timed production-kernel calls")
    parser.add_argument("--json", required=True, type=Path, help="new immutable JSON artifact")
    args = parser.parse_args()
    if not args.model.is_file():
        parser.error(f"GGUF model is missing: {args.model}")
    if args.warmup <= 0 or args.repetitions <= 0:
        parser.error("--warmup and --repetitions must be positive")
    if args.json.exists():
        parser.error(f"refusing to overwrite artifact: {args.json}")
    if not torch.cuda.is_available():
        parser.error("this benchmark requires a CUDA or HIP PyTorch device")
    return args


def find_tensor(model: Path, name: str) -> GgufTensor:
    """Return the requested real tensor while preserving its packed GGUF bytes."""

    for tensor in iter_gguf_tensors(str(model)):
        if tensor.name == name:
            return tensor
    raise KeyError(f"GGUF tensor not found: {name}")


def event_time_us(kernel, repetitions: int, device: torch.device) -> float:
    """Return average synchronized device elapsed time in microseconds."""

    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    torch.cuda.synchronize(device)
    start.record()
    for _ in range(repetitions):
        kernel()
    end.record()
    end.synchronize()
    return start.elapsed_time(end) * 1000.0 / repetitions


def main() -> int:
    """Screen one dense Q8_0 projection and preserve complete measurement context."""

    args = parse_args()
    tensor = find_tensor(args.model, args.tensor)
    if tensor.ggml_type != GGML_Q8_0:
        raise ValueError(f"{tensor.name} is not Q8_0: ggml type={tensor.ggml_type}")
    if len(tensor.shape) != 2:
        raise ValueError(f"{tensor.name} must be two-dimensional, got shape={tensor.shape}")

    out_features, in_features = (int(dimension) for dimension in tensor.shape)
    device = torch.device("cuda")
    # ``packed`` is a zero-copy CPU view.  ``contiguous`` owns the copy before
    # HIP transfer, which avoids writing through the GGUF reader's read-only map.
    weight = tensor.packed().contiguous().to(device=device, non_blocking=False)
    # A fixed seed makes the activation input reproducible without changing the
    # model's real packed weights or claiming this is a model-quality workload.
    generator = torch.Generator(device=device)
    generator.manual_seed(20260901)
    activation = torch.randn((1, in_features), dtype=torch.bfloat16, device=device, generator=generator)

    def kernel() -> torch.Tensor:
        """Call the same Q8_0 MMVQ operator selected for one decoded token."""

        return ggml_mul_mat_vec_a8(weight, activation, int(GGML_Q8_0), out_features)

    for _ in range(args.warmup):
        output = kernel()
    torch.cuda.synchronize(device)
    if not torch.isfinite(output).all():
        raise RuntimeError("Q8_0 dense kernel produced non-finite output")

    result = {
        "schema_version": 1,
        "classification": "real-weight dense Q8_0 HIP kernel screen, not API TPS",
        "model": str(args.model.resolve()),
        "tensor": tensor.name,
        "weight_shape": [out_features, in_features],
        "packed_weight_shape": list(weight.shape),
        "output_shape": list(output.shape),
        "quantization": "Q8_0",
        "warmup": args.warmup,
        "repetitions": args.repetitions,
        "device": torch.cuda.get_device_name(device),
        "hip": torch.version.hip,
        "torch": torch.__version__,
        "mean_device_us": event_time_us(kernel, args.repetitions, device),
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
