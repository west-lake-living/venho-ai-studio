from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/run_candidate_v3_r1_p5_r3_provider_recovery_recheck.py"


def test_r3_recheck_is_one_call_without_bulk_or_retry() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"maxProviderCalls": 1' in source
    assert '"maxRetries": 0' in source
    assert '"GEMINI_MAX_TRANSPORT_ATTEMPTS"] = "1"' in source
    assert '"VALIDATOR_MAX_NEW_CALLS"] = "1"' in source
    assert '"bulkEvaluationsAuthorized": False' in source
    assert "run_candidate_v3_r1_p5_r2_provider_recovery_recheck.py" in source


def test_r3_identity_and_fail_closed_action_are_explicit() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "R1-P5-R3-PROVIDER-RECOVERY-RECHECK" in source
    assert '"KEEP_PROVIDER_HOLD_ACTIVE"' in source
    assert '"AUTHORITATIVE_EVALUATION_RESUME_REQUIRES_SEPARATE_AUTHORIZATION"' in source
