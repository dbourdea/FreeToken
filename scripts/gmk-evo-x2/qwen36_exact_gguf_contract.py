"""Run an explicit local-model contract check for the Qwen3.6 mixed GGUF loader."""

# Import argument parsing so operators must name the private model artifact explicitly.
import argparse

# Import Torch for CPU/meta model construction without allocating production model memory.
import torch

# Import tensor-parallel setup because model construction reads the active TP identity.
from freetoken.distributed.info import set_tp_info
# Import rotary-device setup because meta construction still requires an explicit safe device.
from freetoken.layers.rotary import set_rope_device
# Import the GGUF shim builder so the private artifact drives the exact model configuration.
from freetoken.models.gguf.config import build_gguf_shim
# Import the Qwen parser so the check uses the same architecture contract as runtime loading.
from freetoken.models.qwen3_5_moe.config import parse_gguf_config
# Import the production iterator so validation covers the real GGUF tensor mapping.
from freetoken.models.qwen3_5_moe.gguf import iter_gguf_weights
# Import model registration so the configured architecture resolves through the public runtime registry.
from freetoken.models.register import get_model_class
# Import the dtype context because meta construction must match runtime bfloat16 expectations.
from freetoken.utils.torch_utils import torch_dtype


def require(condition: bool, detail: object) -> None:
    """Raise an optimization-safe contract failure with the supplied diagnostic."""
    # Reject false conditions explicitly because Python optimization can remove ordinary assert statements.
    if not condition:
        # Preserve the mismatch detail so operators can identify the exact tensor or tokenizer contract.
        raise RuntimeError(f"Qwen GGUF contract failed: {detail}")


def validate(model_path: str, *, check_tokenizer: bool) -> None:
    """Validate exact non-MoE tensor shape/dtype coverage and optional tokenizer round-trip."""
    # Configure one CPU rank because the local check is intentionally isolated from distributed launch state.
    set_tp_info(0, 1)
    # Pin rotary metadata to CPU so validation cannot accidentally initialize a GPU runtime.
    set_rope_device(torch.device("cpu"))
    # Parse the exact private artifact through the production GGUF configuration path.
    config = parse_gguf_config(build_gguf_shim(model_path))
    # Build only metadata tensors so the contract check remains bounded on systems without model-sized RAM.
    with torch.device("meta"), torch_dtype(torch.bfloat16):
        # Resolve and instantiate the same registered model class selected during production serving.
        model = get_model_class(config.architectures[0], config)
    # Copy expected state keys so every observed GGUF tensor can remove exactly one contract entry.
    expected = model.state_dict()
    # Iterate non-expert tensors because the exact expert payload is validated by its separate streamed path.
    for name, value in iter_gguf_weights(
        model_path,
        device="cpu",
        include_moe_experts=False,
        include_non_moe=True,
    ):
        # Remove the matching destination so unknown or duplicate names fail at their point of use.
        target = expected.pop(name)
        # Require shape equality because a shape-compatible load is the minimum safe tensor contract.
        require(target.shape == value.shape, (name, target.shape, value.shape))
        # Require dtype equality because implicit conversion would invalidate the exact-file contract.
        require(target.dtype == value.dtype, (name, target.dtype, value.dtype))
    # Require complete destination coverage so silently omitted tensors cannot pass the manual validator.
    require(not expected, sorted(expected))
    # Emit a stable marker for private automation that records this bounded validation result.
    print("EXACT_GGUF_STATE_CONTRACT_OK")
    # Skip tokenizer work unless requested because tokenizer loading adds private-artifact I/O.
    if not check_tokenizer:
        # Return after the required tensor contract because no optional tokenizer gate was selected.
        return
    # Import lazily so tensor-only validation does not load tokenizer dependencies unnecessarily.
    from freetoken.models.gguf.tokenizer import load_gguf_tokenizer
    # Load the tokenizer from the same exact artifact to prevent cross-checkpoint substitution.
    tokenizer = load_gguf_tokenizer(model_path)
    # Use a stable visible string because the check is round-trip integrity, not model quality.
    text = "Hello, model."
    # Require exact decode equality so tokenizer normalization drift is visible to the operator.
    require(tokenizer.decode(tokenizer.encode(text, add_special_tokens=False)) == text, text)
    # Emit a separate marker so automation can distinguish tensor-only and tokenizer-complete runs.
    print("TOKENIZER_ROUND_TRIP_OK")


def main(argv: list[str] | None = None) -> int:
    """Parse explicit private inputs and run the local contract validator."""
    # Create the CLI parser inside main so importing this module never consumes pytest or caller arguments.
    parser = argparse.ArgumentParser(description=__doc__)
    # Require the local model path because the repository intentionally contains no private checkpoint.
    parser.add_argument("model", help="Local Qwen35 GGUF file to validate on CPU/meta")
    # Make tokenizer validation opt-in because it is slower and independent from tensor shape coverage.
    parser.add_argument("--tokenizer", action="store_true", help="Also verify a tokenizer text round-trip")
    # Parse only the caller-supplied arguments so tests and wrappers can invoke main deterministically.
    args = parser.parse_args(argv)
    # Run the complete selected validation before reporting success.
    validate(args.model, check_tokenizer=args.tokenizer)
    # Return zero only after every selected contract gate completes.
    return 0


# Execute the CLI only when invoked as a script so imports remain side-effect free.
if __name__ == "__main__":
    # Propagate the explicit status code to shells and automation.
    raise SystemExit(main())
