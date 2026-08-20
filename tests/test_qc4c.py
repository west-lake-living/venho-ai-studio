import json
from pathlib import Path

from image_studio_runtime.action_composite.workflow_v2 import RegionalGate


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4-local-candidate/diagnostics/qc4c/qc4c-report.json"


def test_qc4c_reproduces_both_persisted_scores_without_threshold_change():
    report = json.loads(REPORT.read_text())
    assert report["scores"]["scores_reproduced"] is True
    assert report["scores"]["locked_base_geometry_score"] == 17.59
    assert report["scores"]["repaired_candidate_geometry_score"] == 19.37
    assert report["geometry_formula"]["threshold"] == RegionalGate().thresholds["geometry"] == 92.0


def test_qc4c_binds_reference_to_base_not_a2_and_preserves_artifacts():
    report = json.loads(REPORT.read_text())
    assert report["reference"]["reference_type"] == "source/base FaceGeometry lock"
    assert report["reference"]["reference_sha256"] == report["source_hashes"]["base"]
    assert report["canonical_artifacts_unchanged"] is True
    assert report["implementation_changed"] is False


def test_qc4c_records_stage_contract_gap_and_identity_interaction_as_non_monotonic():
    report = json.loads(REPORT.read_text())
    assert report["feasibility"]["classification"] == "CONTRACT_CONTRADICTION"
    assert report["correct_stage_binding"]["option"] == "OPTION 3"
    assert "UNKNOWN_NON_MONOTONIC" in report["identity_interaction"]["expected_effect_of_larger_identity_mask"]
