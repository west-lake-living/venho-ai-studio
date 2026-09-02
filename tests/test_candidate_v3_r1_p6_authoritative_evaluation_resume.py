from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/run_candidate_v3_r1_p6_authoritative_evaluation_resume.py"


def test_r1_p6_is_sequential_and_bounded_to_18_cases() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"maxProviderCalls": 18' in source
    assert '"VALIDATOR_MAX_NEW_CALLS"] = "18"' in source
    assert '"FACE_LOCAL", number' in source
    assert '"SCENARIO_GLOBAL", number' in source
    assert '"stability_gate.json"' in source
    assert '"executionOrder": ["offline_preflight", "FACE_LOCAL", "stability_gate", "SCENARIO_GLOBAL", "quality_disposition"]' in source


def test_r1_p6_requires_separate_authorization_and_preserves_safety() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "AUTHORITATIVE_EVALUATION_RESUME_AUTHORIZED" in source
    assert '"PRODUCTION_PROMOTION": "NO"' not in source or '"productionPromotion": "NO"' in source
    assert '"featureFlag": "OFF"' in source
    assert '"gpuJobs": 0' in source
    assert '"nanoCalls": 0' in source
    assert '"alternativeProviderCalls": 0' in source
