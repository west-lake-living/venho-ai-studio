from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/run_candidate_v3_r1_p10_b05_parameter_resolution_final_closure.py"


def text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_parameter_authority_matrix_exists():
    assert "parameter_authority_matrix.json" in text()


def test_current_parameters_are_pinned():
    source = text()
    assert '"denoise": 0.35' in source
    assert '"cfg": 6.0' in source
    assert '"steps": 20' in source


def test_approved_domains_are_explicit():
    source = text()
    assert '"min": 0.05' in source
    assert '"max": 0.75' in source
    assert '"min": 1.0' in source
    assert '"max": 12.0' in source


def test_missing_selection_rule_fails_closed():
    source = text()
    assert "selection_rule_found = False" in source
    assert '"HUMAN_PARAMETER_DECISION_REQUIRED"' not in source or "BLOCKED / HUMAN_PARAMETER_DECISION_REQUIRED" in source


def test_no_delta_is_selected():
    source = text()
    assert '"selectedRemediationDelta": None' in source
    assert '"selectedDelta": None' in source


def test_no_parameter_sweep_or_variant_sweep():
    source = text()
    assert '"maxArtifacts": 1' in source
    assert '"maxProviderCalls": 1' in source
    assert '"artifactsCreated": 0' in source


def test_b05_scope_is_fixed():
    assert '"caseId": "B05"' in text()


def test_workflow_is_pinned():
    source = text()
    assert "face_restore_win_sd15_ipadapter_v3" in source
    assert "workflowSha256" in source


def test_reference_and_geometry_are_preserved():
    source = text()
    assert "faceScale" in source
    assert "yaw" in source
    assert "knownBaseline" in source


def test_artifact_materialization_is_blocked():
    assert '"artifactCount": 0' in text()
    assert '"status": "NOT_EXECUTED"' in text()


def test_lineage_gate_does_not_run_without_artifact():
    source = text()
    assert '"artifactExists": False' in source
    assert '"contractMatch": False' in source


def test_provider_calls_are_zero():
    assert '"providerCalls": 0' in text()


def test_retries_are_zero():
    assert '"retries": 0' in text()


def test_passing_baseline_is_protected():
    source = text()
    assert '"boundary": "9/9 PASS"' in source
    assert '"faceLocal": "8/9 PASS"' in source
    assert '"scenarioGlobal": "9/9 PASS"' in source


def test_feature_flag_is_off():
    assert '"featureFlag": "OFF"' in text()


def test_promotion_is_disabled():
    assert '"productionPromotion": "NO"' in text()


def test_architecture_is_unchanged():
    assert '"architectureChanged": False' in text()
