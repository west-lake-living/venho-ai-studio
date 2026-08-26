from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from identity_restoration.application.use_cases.validate_restoration_artifact import (
    ValidateRestorationArtifactCommand,
    ValidateRestorationArtifactUseCase,
)
from identity_restoration.domain.policies.promotion import QcResult


class CountingQc:
    provider = "mock"
    samples = 3

    def __init__(self, *, fail: bool = False):
        self.calls = 0
        self.fail = fail

    def validate(self, composite_path: str, a2_path: str) -> QcResult:
        self.calls += 1
        assert Path(composite_path).is_file()
        assert Path(a2_path).is_file()
        if self.fail:
            raise ValueError("validator fixture failed")
        return QcResult(
            face_score=88.5,
            all_validators_approved=False,
            kill_switch_triggered=False,
            source_authority={
                "faceScore": 88.5,
                "verdict": "revise",
                "killSwitchTriggered": False,
                "binaryGates": [],
                "provider": "mock",
                "model": "mock",
                "samples": 3,
                "authority": "non-authoritative",
                "qualityAcceptanceEligible": False,
            },
        )


def _command(tmp_path: Path) -> tuple[ValidateRestorationArtifactCommand, Path]:
    attempt = "run-1-attempt-1"
    artifact = tmp_path / "run-1" / attempt / "composite.png"
    artifact.parent.mkdir(parents=True)
    Image.new("RGB", (8, 8), "white").save(artifact)
    a2 = tmp_path / "A2.png"
    Image.new("RGB", (8, 8), "white").save(a2)
    return ValidateRestorationArtifactCommand("run-1", attempt, str(artifact), str(a2), attempt), artifact


def test_existing_artifact_qc_has_no_restorer_path_and_preserves_bytes(tmp_path: Path):
    command, artifact = _command(tmp_path)
    before = artifact.read_bytes()
    qc = CountingQc()

    result = ValidateRestorationArtifactUseCase(qc=qc).execute(command)

    assert result.status == "QC_VALIDATED"
    assert result.run_id == command.run_id
    assert result.attempt_id == command.attempt_id
    assert result.qc == {
        "faceScore": 88.5,
        "allValidatorsApproved": False,
        "killSwitchTriggered": False,
        "sourceAuthority": {
            "faceScore": 88.5,
            "verdict": "revise",
            "killSwitchTriggered": False,
            "binaryGates": [],
            "provider": "mock",
            "model": "mock",
            "samples": 3,
            "authority": "non-authoritative",
            "qualityAcceptanceEligible": False,
        },
        "qualityAcceptanceEligible": False,
    }
    assert qc.calls == 1
    assert artifact.read_bytes() == before


def test_existing_artifact_qc_fails_closed_on_missing_artifact(tmp_path: Path):
    command, _ = _command(tmp_path)
    missing = ValidateRestorationArtifactCommand(
        command.run_id, command.attempt_id, str(tmp_path / "missing.png"), command.a2_path, command.artifact_attempt_id
    )
    qc = CountingQc()

    result = ValidateRestorationArtifactUseCase(qc=qc).execute(missing)

    assert result.status == "QC_FAILED"
    assert result.error and result.error["code"] == "ERR_GW_QC_ARTIFACT_MISSING"
    assert qc.calls == 0


def test_existing_artifact_qc_rejects_attempt_ownership_mismatch(tmp_path: Path):
    command, _ = _command(tmp_path)
    mismatched = ValidateRestorationArtifactCommand(
        command.run_id, command.attempt_id, command.composite_path, command.a2_path, "other-attempt"
    )
    qc = CountingQc()

    result = ValidateRestorationArtifactUseCase(qc=qc).execute(mismatched)

    assert result.status == "QC_FAILED"
    assert result.error and result.error["code"] == "ERR_GW_QC_OWNERSHIP_MISMATCH"
    assert qc.calls == 0


def test_existing_artifact_qc_sanitizes_gateway_failure(tmp_path: Path):
    command, _ = _command(tmp_path)
    result = ValidateRestorationArtifactUseCase(qc=CountingQc(fail=True)).execute(command)

    assert result.status == "QC_FAILED"
    assert result.error and result.error["code"] == "ERR_GW_QC_VALIDATION"
