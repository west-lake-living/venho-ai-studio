from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/run_candidate_v3_r1_p7_r1_targeted_authoritative_recheck.py"


def test_r1_p7_r1_is_bounded_to_the_five_authorized_cases():
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'FACE_CASES = ("B05", "B07")' in source
    assert 'SCENARIO_CASES = ("B05", "B06", "B09")' in source
    assert 'os.environ["VALIDATOR_MAX_NEW_CALLS"] = "5"' in source
    assert 'os.environ["GEMINI_MAX_TRANSPORT_ATTEMPTS"] = "1"' in source
    assert '"maxProviderCalls": 5' in source


def test_r1_p7_r1_preserves_production_safety_and_fail_closed_states():
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"retries": 0' in source
    assert '"gpuJobs": 0' in source
    assert '"nanoCalls": 0' in source
    assert '"alternativeProviderCalls": 0' in source
    assert '"featureFlag": "OFF"' in source
    assert '"productionPromotion": "NO"' in source
    assert '"PROVIDER_BLOCKED_PARTIAL"' in source
