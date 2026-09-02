#!/usr/bin/env python3
"""Screen one Qwen GDN decode-kernel pipeline depth on a GMKtec EVO-X2.

This geometry-matched component benchmark reads the target GGUF metadata, then
uses deterministic synthetic decode inputs with the exact attention and GDN
state dimensions.  It measures only production fused-GDN device launches and
requires exact output plus recurrent-state equality against a saved qualified
three-stage reference.  It is not an end-to-end API TPS benchmark and never
claims to use model weights.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
from pathlib import Path
from typing import Any

import torch

from freetoken.kernel.fla import fused_sigmoid_gating_delta_rule_update
from freetoken.models.gguf.reader import load_gguf_metadata


EXPECTED_HOSTNAME = "david-Gmktec-x2-2"
EXPECTED_METADATA = {
    "qwen35moe.attention.head_count": 16,
    "qwen35moe.attention.head_count_kv": 2,
    "qwen35moe.attention.key_length": 256,
    "qwen35moe.attention.value_length": 256,
    "qwen35moe.ssm.group_count": 16,
    "qwen35moe.ssm.inner_size": 4096,
    "qwen35moe.ssm.state_size": 128,
}


def parse_args() -> argparse.Namespace:
    """Read immutable artifact paths and positive launch-count settings."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--warmup", type=int, default=30)
    parser.add_argument("--repetitions", type=int, default=300)
    parser.add_argument("--json", required=True, type=Path)
    parser.add_argument("--save-output", type=Path)
    parser.add_argument("--reference-output", type=Path)
    args = parser.parse_args()
    if socket.gethostname() != EXPECTED_HOSTNAME:
        parser.error(f"this controlled GPU screen requires {EXPECTED_HOSTNAME}")
    if not args.model.is_file() or args.warmup <= 0 or args.repetitions <= 0:
        parser.error("model must exist and timing counts must be positive")
    if args.json.exists() or (args.save_output and args.save_output.exists()):
        parser.error("refusing to overwrite an existing artifact")
    if args.reference_output and not args.reference_output.is_file():
        parser.error("reference output is missing")
    if not torch.cuda.is_available():
        parser.error("HIP must be available")
    return args


def sha256(tensor: torch.Tensor) -> str:
    """Hash exact contiguous tensor storage bytes without value conversion."""

    return hashlib.sha256(tensor.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()


def require_geometry(model: Path) -> dict[str, int]:
    """Load and validate the GGUF dimensions represented by this screen."""

    metadata: dict[str, Any] = load_gguf_metadata(str(model))
    observed: dict[str, int] = {}
    for key, expected in EXPECTED_METADATA.items():
        if key not in metadata:
            raise ValueError(f"GGUF metadata is missing required key: {key}")
        value = int(metadata[key])
        if value != expected:
            raise ValueError(f"{key} must be {expected}, got {value}")
        observed[key] = value
    return observed


def make_inputs(device: torch.device, geometry: dict[str, int]) -> dict[str, torch.Tensor]:
    """Create deterministic one-token GDN decode inputs at the validated geometry."""

    generator = torch.Generator(device=device)
    generator.manual_seed(20260902)
    heads = geometry["qwen35moe.attention.head_count_kv"]
    value_heads = geometry["qwen35moe.ssm.group_count"]
    key_length = geometry["qwen35moe.attention.key_length"]
    value_length = geometry["qwen35moe.attention.value_length"]
    return {
        "A_log": torch.randn((value_heads,), device=device, dtype=torch.float32, generator=generator),
        "a": torch.randn((1, value_heads), device=device, dtype=torch.float32, generator=generator),
        "dt_bias": torch.randn((value_heads,), device=device, dtype=torch.float32, generator=generator),
        "q": torch.randn((1, 1, heads, key_length), device=device, dtype=torch.bfloat16, generator=generator),
        "k": torch.randn((1, 1, heads, key_length), device=device, dtype=torch.bfloat16, generator=generator),
        "v": torch.randn((1, 1, value_heads, value_length), device=device, dtype=torch.bfloat16, generator=generator),
        "b": torch.randn((1, value_heads), device=device, dtype=torch.float32, generator=generator),
        "initial_state": torch.randn((1, value_heads, key_length, value_length), device=device, dtype=torch.float32, generator=generator),
        "indices": torch.zeros((1,), device=device, dtype=torch.int32),
        "cu_seqlens": torch.tensor([0, 1], device=device, dtype=torch.int32),
    }


def invoke(inputs: dict[str, torch.Tensor], state: torch.Tensor) -> torch.Tensor:
    """Launch the production fused GDN decode path, mutating only supplied state."""

    return fused_sigmoid_gating_delta_rule_update(
        A_log=inputs["A_log"], a=inputs["a"], dt_bias=inputs["dt_bias"],
        softplus_beta=1.0, softplus_threshold=20.0, q=inputs["q"], k=inputs["k"],
        v=inputs["v"], b=inputs["b"], initial_state_source=state,
        initial_state_indices=inputs["indices"], scale=inputs["q"].shape[-1] ** -0.5,
        use_qk_l2norm_in_kernel=True, cu_seqlens=inputs["cu_seqlens"],
    )


def time_launches(inputs: dict[str, torch.Tensor], state: torch.Tensor, repetitions: int, device: torch.device) -> tuple[float, torch.Tensor]:
    """Time only consecutive device launches and return the final production output."""

    start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
    torch.cuda.synchronize(device)
    start.record()
    for _ in range(repetitions):
        output = invoke(inputs, state)
    end.record()
    end.synchronize()
    return start.elapsed_time(end) * 1000.0 / repetitions, output


def main() -> int:
    """Compile, warm, time, compare, and persist the bounded GDN screen evidence."""

    args = parse_args()
    geometry = require_geometry(args.model)
    device = torch.device("cuda")
    inputs = make_inputs(device, geometry)
    initial_state = inputs.pop("initial_state")
    for _ in range(args.warmup):
        invoke(inputs, initial_state.clone())
    torch.cuda.synchronize(device)
    timed_state = initial_state.clone()
    mean_device_us, output = time_launches(inputs, timed_state, args.repetitions, device)
    output_cpu, state_cpu = output.detach().cpu().contiguous(), timed_state.detach().cpu().contiguous()
    if not torch.isfinite(output_cpu).all() or not torch.isfinite(state_cpu).all():
        raise RuntimeError("GDN decode kernel produced non-finite output or state")
    evidence = {"output": output_cpu, "state": state_cpu}
    parity = None
    if args.reference_output:
        reference = torch.load(args.reference_output, map_location="cpu", weights_only=True)
        torch.testing.assert_close(output_cpu, reference["output"], rtol=0, atol=0)
        torch.testing.assert_close(state_cpu, reference["state"], rtol=0, atol=0)
        parity = {"reference_output_sha256": sha256(reference["output"]), "reference_state_sha256": sha256(reference["state"]), "exact": True}
    if args.save_output:
        args.save_output.parent.mkdir(parents=True, exist_ok=True)
        torch.save(evidence, args.save_output)
    result = {"schema_version": 1, "classification": "geometry-matched deterministic GDN HIP kernel screen, not API TPS and not real-weight inference", "model": str(args.model.resolve()), "geometry": geometry, "warmup": args.warmup, "repetitions": args.repetitions, "device": torch.cuda.get_device_name(device), "hip": torch.version.hip, "torch": torch.__version__, "mean_device_us": mean_device_us, "output_sha256": sha256(output_cpu), "state_sha256": sha256(state_cpu), "parity": parity}
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
