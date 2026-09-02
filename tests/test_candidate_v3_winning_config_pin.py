from identity_restoration.domain.policies.candidate_v3_winning_config import (
    R2_WINNING_CONFIG_ID,
    R2_WINNING_CONFIG_SHA256,
    R2_WINNING_CONFIG_SOURCE,
    resolve_candidate_v3_params,
)
from identity_restoration.domain.value_objects import RestorationParams


def test_r2_winning_pin_is_deterministic_and_linked_to_authoritative_evidence() -> None:
    requested = RestorationParams(denoise=0.40, steps=20, cfg=5.0, sampler="euler", scheduler="normal")
    resolved = resolve_candidate_v3_params(case_id="B05", requested=requested)

    assert (resolved.params.denoise, resolved.params.cfg, resolved.params.steps) == (0.35, 6.1, 21)
    assert resolved.source == "R2_WINNING_CONFIG"
    assert resolved.config_id == R2_WINNING_CONFIG_ID
    assert resolved.config_sha256 == R2_WINNING_CONFIG_SHA256
    assert "r2-b05-face-local-focused-recovery" in R2_WINNING_CONFIG_SOURCE
