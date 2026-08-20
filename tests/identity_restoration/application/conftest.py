from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterator

import pytest

from identity_restoration.application.ports.artifact_sink import PersistedArtifact
from identity_restoration.application.ports.concurrency import Lease
from identity_restoration.application.ports.ledger import LedgerEntry
from identity_restoration.application.registry.restorer_registry import RestorerRegistry
from identity_restoration.application.use_cases.restore_face_crop import RestoreFaceCropUseCase
from identity_restoration.domain.entities import A2Authority
from identity_restoration.infrastructure.restorers.mock_restorer import MockIdentityRestorer


class FakeClock:
    def __init__(self) -> None:
        self._t = 0.0

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        self._t += 1.0
        return self._t


@dataclass
class FakeA2Repository:
    sha256: str
    path: str = "fake/a2.png"
    data: bytes = b"a2-bytes"

    def load(self) -> A2Authority:
        return A2Authority(image_bytes=self.data, sha256=self.sha256)


@dataclass
class FakeArtifactSink:
    written: dict[str, bytes] = field(default_factory=dict)

    def write_atomic(self, key: str, data: bytes) -> PersistedArtifact:
        self.written[key] = data
        import hashlib
        return PersistedArtifact(path=f"/fake/{key}", sha256=hashlib.sha256(data).hexdigest())


@dataclass
class FakeLedger:
    entries: list[LedgerEntry] = field(default_factory=list)

    def append(self, entry: LedgerEntry) -> None:
        self.entries.append(entry)


@dataclass
class FakeLease:
    acquired_count: int = 0
    released_count: int = 0
    raise_on_acquire: bool = False

    @contextmanager
    def acquire(self, key: str, ttl_seconds: int) -> Iterator[Lease]:
        if self.raise_on_acquire:
            raise RuntimeError("lease unavailable")
        self.acquired_count += 1
        try:
            yield Lease(key=key, holder="fake")
        finally:
            self.released_count += 1


class ExplodingRestorer:
    """A restorer whose .restore() always raises — used to prove the lease is
    released even when the single provider call blows up. Raises
    RestorationError, matching the Port's own obligation that adapters never
    raise a raw library exception."""

    restorer_id = "mock"
    call_count = 0

    def restore(self, request):
        from identity_restoration.domain.errors import RestorationError
        ExplodingRestorer.call_count += 1
        raise RestorationError("ERR_GW_WORKER_TIMEOUT", "boom", retryable=True)

    def describe(self):
        from identity_restoration.application.ports.identity_restorer import RestorerDescriptor
        return RestorerDescriptor(restorer_id="mock", workflow_id=None, workflow_sha256=None)


class CountingMockRestorer(MockIdentityRestorer):
    call_count: int = 0

    def restore(self, request):
        type(self).call_count += 1
        return super().restore(request)


@pytest.fixture
def fake_ports():
    return {
        "clock": FakeClock(),
        "sink": FakeArtifactSink(),
        "ledger": FakeLedger(),
    }


@pytest.fixture
def build_use_case():
    def _build(*, a2_sha256: str, restorer=None, lease=None, qc=None, health=None, face_qc_min=90.0):
        restorer = restorer or MockIdentityRestorer()
        registry = RestorerRegistry(restorers={"mock": restorer}, default_id="mock")
        return RestoreFaceCropUseCase(
            registry=registry,
            a2_authority=FakeA2Repository(sha256=a2_sha256),
            artifact_sink=FakeArtifactSink(),
            ledger=FakeLedger(),
            lease=lease or FakeLease(),
            clock=FakeClock(),
            qc=qc,
            health=health,
            face_qc_min=face_qc_min,
        )

    return _build
