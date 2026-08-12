from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Mapping, Optional

from pydantic import BaseModel, Field

from .selective_repair import RETRY_CAPS
from .validators import RegionValidation, ValidationStatus, RegionalValidator


class IterationRecord(BaseModel):
    iteration: int = Field(ge=0)
    provider: str
    workflow_version: str
    seed: Optional[int] = None
    identity_score: Optional[float] = Field(default=None, ge=0, le=100)
    geometry_score: Optional[float] = Field(default=None, ge=0, le=100)
    global_score: Optional[float] = Field(default=None, ge=0, le=100)
    mask_version: str = "unknown"
    parameters: Dict[str, object] = Field(default_factory=dict)
    state: str = "INIT"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AuditTrail(BaseModel):
    job_id: str
    events: List[IterationRecord] = Field(default_factory=list)

    def append(self, record: IterationRecord) -> None:
        if self.events and record.iteration <= self.events[-1].iteration:
            raise ValueError("iteration must increase monotonically")
        self.events.append(record)

    @property
    def latest(self) -> Optional[IterationRecord]:
        return self.events[-1] if self.events else None


@dataclass
class RetryPolicy:
    caps: Dict[str, int] = field(default_factory=lambda: dict(RETRY_CAPS))
    attempts: Dict[str, int] = field(default_factory=dict)

    def allow(self, repair_type: str) -> bool:
        attempt = self.attempts.get(repair_type, 0) + 1
        default_cap = self.caps.get("region", RETRY_CAPS["region"])
        if attempt > self.caps.get(repair_type, default_cap):
            return False
        self.attempts[repair_type] = attempt
        return True


@dataclass
class CostLedger:
    """Tracks local/cloud compute without requiring a billing provider."""

    entries: List[Dict[str, object]] = field(default_factory=list)

    def record(self, *, provider: str, duration_seconds: float, cost: float = 0.0,
               job_id: Optional[str] = None) -> None:
        if duration_seconds < 0 or cost < 0:
            raise ValueError("duration_seconds and cost must be non-negative")
        self.entries.append({"provider": provider, "duration_seconds": duration_seconds,
                             "cost": cost, "job_id": job_id})

    @property
    def total_cost(self) -> float:
        return round(sum(float(item["cost"]) for item in self.entries), 6)

    @property
    def total_duration_seconds(self) -> float:
        return round(sum(float(item["duration_seconds"]) for item in self.entries), 3)

    def snapshot(self) -> Dict[str, object]:
        return {"entries": list(self.entries), "total_cost": self.total_cost,
                "total_duration_seconds": self.total_duration_seconds}


class IdempotencyStore:
    """In-memory idempotency gate; callers can replace it with a durable store."""

    def __init__(self) -> None:
        self._completed: Dict[str, object] = {}

    @staticmethod
    def key(job_id: str, payload: bytes) -> str:
        return hashlib.sha256(job_id.encode("utf-8") + b":" + payload).hexdigest()

    def get(self, key: str) -> Optional[object]:
        return self._completed.get(key)

    def put(self, key: str, result: object) -> None:
        self._completed[key] = result


class StopCondition:
    """Production stop gate: every required region must be PASS."""

    REQUIRED = ("identity", "facial_geometry", "anatomy", "outfit", "environment", "global")

    def __init__(self, *, informational_threshold: float = 90.0) -> None:
        # Anatomy/outfit/environment/global are PASS-FAIL judgements upstream and
        # reach the gate as informational scores, so they need an explicit bar.
        self.informational_threshold = informational_threshold

    def evaluate(self, scores: Mapping[str, Optional[float]], *, validator: Optional[RegionalValidator] = None) -> bool:
        validator = validator or RegionalValidator()
        results = validator.validate(scores)
        for name in self.REQUIRED:
            result = results.get(name)
            if result is None or result.status != ValidationStatus.PASS:
                return False
            score = scores.get(name)
            if score is None:
                return False
            # Regions the validator scores itself were already gated above; only
            # apply the informational bar where it has no threshold of its own.
            if result.threshold is None and score < self.informational_threshold:
                return False
        return True


def failed_regions(results: Mapping[str, RegionValidation]) -> List[str]:
    return [name for name, result in results.items() if result.status == ValidationStatus.FAIL]
