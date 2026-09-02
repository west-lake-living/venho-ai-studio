from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/run_candidate_v3_r1_p11_human_parameter_final_closure.py"


def source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_human_decision_is_explicit_and_scoped():
    text = source()
    assert '"parameter": "denoise"' in text
    assert '"authorizedDelta": 0.05' in text
    assert '"scope": "B05_ONLY"' in text


def test_cfg_and_steps_are_unchanged():
    text = source()
    assert '"cfgChange": 0' in text
    assert '"stepsChange": 0' in text
    assert '"cfgUnchanged": True' in text
    assert '"stepsUnchanged": True' in text


def test_current_parameter_is_read_from_authoritative_state():
    text = source()
    assert 'bound["denoise"]' in text
    assert '"currentDenoise": current_denoise' in text


def test_approved_range_and_clamp_are_enforced():
    text = source()
    assert '"min": 0.05, "max": 0.75' in text
    assert 'final_denoise = min(requested_denoise, maximum)' in text
    assert '"clamped": clamped' in text


def test_expected_final_denoise_is_zero_point_four():
    text = source()
    assert "requested_denoise = round(current_denoise + 0.05, 2)" in text
    assert 'if current_denoise != 0.35' in text


def test_one_artifact_and_one_gpu_job_limit():
    text = source()
    assert '"maxGpuJobs": 1' in text
    assert '"maxArtifacts": 1' in text
    assert '"artifactCount": 0' in text


def test_one_provider_call_and_zero_retries():
    text = source()
    assert '"maxProviderCalls": 1' in text
    assert '"providerCalls": 0' in text
    assert '"retries": 0' in text


def test_workflow_pin_is_fixed():
    text = source()
    assert "face_restore_win_sd15_ipadapter_v3" in text
    assert '"workflowHash"' in text


def test_a2_reference_is_fixed():
    text = source()
    assert '"type": "A2"' in text
    assert '"referenceBinding"' in text


def test_output_identity_is_deterministic():
    text = source()
    assert "OUTPUT_ARTIFACT_ID = \"candidate-v3-r1-p11-B05-face-detail-denoise-040-v1\"" in text
    assert '"outputPath": str(output_path.relative_to(ROOT))' in text
    assert '"outputManifest": str(output_manifest.relative_to(ROOT))' in text


def test_passing_baseline_is_protected():
    text = source()
    assert '"boundary": "9/9 PASS"' in text
    assert '"faceLocal": "8/9 PASS"' in text
    assert '"scenarioGlobal": "9/9 PASS"' in text
    assert '"passingCasesProtected": True' in text


def test_no_provider_call_precedes_materialization():
    text = source()
    assert '"providerCalls": 0' in text
    assert "if not start_reasons:" in text


def test_lineage_requires_contract_and_artifact():
    text = source()
    assert '"contractMatch": False' in text
    assert '"artifactExists": False' in text
    assert '"denoiseMatch": False' in text


def test_feature_flag_is_off():
    assert '"featureFlag": "OFF"' in source()


def test_promotion_is_disabled():
    assert '"productionPromotion": "NO"' in source()


def test_architecture_is_unchanged():
    assert '"architectureChanged": False' in source()
