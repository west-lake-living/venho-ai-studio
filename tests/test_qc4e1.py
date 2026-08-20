import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4e-local-search/qc4e1/qc4e1-report.json"


def test_qc4e1_redacts_credentials_and_reuses_existing_matrix():
    report = json.loads(REPORT.read_text())
    assert report["credential"]["secret_exposed"] is False
    assert report["secret_persisted"] is False
    assert report["comfyui_rerun"] is False
    assert len(report["candidates"]) == 8
    assert report["validator"]["provider"] == "gemini"
    assert report["validator"]["samples"] == 1
    assert all("GEMINI_API_KEY=" not in REPORT.read_text() for _ in [0])


def test_qc4e1_selection_uses_hard_gates_and_face_thresholds():
    report = json.loads(REPORT.read_text())
    best = report["best_candidate"]
    assert best["candidate_id"] == "qc4e-w070-d060"
    assert best["identity_score"] >= 90
    assert best["eyes_brows_score"] >= 90
    assert best["geometry_score"] >= 92
    assert best["pixel_lock_status"] == "PASS"
    assert best["byte_difference_status"] == "PASS"
    assert best["detector_count"] == 1


def test_qc4e1_all_face_evidence_is_bound_to_candidate_hash():
    report = json.loads(REPORT.read_text())
    for candidate in report["candidates"]:
        raw = candidate["face_validator"]["raw_report"]
        assert raw["artifact_ref"]["hash"].endswith(candidate["composite_sha256"])
        assert candidate["face_validator"]["reference_sha256"] == report["credential"].get("a2_sha256", "") or candidate["face_validator"]["reference_sha256"] == "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d"
