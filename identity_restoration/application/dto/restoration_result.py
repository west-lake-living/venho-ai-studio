from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from ...domain.errors import ErrorCode
from ...domain.policies.pixel_preservation import PixelLockReport

Status = Literal["FULL_GATE_PASS", "NEEDS_REVIEW", "REJECTED", "FAILED", "CANCELLED"]


@dataclass(frozen=True)
class RestorationErrorDetail:
    code: ErrorCode
    message: str
    retryable: bool


@dataclass(frozen=True)
class RestorationResult:
    """Mirrors contracts/restoration_result.schema.json (contractVersion 1.0)."""

    run_id: str
    attempt_id: str
    status: Status
    restored_crop_path: str | None = None
    composite_path: str | None = None
    pixel_lock: PixelLockReport | None = None
    qc: dict[str, Any] | None = None
    lineage: dict[str, Any] = field(default_factory=dict)
    error: RestorationErrorDetail | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "contractVersion": "1.0",
            "runId": self.run_id,
            "attemptId": self.attempt_id,
            "status": self.status,
            "restoredCropPath": self.restored_crop_path,
            "compositePath": self.composite_path,
            "pixelLock": (
                {"passed": self.pixel_lock.passed, "mutatedPixelCount": self.pixel_lock.mutated_pixel_count}
                if self.pixel_lock is not None
                else None
            ),
            "qc": self.qc,
            "lineage": self.lineage,
            "error": (
                {"code": self.error.code, "message": self.error.message, "retryable": self.error.retryable}
                if self.error is not None
                else None
            ),
        }
