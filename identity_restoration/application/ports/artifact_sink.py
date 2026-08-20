from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PersistedArtifact:
    path: str
    sha256: str


class ArtifactSinkPort(Protocol):
    def write_atomic(self, key: str, data: bytes) -> PersistedArtifact:
        """Write tmp -> fsync -> rename. Never expose a half-written file."""
        ...
