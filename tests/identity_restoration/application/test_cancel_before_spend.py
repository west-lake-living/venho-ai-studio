from __future__ import annotations

from tests.identity_restoration.application.conftest import CountingMockRestorer


def test_cancel_checked_before_restore_call(build_use_case, restore_command_factory) -> None:
    """Cancel must be honoured before the costly restorer call — no GPU-time
    spent on a job the caller already cancelled (v2.0 PHẦN 12.3 #3)."""
    CountingMockRestorer.call_count = 0
    restorer = CountingMockRestorer()
    use_case = build_use_case(a2_sha256="deadbeef", restorer=restorer)
    use_case._cancel_check = lambda run_id: True  # simulate an already-cancelled run
    cmd = restore_command_factory(a2_sha256="deadbeef")

    result = use_case.execute(cmd)

    assert result.status == "CANCELLED"
    assert CountingMockRestorer.call_count == 0
