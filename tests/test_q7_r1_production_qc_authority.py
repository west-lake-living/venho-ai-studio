from __future__ import annotations

from pathlib import Path

from PIL import Image

from identity_restoration.application.use_cases.validate_restoration_artifact import (
    ValidateRestorationArtifactCommand,
    ValidateRestorationArtifactUseCase,
)
from identity_restoration.domain.policies.pixel_preservation import PixelLockReport
from identity_restoration.domain.policies.promotion import QcResult, is_full_gate_pass
from identity_restoration.infrastructure.composition.env import RestorationEnv, read_restoration_env
from identity_restoration.infrastructure.composition.identity_restoration_module import build_qc_gateway
from identity_restoration.infrastructure.qc.validator_studio_qc_gateway import ValidatorStudioQcGateway


def test_authoritative_composition_requires_gemini_configuration():
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        artifact = Path(directory) / "composite.png"
        a2 = Path(directory) / "A2.png"
        Image.new("RGB", (4, 4), "white").save(artifact)
        Image.new("RGB", (4, 4), "white").save(a2)
        gateway = build_qc_gateway(RestorationEnv(qc_enabled=False, qc_provider="mock"), required=True)
        result = ValidateRestorationArtifactUseCase(qc=gateway).execute(
            ValidateRestorationArtifactCommand("run-1", "attempt-1", str(artifact), str(a2), "attempt-1")
        )
    assert result.status == "QC_FAILED"
    assert result.error and result.error["code"] == "QC_AUTHORITY_UNAVAILABLE"


def test_authoritative_composition_rejects_explicit_mock_provider():
    gateway = build_qc_gateway(RestorationEnv(qc_enabled=True, qc_provider="mock"), required=True)
    assert not isinstance(gateway, ValidatorStudioQcGateway)


def test_offline_mock_remains_available_when_explicitly_selected():
    gateway = build_qc_gateway(RestorationEnv(qc_enabled=True, qc_provider="mock"))
    assert isinstance(gateway, ValidatorStudioQcGateway)
    assert gateway.provider == "mock"


def test_fresh_process_reads_authoritative_qc_configuration(monkeypatch):
    monkeypatch.setenv("IDR_QC_ENABLED", "true")
    monkeypatch.setenv("IDR_QC_PROVIDER", "gemini")
    monkeypatch.setenv("IDR_QC_SAMPLES", "3")
    env = read_restoration_env()
    assert env.qc_enabled is True
    assert env.qc_provider == "gemini"
    assert env.qc_samples == 3
    gateway = build_qc_gateway(env, required=True)
    assert isinstance(gateway, ValidatorStudioQcGateway)
    assert gateway.provider == "gemini"


def test_mock_source_is_non_authoritative_and_cannot_pass_quality_gate():
    qc = QcResult(
        face_score=99,
        all_validators_approved=True,
        kill_switch_triggered=False,
        source_authority={
            "provider": "mock",
            "authority": "non-authoritative",
            "qualityAcceptanceEligible": False,
        },
    )
    pixel = PixelLockReport(passed=True, mutated_pixel_count=0, editable_region_hash="")
    assert is_full_gate_pass(qc, pixel, face_qc_min=90) is False


def test_authoritative_gateway_metadata_marks_gemini(monkeypatch):
    from validator_studio.schemas.validation_base import ArtifactRef, KillSwitch, ObserverInfo, Recommendation, ValidationReport
    import identity_restoration.infrastructure.qc.validator_studio_qc_gateway as module

    report = ValidationReport(
        project="venho_hotel", subject="linh_an", validation_type="face",
        artifact_ref=ArtifactRef(type="face", file="artifact.png"), overall_score=95,
        verdict=Recommendation.APPROVE, recommendation=Recommendation.APPROVE,
        kill_switch=KillSwitch(triggered=False),
        observer=ObserverInfo(provider="gemini", model="gemini-3.5-flash", samples=3),
    )
    monkeypatch.setattr(module, "validate_face", lambda **_: report)
    qc = ValidatorStudioQcGateway(provider="gemini", samples=3).validate("artifact.png", "A2.png")
    assert qc.source_authority and qc.source_authority["authority"] == "authoritative"
    assert qc.source_authority["qualityAcceptanceEligible"] is True


def test_validation_contract_preserves_mock_as_non_authoritative(tmp_path: Path):
    artifact = tmp_path / "composite.png"
    a2 = tmp_path / "A2.png"
    Image.new("RGB", (4, 4), "white").save(artifact)
    Image.new("RGB", (4, 4), "white").save(a2)
    class ExplicitMock:
        provider = "mock"
        samples = 1

        def validate(self, _composite: str, _a2: str) -> QcResult:
            return QcResult(88, False, False, {"provider": "mock", "qualityAcceptanceEligible": False})

    result = ValidateRestorationArtifactUseCase(qc=ExplicitMock()).execute(
        ValidateRestorationArtifactCommand("run-1", "attempt-1", str(artifact), str(a2), "attempt-1")
    )
    assert result.status == "QC_VALIDATED"
    assert result.qc and result.qc["qualityAcceptanceEligible"] is False
