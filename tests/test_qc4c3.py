import hashlib
import json
from pathlib import Path

from image_studio_runtime.action_composite.workflow_v2 import RegionalGate


BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
REPORT = Path("data/identity_restoration_runs/gw-p0-t2-20260819-local-rerun/diagnostics/qc4c3/gw-p0-t2-qc4c3-report.json")


def test_qc4c3_regional_gate_unknown_is_fail_closed():
    gate = RegionalGate(geometry=95.0, pixel_preservation=False)
    passed, failures = gate.evaluate()
    assert passed is False
    assert "identity_unvalidated" in failures
    assert "global_composite_unvalidated" in failures
    assert "pixel_preservation_failed" in failures


def test_qc4c3_thresholds_are_the_existing_authoritative_values():
    assert RegionalGate().thresholds == {
        "identity": 90.0,
        "eyes_brows": 90.0,
        "geometry": 92.0,
        "anatomy": 90.0,
        "outfit": 90.0,
        "environment": 90.0,
        "global_composite": 90.0,
    }


def test_qc4c3_base_authority_and_geometry_source_sha_are_identical():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    base_sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
    assert base_sha == "bb031e7adfcc0c7d79544c3edb932eebafc1f797a59881415e57addc584d26a0"
    assert report["base_sha256"] == base_sha
    assert report["geometry"]["source_sha256"] == base_sha
    assert report["evidence_source_sha_consistent"] is True


def test_qc4c3_serialized_geometry_provenance_has_real_five_landmarks():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    geometry = report["geometry"]
    assert geometry["detection_count"] == 1
    assert len(geometry["landmarks"]) == 5
    assert geometry["provenance"]["pnp"]["synthetic_landmarks_added"] == 0
