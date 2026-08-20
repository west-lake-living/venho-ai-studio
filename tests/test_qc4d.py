import json
from pathlib import Path

from image_studio_runtime.action_composite.workflow_v2 import RegionalGate


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4-local-candidate/diagnostics/qc4d/qc4d-report.json"


def test_qc4d_uses_same_extractor_and_preserves_gate_contract():
    report = json.loads(REPORT.read_text())
    contract = report["contract"]
    assert contract["reference_extractor"] == contract["observed_extractor"]
    assert contract["formula_changed"] is False
    assert contract["threshold_changed"] is False
    assert report["geometry_score"]["threshold"] == RegionalGate().thresholds["geometry"] == 92.0
    assert report["reference_base"]["detection_count"] == 1
    assert report["observed_candidate"]["detection_count"] == 1


def test_qc4d_provenance_binds_both_source_hashes_and_not_a2():
    report = json.loads(REPORT.read_text())
    provenance = report["geometry_score"]["provenance"]
    assert provenance["stage"] == "post_identity_restoration"
    assert provenance["reference_semantics"] == "insightface_geometry"
    assert provenance["observed_semantics"] == "insightface_geometry"
    assert provenance["reference_sha"] == report["reference_base"]["sha256"]
    assert provenance["observed_sha"] == report["observed_candidate"]["sha256"]
    assert report["regression"]["a2_used_as_geometry_reference"] is False


def test_qc4d_keeps_full_scene_detector_and_canonical_bytes_unchanged():
    report = json.loads(REPORT.read_text())
    assert report["regression"]["bbox_detector_removed"] is False
    assert report["regression"]["candidate_selector_unchanged"] is True
    assert report["canonical_artifacts_unchanged"] is True
