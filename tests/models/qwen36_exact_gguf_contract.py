"""Exact-file, CPU/meta contract check for the Qwen3.6 mixed GGUF loader."""

import argparse
import torch

from freetoken.distributed.info import set_tp_info
from freetoken.layers.rotary import set_rope_device
from freetoken.models.gguf.config import build_gguf_shim
from freetoken.models.qwen3_5_moe.config import parse_gguf_config
from freetoken.models.qwen3_5_moe.gguf import iter_gguf_weights
from freetoken.models.register import get_model_class
from freetoken.utils.torch_utils import torch_dtype


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("model", help="Local Qwen35 GGUF file to validate on CPU/meta")
parser.add_argument("--tokenizer", action="store_true", help="Also verify a tokenizer text round-trip")
args = parser.parse_args()
MODEL_PATH = args.model


set_tp_info(0, 1)
set_rope_device(torch.device("cpu"))
config = parse_gguf_config(build_gguf_shim(MODEL_PATH))
with torch.device("meta"), torch_dtype(torch.bfloat16):
    model = get_model_class(config.architectures[0], config)

expected = model.state_dict()
for name, value in iter_gguf_weights(
    MODEL_PATH,
    device="cpu",
    include_moe_experts=False,
    include_non_moe=True,
):
    target = expected.pop(name)
    assert target.shape == value.shape, (name, target.shape, value.shape)
    assert target.dtype == value.dtype, (name, target.dtype, value.dtype)

assert not expected, sorted(expected)
print("EXACT_GGUF_STATE_CONTRACT_OK")
if args.tokenizer:
    from freetoken.models.gguf.tokenizer import load_gguf_tokenizer

    tokenizer = load_gguf_tokenizer(MODEL_PATH)
    text = "Hello, model."
    assert tokenizer.decode(tokenizer.encode(text, add_special_tokens=False)) == text
    print("TOKENIZER_ROUND_TRIP_OK")
