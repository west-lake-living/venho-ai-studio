from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_candidate_v3_r2_b05_face_local_focused_recovery.py"


def test_r2_freezes_four_unique_untested_b05_candidates() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"id": "A", "denoise": 0.35, "cfg": 6.0, "steps": 22' in source
    assert '"id": "B", "denoise": 0.35, "cfg": 6.1, "steps": 21' in source
    assert '"id": "C", "denoise": 0.35, "cfg": 6.1, "steps": 22' in source
    assert '"id": "D", "denoise": 0.35, "cfg": 6.0, "steps": 23' in source
    assert '"notPreviouslyTested"' in source
    assert '"countWithinBudget"' in source


def test_r2_enforces_all_global_limits_and_sequential_early_stop() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"maxGpuJobs": 4' in source
    assert '"maxProviderCalls": 4' in source
    assert '"maxProviderRetries": 0' in source
    assert 'for candidate in CANDIDATES:' in source
    assert 'if result["provider"]["pass"]:' in source
    assert source.index('for candidate in CANDIDATES:') < source.index('if result["provider"]["pass"]:')


def test_r2_protects_passing_cases_and_production_state() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"boundary": "9/9 PASS"' in source
    assert '"otherFaceLocalPassingCases": "8/8 PASS"' in source
    assert '"scenarioGlobal": "9/9 PASS"' in source
    assert '"featureFlag": "OFF"' in source
    assert '"productionPromotion": "NO"' in source
    assert '"architectureChanged": False' in source


def test_r2_uses_existing_adapter_and_validator_without_alternatives() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "ComfyUiCandidateV3Adapter" in source
    assert "validate_face(" in source
    assert '"nanoCalls": 0' in source
    assert '"alternativeProviderCalls": 0' in source
    assert '"provider": "Gemini"' in source
