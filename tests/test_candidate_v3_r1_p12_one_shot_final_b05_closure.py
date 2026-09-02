from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_candidate_v3_r1_p12_one_shot_final_b05_closure.py"


def test_p12_locks_rollback_and_one_steps_change() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'CONTRACT_ID = "candidate-v3-r1-p12-B05-steps-021-v1"' in source
    assert 'OUTPUT_ARTIFACT_ID = "candidate-v3-r1-p12-B05-face-detail-steps-021-v1"' in source
    assert 'RestorationParams(denoise=0.35, steps=21, cfg=6.0' in source
    assert '"selectedParameter": "steps"' in source
    assert '"parameterChanges": 1' in source


def test_p12_preserves_existing_worker_and_quality_boundaries() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "WINDOWS_WORKER_RUNBOOK.md" in source
    assert "ComfyUiCandidateV3Adapter" in source
    assert "Tailscale HTTPS existing approved remote ComfyUI transport" in source
    assert '"boundary": "9/9 PASS"' in source
    assert '"scenarioGlobal": "9/9 PASS"' in source
    assert '"featureFlag": "OFF"' in source


def test_p12_provider_is_after_single_artifact_lineage_gate() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert source.index('if local_gate:') < source.index('validate_face(')
    assert '"maxProviderCalls": 1' in source
    assert '"maxGpuJobs": 1' in source
