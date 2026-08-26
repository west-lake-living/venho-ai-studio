from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...application.ports.qc_gateway import QcGatewayPort
from ...domain.errors import RestorationError


@dataclass(frozen=True)
class ValidateRestorationArtifactCommand:
    """Application-level request for QC of an already completed artifact."""

    run_id: str
    attempt_id: str
    composite_path: str
    a2_path: str
    artifact_attempt_id: str


@dataclass(frozen=True)
class ValidateRestorationArtifactResult:
    run_id: str
    attempt_id: str
    status: str
    qc: dict[str, object] | None = None
    samples: int | None = None
    provider: str | None = None
    error: dict[str, object] | None = None

    def to_json_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "contractVersion": "1.0",
            "runId": self.run_id,
            "attemptId": self.attempt_id,
            "status": self.status,
            "qc": self.qc,
        }
        if self.samples is not None:
            result["samples"] = self.samples
        if self.provider is not None:
            result["provider"] = self.provider
        if self.error is not None:
            result["error"] = self.error
        return result


class ValidateRestorationArtifactUseCase:
    """Validate an existing composite without any restoration dependency."""

    def __init__(self, *, qc: QcGatewayPort | None) -> None:
        self._qc = qc

    def execute(self, command: ValidateRestorationArtifactCommand) -> ValidateRestorationArtifactResult:
        try:
            self._validate_command(command)
            if self._qc is None:
                raise RestorationError("ERR_GW_QC_NOT_CONFIGURED", "authoritative QC gateway is not configured", False)
            report = self._qc.validate(command.composite_path, command.a2_path)
            qc = {
                "faceScore": report.face_score,
                "allValidatorsApproved": report.all_validators_approved,
                "killSwitchTriggered": report.kill_switch_triggered,
            }
            if report.source_authority is not None:
                qc["sourceAuthority"] = report.source_authority
                qc["qualityAcceptanceEligible"] = report.source_authority.get(
                    "qualityAcceptanceEligible", False
                )
            return ValidateRestorationArtifactResult(
                run_id=command.run_id,
                attempt_id=command.attempt_id,
                status="QC_VALIDATED",
                qc=qc,
                samples=getattr(self._qc, "samples", None),
                provider=getattr(self._qc, "provider", None),
            )
        except RestorationError as error:
            return ValidateRestorationArtifactResult(
                run_id=command.run_id,
                attempt_id=command.attempt_id,
                status="QC_FAILED",
                error={"code": error.code, "message": error.message, "retryable": error.retryable},
            )
        except Exception:
            return ValidateRestorationArtifactResult(
                run_id=command.run_id,
                attempt_id=command.attempt_id,
                status="QC_FAILED",
                error={
                    "code": "ERR_GW_QC_VALIDATION",
                    "message": "authoritative QC validation failed",
                    "retryable": False,
                },
            )

    @staticmethod
    def _validate_command(command: ValidateRestorationArtifactCommand) -> None:
        if not _valid_id(command.run_id) or not _valid_id(command.attempt_id):
            raise RestorationError("ERR_GW_QC_CONTRACT_INVALID", "run_id and attempt_id are invalid", False)
        if command.artifact_attempt_id != command.attempt_id:
            raise RestorationError("ERR_GW_QC_OWNERSHIP_MISMATCH", "artifact attempt ownership mismatch", False)
        composite = Path(command.composite_path)
        a2 = Path(command.a2_path)
        if not composite.is_file() or not composite.stat().st_size:
            raise RestorationError("ERR_GW_QC_ARTIFACT_MISSING", "completed composite artifact is missing", False)
        if not a2.is_file() or not a2.stat().st_size:
            raise RestorationError("ERR_GW_QC_A2_MISSING", "authoritative A2 artifact is missing", False)


def _valid_id(value: str) -> bool:
    return isinstance(value, str) and 1 < len(value) <= 128 and all(
        char.isalnum() or char in "_-" for char in value
    )
