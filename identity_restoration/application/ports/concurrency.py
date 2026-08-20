from __future__ import annotations

from dataclasses import dataclass
from typing import ContextManager, Protocol


@dataclass(frozen=True)
class Lease:
    key: str
    holder: str


class ConcurrencyLeasePort(Protocol):
    def acquire(self, key: str, ttl_seconds: int) -> ContextManager[Lease]:
        """max_concurrent=1 at Phase 3-5. 6 GB VRAM cannot take two workflows
        at once; the symptom would be random, very-hard-to-diagnose OOM."""
        ...
