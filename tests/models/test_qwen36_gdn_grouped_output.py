import torch
import pytest
from types import SimpleNamespace

from freetoken.models.qwen3_5_moe.gdn import Qwen3_5GatedDeltaNet
from freetoken.models.qwen3_5_moe.gguf import _restore_gdn_value_head_order


def test_grouped_output_activation_inverts_gguf_value_head_restore():
    """Q4_K GDN output weights remain packed while activation order is inverted."""
    grouped = torch.arange(2 * 48 * 128, dtype=torch.float32).reshape(2, 48, 128)
    free_token_order = _restore_gdn_value_head_order(grouped.transpose(0, 1), 16).transpose(0, 1)

    op = Qwen3_5GatedDeltaNet.__new__(Qwen3_5GatedDeltaNet)
    op.num_k_heads = 16
    op.num_v_heads = 48
    op.head_v_dim = 128

    restored_grouped = op._gguf_group_value_heads_for_out_proj(free_token_order.reshape(2, -1))
    assert torch.equal(restored_grouped.reshape_as(grouped), grouped)


@pytest.mark.parametrize("qkv_type", [8, 12, 14])
@pytest.mark.parametrize("gate_type", [8, 12, 14])
def test_dense_gdn_uses_each_tensor_descriptor(qkv_type, gate_type):
    from freetoken.distributed import set_tp_info, try_get_tp_info
    from freetoken.models.gguf.dequant import row_bytes

    if try_get_tp_info() is None:
        set_tp_info(rank=0, size=1)
    config = SimpleNamespace(gguf_tensor_types=(
        ("blk.0.attn_qkv.weight", qkv_type),
        ("blk.0.attn_gate.weight", gate_type),
    ))
    with torch.device("meta"):
        op = Qwen3_5GatedDeltaNet(
            hidden_size=4096, num_k_heads=16, num_v_heads=32,
            head_k_dim=128, head_v_dim=128, conv_kernel_size=4,
            rms_norm_eps=1e-6, layer_id=0, attn_quant="gguf_mixed", config=config,
        )
    assert op.in_proj_qkv._quant_type == qkv_type
    assert op.in_proj_z._quant_type == gate_type
    assert op.in_proj_qkv.qweight.shape[-1] == row_bytes(4096, qkv_type)
    assert op.in_proj_z.qweight.shape[-1] == row_bytes(4096, gate_type)
    assert not hasattr(op, "in_proj_qkvz")
