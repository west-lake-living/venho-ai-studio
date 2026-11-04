from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from growth_engine.domain.media.asset import _validate_sha256


class QcDecision(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"


@dataclass(frozen=True)
class QcReport:
    id: str
    variant_id: str
    caption_hash: str
    ruleset_hash: str
    fact_snapshot_hash: str
    decision: QcDecision
    coverage_gaps: tuple[str, ...]
    result_json: str
    created_at_ms: int

    def __post_init__(self) -> None:
        for name in ("id", "variant_id", "result_json"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        for name in ("caption_hash", "ruleset_hash", "fact_snapshot_hash"):
            _validate_sha256(getattr(self, name), name)
        if type(self.created_at_ms) is not int:
            raise ValueError("created_at_ms must be integer epoch milliseconds")
