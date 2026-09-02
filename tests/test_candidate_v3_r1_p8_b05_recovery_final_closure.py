from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/run_candidate_v3_r1_p8_b05_recovery_final_closure.py"


def test_p8_detects_incomplete_r2_artifact_contract_and_stops_before_provider():
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"REMEDIATION_CONTRACT_INCOMPLETE"' in source
    assert '"providerCalls": 0' in source
    assert '"t3": "NOT_EXECUTED"' in source
    assert '"t5": "NOT_EXECUTED"' in source
    assert '"expectedOutputPath": remediation.get("artifact")' in source


def test_p8_enforces_authority_scope_and_production_safety():
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"maxB05AuthoritativeProviderCalls": 2' in source
    assert '"retries": 0' in source
    assert '"gpuJobs": 0' in source
    assert '"nanoCalls": 0' in source
    assert '"alternativeProviderCalls": 0' in source
    assert '"featureFlag": "OFF"' in source
    assert '"productionPromotion": "NO"' in source
    assert '"architectureChanged": False' in source
