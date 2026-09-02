from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/run_candidate_v3_r1_p7_r2_r1_b05_face_local_recheck.py"
CONFIG = ROOT / "config/projects/venho_hotel/identity_restoration/r1_p7_r2_b05_face_local.yaml"


def test_r2_r1_is_single_case_and_fail_closed_without_new_remediated_artifact():
    source = SCRIPT.read_text(encoding="utf-8")
    config = CONFIG.read_text(encoding="utf-8")
    assert 'TASK_ID = "R1-P7-R2-R1-B05-FACE-LOCAL-AUTHORITATIVE-RECHECK"' in source
    assert '"R2_REMEDIATED_ARTIFACT_MISSING"' in source
    assert '"providerCalls": 0' in source
    assert '"maxProviderCalls": 1' in source
    assert "B05_FACE_LOCAL_RECHECK_AUTHORIZED" in source
    assert "r1-p7-r2-b05-face-detail-v1" in config


def test_r2_r1_preserves_scope_and_production_safety():
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"gpuJobs": 0' in source
    assert '"nanoCalls": 0' in source
    assert '"alternativeProviderCalls": 0' in source
    assert '"featureFlag": "OFF"' in source
    assert '"productionPromotion": "NO"' in source
    assert '"architectureChanged": False' in source
    assert "B07" not in source
    assert "SCENARIO_GLOBAL" not in source
