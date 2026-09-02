from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_candidate_v3_r1_p11_r1_gpu_recovery_final_resume.py"


def test_r1_p11_r1_locks_single_gpu_and_provider_budget() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'CONTRACT_ID = "candidate-v3-r1-p11-B05-denoise-040-v1"' in source
    assert 'OUTPUT_ARTIFACT_ID = "candidate-v3-r1-p11-B05-face-detail-denoise-040-v1"' in source
    assert 'RestorationParams(denoise=0.40, steps=20, cfg=6.0' in source
    assert 'os.environ["GEMINI_MAX_TRANSPORT_ATTEMPTS"] = "1"' in source
    assert '"maxGpuJobs": 1' in source
    assert '"maxProviderCalls": 1' in source


def test_r1_p11_r1_uses_documented_remote_worker_and_existing_adapter() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "WINDOWS_WORKER_RUNBOOK.md" in source
    assert "ComfyUiCandidateV3Adapter" in source
    assert "ComfyUIHttpClient(base_url=endpoint" in source
    assert "127.0.0.1:8188" in source
    assert "Tailscale HTTPS existing approved remote ComfyUI transport" in source


def test_r1_p11_r1_provider_is_after_lineage_gate() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert source.index('if local_gate:') < source.index('validate_face(')
    assert 'provider_calls = 1' in source
    assert 'provider_calls = 0' in source
