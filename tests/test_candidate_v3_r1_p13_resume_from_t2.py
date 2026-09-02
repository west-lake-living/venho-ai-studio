from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_candidate_v3_r1_p13_resume_from_t2.py"


def test_resume_starts_at_t2_and_keeps_p13_contract() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"resumePoint": "T2"' in source
    assert '"t0": "NOT_RERUN"' in source
    assert 'RestorationParams(denoise=0.35, steps=21, cfg=6.0' in source
    assert '"parameterChanges": 0' in source


def test_resume_keeps_single_job_and_provider_limits() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"maxGpuJobs": 1' in source
    assert '"maxProviderCalls": 1' in source
    assert '"maxProviderRetries": 0' in source
    assert source.index('if lineage["status"] == "PASS"') < source.index("validate_face(")


def test_resume_preserves_production_boundaries() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"boundary": "9/9 PASS"' in source
    assert '"scenarioGlobal": "9/9 PASS"' in source
    assert '"featureFlag": "OFF"' in source
    assert '"productionPromotion": "NO"' in source
    assert '"architectureChanged": False' in source
