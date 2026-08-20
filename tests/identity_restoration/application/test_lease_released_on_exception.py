from __future__ import annotations

from tests.identity_restoration.application.conftest import ExplodingRestorer, FakeLease


def test_lease_released_on_restorer_exception(build_use_case, restore_command_factory) -> None:
    """The lease must always be released, even when the restorer raises
    (v2.0 PHẦN 12.3 #2). RestoreFaceCropUseCase relies on the lease's own
    context manager `finally`; this test proves that guarantee end to end."""
    ExplodingRestorer.call_count = 0
    lease = FakeLease()
    use_case = build_use_case(a2_sha256="deadbeef", restorer=ExplodingRestorer(), lease=lease)
    cmd = restore_command_factory(a2_sha256="deadbeef")

    result = use_case.execute(cmd)

    assert result.status == "FAILED"
    assert ExplodingRestorer.call_count == 1
    assert lease.acquired_count == 1
    assert lease.released_count == 1
