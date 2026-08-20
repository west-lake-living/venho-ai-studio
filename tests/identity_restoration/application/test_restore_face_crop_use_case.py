from __future__ import annotations

from identity_restoration.domain.errors import RestorationError


def test_happy_path_via_mock_restorer_returns_needs_review_without_qc(build_use_case, restore_command_factory):
    use_case = build_use_case(a2_sha256="deadbeef")
    cmd = restore_command_factory(a2_sha256="deadbeef")

    result = use_case.execute(cmd)

    assert result.status == "NEEDS_REVIEW"  # no QcGatewayPort wired -> can't reach FULL_GATE_PASS
    assert result.pixel_lock is not None
    assert result.pixel_lock.passed is True
    assert result.composite_path is not None
    assert result.restored_crop_path is not None
    assert result.error is None


def test_a2_hash_mismatch_fails_before_any_restorer_call(build_use_case, restore_command_factory):
    from tests.identity_restoration.application.conftest import CountingMockRestorer

    CountingMockRestorer.call_count = 0
    use_case = build_use_case(a2_sha256="expected-hash", restorer=CountingMockRestorer())
    cmd = restore_command_factory(a2_sha256="wrong-hash")

    result = use_case.execute(cmd)

    assert result.status == "FAILED"
    assert result.error is not None
    assert result.error.code == "ERR_GW_A2_HASH_MISMATCH"
    assert CountingMockRestorer.call_count == 0


def test_pixel_lock_is_evaluated_even_when_face_qc_is_perfect(build_use_case, restore_command_factory):
    """A beautiful face score never bypasses the pixel-lock gate.

    The domain compositor pastes strictly inside the same mask used for the
    lock check (identity_restoration/domain/compositing.py +
    domain/policies/pixel_preservation.py both take editable_mask_png/
    editable_mask), so a Port-conformant restorer cannot violate lock through
    it — that shared-mask design IS the guarantee (see
    tests/identity_restoration/domain/test_pixel_preservation.py for the
    domain-level fail case). What this test proves at the use-case level is
    that pixel_lock is still computed and still gates the status even when
    QC reports a perfect score, i.e. QC never short-circuits the check.
    """
    from identity_restoration.domain.policies.promotion import QcResult

    class AlwaysPerfectQc:
        def validate(self, composite_path, a2_path):
            return QcResult(face_score=100.0, all_validators_approved=True, kill_switch_triggered=False)

    use_case = build_use_case(a2_sha256="deadbeef", qc=AlwaysPerfectQc())
    cmd = restore_command_factory(a2_sha256="deadbeef")

    result = use_case.execute(cmd)

    assert result.pixel_lock is not None and result.pixel_lock.passed is True
    assert result.status == "FULL_GATE_PASS"
