from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CandidateState(str, Enum):
    NEW = "NEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    USED = "USED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class ResearchCandidate:
    id: str
    project_id: str
    source: str
    external_key: str
    source_revision: str
    event_key: str | None
    topic_key: str
    event_start_at_ms: int | None
    event_end_at_ms: int | None
    expires_at_ms: int
    source_hash: str
    state: CandidateState

    def __post_init__(self) -> None:
        for name in ("id", "project_id", "source", "external_key", "source_revision", "topic_key"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if type(self.expires_at_ms) is not int:
            raise ValueError("expires_at_ms must be integer epoch milliseconds")
        for name in ("event_start_at_ms", "event_end_at_ms"):
            value = getattr(self, name)
            if value is not None and type(value) is not int:
                raise ValueError(f"{name} must be integer epoch milliseconds or None")
        if (
            self.event_start_at_ms is not None
            and self.event_end_at_ms is not None
            and self.event_end_at_ms < self.event_start_at_ms
        ):
            raise ValueError("event_end_at_ms must not precede event_start_at_ms")
        if len(self.source_hash) != 64 or any(
            char not in "0123456789abcdefABCDEF" for char in self.source_hash
        ):
            raise ValueError("source_hash must be a 64-character SHA-256 hex digest")

    def is_usable(self, at_ms: int) -> bool:
        return (
            type(at_ms) is int
            and self.state is CandidateState.APPROVED
            and at_ms < self.expires_at_ms
            and (self.event_end_at_ms is None or at_ms < self.event_end_at_ms)
        )
