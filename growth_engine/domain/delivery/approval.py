from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ApprovalType(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REVOKE = "REVOKE"


@dataclass(frozen=True)
class ApprovalDecision:
    id: str
    revision_id: str
    payload_hash: str
    decision: ApprovalType
    actor_id: str
    created_at_ms: int
    reason: str | None = None
    revokes_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("id", "revision_id", "actor_id"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")
        if len(self.payload_hash) != 64 or any(
            char not in "0123456789abcdefABCDEF" for char in self.payload_hash
        ):
            raise ValueError("payload_hash must be a 64-character SHA-256 hex digest")
        if type(self.created_at_ms) is not int:
            raise ValueError("created_at_ms must be an integer")
        if not isinstance(self.decision, ApprovalType):
            raise ValueError("decision must be APPROVE, REJECT, or REVOKE")
        if self.decision is ApprovalType.REVOKE and not (self.revokes_id or "").strip():
            raise ValueError("REVOKE requires revokes_id")
