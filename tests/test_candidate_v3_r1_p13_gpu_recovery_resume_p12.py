from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_candidate_v3_r1_p13_gpu_recovery_resume_p12.py"


def test_p13_reuses_frozen_p12_contract_without_parameter_selection() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'CONTRACT_ID = "candidate-v3-r1-p12-B05-steps-021-v1"' in source
    assert 'OUTPUT_ARTIFACT_ID = "candidate-v3-r1-p12-B05-face-detail-steps-021-v1"' in source
    assert 'RestorationParams(denoise=0.35, steps=21, cfg=6.0' in source
    assert '"parameterChangesRequired": False' in source
    assert '"maxParameterChanges": 0' in source


def test_p13_has_single_gpu_and_provider_gates() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "Tailscale HTTPS existing approved remote ComfyUI transport" in source
    assert '"maxGpuJobs": 1' in source
    assert '"maxProviderCalls": 1' in source
    assert '"maxProviderRetries": 0' in source
    assert source.index('if lineage["status"] == "PASS"') < source.index("validate_face(")


def test_p13_preserves_quality_and_production_boundaries() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"boundary": "9/9 PASS"' in source
    assert '"scenarioGlobal": "9/9 PASS"' in source
    assert '"featureFlag": "OFF"' in source
    assert '"productionPromotion": "NO"' in source
    assert '"architectureChanged": False' in source
