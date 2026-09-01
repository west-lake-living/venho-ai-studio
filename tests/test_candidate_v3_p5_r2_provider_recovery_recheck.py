from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/run_candidate_v3_r1_p5_r2_provider_recovery_recheck.py"


def test_r2_recheck_is_one_call_and_reuses_authoritative_probe_path() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"maxProviderCalls": 1' in source
    assert '"maxRetries": 0' in source
    assert '"GEMINI_MAX_TRANSPORT_ATTEMPTS"] = "1"' in source
    assert '"VALIDATOR_MAX_NEW_CALLS"] = "1"' in source
    assert '"bulkEvaluationsAuthorized": False' in source
    assert 'run_candidate_v3_r1_p5_r1_provider_recovery_probe.py' in source


def test_r2_evidence_identity_and_hold_actions_are_explicit() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "R1-P5-R2-PROVIDER-RECOVERY-RECHECK" in source
    assert '"KEEP_PROVIDER_HOLD_ACTIVE"' in source
    assert '"AUTHORITATIVE_EVALUATION_RESUME_REQUIRES_SEPARATE_AUTHORIZATION"' in source
