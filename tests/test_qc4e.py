import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4e-local-search/qc4e-report.json"
HISTORICAL = ROOT / "data/identity_restoration_runs/gw-p0-t2-20260819-local-rerun/artifacts/restored_crop.png"


def test_qc4e_bounded_matrix_and_locked_authority():
    report = json.loads(REPORT.read_text())
    assert len(report["candidates"]) == 8
    assert report["base_sha256"] == "bb031e7adfcc0c7d79544c3edb932eebafc1f797a59881415e57addc584d26a0"
    assert report["a2_sha256"] == "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d"
    assert report["workflow_sha256"] == "b232b18d498f9a0064707a83aeebb36306fda147ac50d757a27721267c9f3e25"
    assert {item["parameter_set"]["pulid_weight"] for item in report["candidates"]} == {0.65, 0.7, 0.8, 0.9, 1.0}
    assert {item["parameter_set"]["denoise"] for item in report["candidates"]} == {0.5, 0.6, 0.7, 0.8}


def test_qc4e_all_candidates_pass_hard_gates_but_missing_validator_is_not_pass():
    report = json.loads(REPORT.read_text())
    for item in report["candidates"]:
        assert item["byte_difference_status"] == "PASS"
        assert item["pixel_lock_status"] == "PASS"
        assert item["detector_count"] == 1
        assert item["geometry_score"] >= 92
        assert item["identity_score"] is None
        assert item["eyes_brows_score"] is None
        assert item["eligibility"] == "REJECTED"
        assert "GEMINI_API_KEY" in item["rejection_reason"]


def test_qc4e_historical_artifact_unchanged():
    report = json.loads(REPORT.read_text())
    assert report["canonical_historical_artifacts_unchanged"] is True
    assert hashlib.sha256(HISTORICAL.read_bytes()).hexdigest() == "8a347eceb1d481234a97905eb1fc3a5c26809f9823614b0f9175b3b32f272f3e"
