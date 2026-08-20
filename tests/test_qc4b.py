import json
from pathlib import Path

from image_studio_runtime.action_composite.workflow_v2 import RegionalGate


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4-local-candidate/diagnostics/qc4b/qc4b-report.json"


def test_qc4b_contract_matrix_is_fail_closed_and_hash_bound():
    report = json.loads(REPORT.read_text())
    assert report["result"] == "PASS"
    assert report["final_qc4_state"] == "BLOCKED"
    assert report["authority"]["source_hash_consistency"] is True
    assert report["canonical_artifacts_unchanged"] is True
    assert report["regional_gate"]["thresholds"] == RegionalGate().thresholds
    assert {item["region"] for item in report["contract_matrix"]} == {
        "identity", "eyes_brows", "geometry", "anatomy", "outfit", "environment", "global_composite"
    }


def test_qc4b_preservation_does_not_become_a_regional_score():
    report = json.loads(REPORT.read_text())
    assert report["preservation"]["contract_supported"] is False
    for field in ("anatomy", "outfit", "environment"):
        assert report["regional"][field]["score"] is None
        assert report["regional"][field]["status"] == "UNKNOWN"


def test_qc4b_geometry_provenance_is_existing_metric():
    report = json.loads(REPORT.read_text())
    audit = report["geometry_audit"]
    assert audit["producer"] == "GeometryEvidenceProducer"
    assert audit["classification"] == "VALID_LOW_SCORE"
    assert audit["implementation_bug_found"] is False
    assert audit["inputs"]["raw_evidence"]["weights"] == {"bbox_iou": 0.5, "pose_agreement": 0.3, "scale_agreement": 0.2}
