"""Host-side validation for the bounded fused-GDN launch configuration.

The tests do not allocate a GPU or compile Triton.  Device correctness and
performance are covered by the isolated real-model gate on the target AMD GPU.
"""

from __future__ import annotations

import pytest

from freetoken.kernel.fla import fused_sigmoid_gating_recurrent as gdn


def test_gdn_launch_config_defaults_to_one_wave(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the established launch width when no experiment is selected."""

    monkeypatch.delenv("FREETOKEN_GDN_NUM_WARPS", raising=False)

    assert gdn._gdn_num_warps() == 1


def test_gdn_launch_config_allows_the_two_wave_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expose exactly the reviewed ROCm candidate width."""

    monkeypatch.setenv("FREETOKEN_GDN_NUM_WARPS", "2")

    assert gdn._gdn_num_warps() == 2


def test_gdn_launch_config_rejects_unreviewed_width(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail closed instead of silently compiling an arbitrary workgroup shape."""

    monkeypatch.setenv("FREETOKEN_GDN_NUM_WARPS", "4")

    with pytest.raises(RuntimeError, match="FREETOKEN_GDN_NUM_WARPS must be 1 or 2"):
        gdn._gdn_num_warps()


def test_gdn_stage_config_defaults_to_qualified_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the known three-stage pipeline when no component screen is selected."""

    monkeypatch.delenv("FREETOKEN_GDN_NUM_STAGES", raising=False)

    assert gdn._gdn_num_stages() == 3


@pytest.mark.parametrize("candidate", ["2", "4"])
def test_gdn_stage_config_allows_reviewed_candidates(
    monkeypatch: pytest.MonkeyPatch, candidate: str
) -> None:
    """Expose only the two isolated HIP pipeline-depth candidates."""

    monkeypatch.setenv("FREETOKEN_GDN_NUM_STAGES", candidate)

    assert gdn._gdn_num_stages() == int(candidate)


def test_gdn_stage_config_rejects_unreviewed_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail closed rather than creating an unexplained compiler-cache variant."""

    monkeypatch.setenv("FREETOKEN_GDN_NUM_STAGES", "5")

    with pytest.raises(RuntimeError, match="FREETOKEN_GDN_NUM_STAGES must be 2, 3, or 4"):
        gdn._gdn_num_stages()
