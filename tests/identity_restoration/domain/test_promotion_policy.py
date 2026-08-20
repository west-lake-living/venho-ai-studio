from __future__ import annotations

import pytest

from identity_restoration.domain.policies.pixel_preservation import PixelLockReport
from identity_restoration.domain.policies.promotion import QcResult, is_full_gate_pass, is_official


def test_full_gate_pass_requires_all_conditions() -> None:
    good_pixel = PixelLockReport(passed=True, mutated_pixel_count=0, editable_region_hash="x")
    bad_pixel = PixelLockReport(passed=False, mutated_pixel_count=5, editable_region_hash="x")
    good_qc = QcResult(face_score=95.0, all_validators_approved=True, kill_switch_triggered=False)
    low_qc = QcResult(face_score=80.0, all_validators_approved=True, kill_switch_triggered=False)

    assert is_full_gate_pass(good_qc, good_pixel, face_qc_min=90.0) is True
    assert is_full_gate_pass(low_qc, good_pixel, face_qc_min=90.0) is False
    assert is_full_gate_pass(good_qc, bad_pixel, face_qc_min=90.0) is False


def test_no_code_path_creates_official_asset() -> None:
    """is_official() must always raise — official promotion is a human action."""
    with pytest.raises(NotImplementedError):
        is_official()
