from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_candidate_v3_r1_p13_resume_from_t4.py"


def test_t4_reuses_immutable_artifact_without_gpu_or_remediation() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'EXPECTED_ARTIFACT_SHA = "ce58f0ac97a74bc07eccfba9d8c96584ff38eafd5a0a53e14fb84d363a873e40"' in source
    assert '"gpuJobs": 0' in source
    assert '"artifactsCreated": 0' in source
    assert '"parameterChanges": 0' in source


def test_t4_uses_one_provider_call_after_credential_and_preflight_gates() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"maxProviderCalls": 1' in source
    assert '"maxProviderRetries": 0' in source
    assert source.index("if preflight_pass:") < source.index("validate_face(")
    assert "secretExposed" in source


def test_t4_preserves_production_safety() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"featureFlag": "OFF"' in source
    assert '"productionPromotion": "NO"' in source
    assert '"architectureChanged": False' in source
