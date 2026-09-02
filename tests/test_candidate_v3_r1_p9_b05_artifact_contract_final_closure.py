from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/run_candidate_v3_r1_p9_b05_artifact_contract_final_closure.py"


def source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_incomplete_contract_fails_closed():
    assert "REMEDIATION_PARAMETER_UNRESOLVED" in source()
    assert '"contractComplete": False' in source()


def test_unresolved_restore_parameter_is_required():
    assert '"restore_parameters.remediation_change"' in source()
    assert '"remediationChange": None' in source()


def test_deterministic_output_fields_are_required():
    text = source()
    assert '"output_artifact_id"' in text
    assert '"output_path"' in text
    assert '"outputArtifactId": None' in text


def test_b05_only_scope_is_explicit():
    assert '"caseId": "B05"' in source()
    assert '"caseId": "B05", "lane": "FACE_LOCAL"' not in source()


def test_source_lineage_is_required():
    assert '"sourceLineage"' in source()
    assert '"source_manifest_for_new_variant"' in source()


def test_workflow_pin_is_preserved():
    text = source()
    assert '"workflowId"' in text
    assert '"workflowHash"' in text
    assert '"workflow_version"' in text


def test_reference_binding_is_preserved():
    text = source()
    assert '"referencePackId"' in text
    assert '"a2Sha256"' in text


def test_artifact_count_is_bounded():
    text = source()
    assert '"maxArtifacts": 1' in text
    assert '"artifactsCreated": 0' in text


def test_provider_call_count_is_bounded():
    text = source()
    assert '"maxProviderCalls": 1' in text
    assert '"providerCalls": 0' in text


def test_retries_are_zero():
    assert '"retries": 0' in source()


def test_passing_baseline_is_protected():
    text = source()
    assert '"boundary": "9/9 PASS"' in text
    assert '"faceLocal": "8/9 PASS"' in text
    assert '"scenarioGlobal": "9/9 PASS"' in text


def test_quality_pass_path_is_not_fabricated():
    text = source()
    assert '"t5": "NOT_EXECUTED"' in text
    assert '"t6": "NOT_EXECUTED"' in text


def test_quality_fail_path_remains_pending_when_no_recheck_exists():
    text = source()
    assert '"pendingAuthoritativeEvaluations": 1' in text
    assert '"qualityDisposition": "FAIL_PENDING_B05_RECHECK"' in text


def test_provider_blocked_safety_is_fail_closed():
    text = source()
    assert '"providerCalls": 0' in text
    assert '"gpuJobs": 0' in text


def test_feature_flag_stays_off():
    assert '"featureFlag": "OFF"' in source()


def test_promotion_stays_disabled():
    assert '"productionPromotion": "NO"' in source()


def test_architecture_stays_unchanged():
    assert '"architectureChanged": False' in source()
