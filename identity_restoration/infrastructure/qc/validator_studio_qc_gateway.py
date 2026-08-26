from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from validator_studio.face_validator import validate_face
from validator_studio.schemas.validation_base import Recommendation

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
    evidence_sink: Callable[[dict[str, Any]], None] | None = None
    validation_cycle_id: str | None = None
    attempt_id: str | None = None

    def validate(self, composite_path: str, a2_path: str) -> QcResult:
        report = validate_face(
            project=self.project,
            subject=self.subject,
            image_path=Path(composite_path),
            provider=self.provider,
            reference_image_paths=[Path(a2_path)],
            samples=self.samples,
            raw_response_sink=self.evidence_sink,
            validation_cycle_id=self.validation_cycle_id,
            attempt_id=self.attempt_id,
        )
        raw_observation = report.raw_observation if isinstance(report.raw_observation, dict) else {}
        gates = raw_observation.get("gates", [])
        weighted_scores = raw_observation.get("weighted_scores")
        source_provider = report.observer.provider
        source_authority: dict[str, object] = {
            "faceScore": float(report.overall_score),
            "verdict": report.verdict.value,
            "killSwitchTriggered": report.kill_switch.triggered,
            "binaryGates": gates if isinstance(gates, list) else [],
            "provider": source_provider,
            "model": report.observer.model,
            "samples": report.observer.samples,
            "authority": "authoritative" if source_provider == "gemini" else "non-authoritative",
            "qualityAcceptanceEligible": source_provider == "gemini",
            "aggregateIdentity": {
                "contractVersion": report.contract_version,
                "validationType": report.validation_type,
                "artifactHash": report.artifact_ref.hash,
            },
        }
        if isinstance(weighted_scores, dict):
            source_authority["weightedScores"] = weighted_scores
        return QcResult(
            face_score=float(report.overall_score),
            all_validators_approved=report.verdict == Recommendation.APPROVE,
            kill_switch_triggered=report.kill_switch.triggered,
            source_authority=source_authority,
        )
