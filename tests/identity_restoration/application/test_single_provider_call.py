from __future__ import annotations

from tests.identity_restoration.application.conftest import CountingMockRestorer


def test_restorer_called_exactly_once(build_use_case, restore_command_factory) -> None:
    """Guards against hidden cost: exactly one call site to restorer.restore()
    in RestoreFaceCropUseCase.execute() (v2.0 PHẦN 12.3 #1)."""
    CountingMockRestorer.call_count = 0
    restorer = CountingMockRestorer()
    use_case = build_use_case(a2_sha256="deadbeef", restorer=restorer)
    cmd = restore_command_factory(a2_sha256="deadbeef")

    use_case.execute(cmd)

    assert CountingMockRestorer.call_count == 1
