from identity_restoration.infrastructure.composition.env import RestorationEnv
from identity_restoration.infrastructure.composition.identity_restoration_module import build_identity_restoration_module, build_qc_gateway
from identity_restoration.domain.policies.promotion import QcResult
from identity_restoration.infrastructure.qc.validator_studio_qc_gateway import ValidatorStudioQcGateway
from validator_studio.schemas.validation_base import ArtifactRef, KillSwitch, Recommendation, ValidationReport


def test_composition_root_wires_existing_validator_gateway_when_enabled():
    gateway = build_qc_gateway(RestorationEnv(qc_enabled=True, qc_provider="mock", qc_samples=3))

    assert isinstance(gateway, ValidatorStudioQcGateway)
    assert gateway.provider == "mock"
    assert gateway.samples == 3


def test_composition_root_keeps_qc_opt_in_for_legacy_runs():
    assert build_qc_gateway(RestorationEnv(qc_enabled=False)) is None


def test_production_module_injects_gateway_through_use_case(tmp_path):
    module = build_identity_restoration_module(
        RestorationEnv(qc_enabled=True, qc_provider="mock", qc_samples=3),
        repo_root=tmp_path,
    )

    assert isinstance(module.use_case._qc, ValidatorStudioQcGateway)


def _report(*, verdict: Recommendation, kill_switch_triggered: bool) -> ValidationReport:
    return ValidationReport(
        project="venho_hotel",
        subject="linh_an",
        validation_type="face",
        artifact_ref=ArtifactRef(type="face", file="attempt-2/composite.png"),
        overall_score=95.4,
        verdict=verdict,
        recommendation=verdict,
        kill_switch=KillSwitch(triggered=kill_switch_triggered),
    )


def _projected_qc(monkeypatch, report: ValidationReport) -> QcResult:
    import identity_restoration.infrastructure.qc.validator_studio_qc_gateway as module

    monkeypatch.setattr(module, "validate_face", lambda **_: report)
    return ValidatorStudioQcGateway(provider="gemini", samples=3).validate(
        "attempt-2/composite.png", "A2_Front_plate.png"
    )


def test_gateway_projects_approved_authority_without_uppercase_or_model_truthiness(monkeypatch):
    qc = _projected_qc(monkeypatch, _report(verdict=Recommendation.APPROVE, kill_switch_triggered=False))

    assert qc.face_score == 95.4
    assert qc.all_validators_approved is True
    assert qc.kill_switch_triggered is False
    assert qc.source_authority == {
        "faceScore": 95.4,
        "verdict": "approve",
        "killSwitchTriggered": False,
        "binaryGates": [],
        "provider": "mock",
        "model": "mock",
        "samples": 1,
        "authority": "non-authoritative",
        "qualityAcceptanceEligible": False,
        "aggregateIdentity": {
            "contractVersion": "1.0",
            "validationType": "face",
            "artifactHash": None,
        },
    }


def test_gateway_projects_non_approve_verdict_as_not_approved(monkeypatch):
    qc = _projected_qc(monkeypatch, _report(verdict=Recommendation.REJECT, kill_switch_triggered=False))

    assert qc.all_validators_approved is False
    assert qc.kill_switch_triggered is False


def test_gateway_projects_real_kill_switch_field_only(monkeypatch):
    qc = _projected_qc(monkeypatch, _report(verdict=Recommendation.APPROVE, kill_switch_triggered=True))

    assert qc.all_validators_approved is True
    assert qc.kill_switch_triggered is True


def test_gateway_does_not_treat_false_kill_switch_model_as_truthy(monkeypatch):
    report = _report(verdict=Recommendation.APPROVE, kill_switch_triggered=False)
    assert bool(report.kill_switch) is True

    qc = _projected_qc(monkeypatch, report)

    assert qc.kill_switch_triggered is False
