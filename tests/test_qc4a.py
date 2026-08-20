import json
from pathlib import Path


REPORT = Path("data/identity_restoration_runs/gw-p0-t2-qc4-local-candidate/diagnostics/qc4a/qc4a-report.json")


def test_qc4a_candidate_is_bound_to_exact_existing_final_artifact():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    candidate = report["scene_candidate"]
    assert candidate["candidate_id"] == "gw-p0-t2-qc4-existing-final"
    assert candidate["metadata"]["image_regenerated"] is False
    assert report["scene_candidate_sha_consistent"] is True


def test_qc4a_missing_scene_and_global_evidence_stays_unknown_and_blocked():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert all(report["evaluators"][field]["status"] == "UNKNOWN" for field in ("anatomy", "outfit", "environment", "global_composite"))
    assert report["regional_gate"]["status"] == "BLOCKED"
    assert report["final_qc4_state"] == "BLOCKED"


def test_qc4a_authoritative_scores_are_not_overwritten():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["regional"]["identity"]["score"] == 84.6
    assert report["regional"]["eyes_brows"]["score"] == 84.0
    assert report["regional"]["geometry"]["score"] == 19.37
    assert report["authority"]["canonical_artifacts_unchanged"] is True
