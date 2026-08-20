from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from validator_studio.face_validator import validate_face

from ...domain.policies.promotion import QcResult

# WRAPS the existing Validator Studio (validator_studio/face_validator.py)
# unchanged. Behaviour, thresholds and the samples=3 non-determinism fix
# (2026-07-17) all live there and are not touched here — this class only
# reshapes ValidationReport into the domain's QcResult (v2.0 PHẦN 6, PHẦN 7.2:
# "KHÔNG đổi ngưỡng validator").
#
# provider defaults to "mock" so wiring this gateway into a use case never
# spends money by accident; a live run must pass provider explicitly.


@dataclass
class ValidatorStudioQcGateway:
    project: str = "venho_hotel"
    subject: str = "linh_an"
    provider: str = "mock"
    samples: int = 3

    def validate(self, composite_path: str, a2_path: str) -> QcResult:
        report = validate_face(
            project=self.project,
            subject=self.subject,
            image_path=Path(composite_path),
            provider=self.provider,
            reference_image_paths=[Path(a2_path)],
            samples=self.samples,
        )
        return QcResult(
            face_score=float(report.overall_score),
            all_validators_approved=report.verdict == "APPROVED",
            kill_switch_triggered=bool(report.kill_switch),
        )
