import json
from pathlib import Path

REPORT = Path("data/identity_restoration_runs/gw-p0-t2-qc4e-local-search/qc4h2/global-validation-authority.json")


def test_qc4h2_reference_roles_are_distinct_with_shared_artifact():
    report = json.loads(REPORT.read_text())
    members = {item["role"]: item for item in report["reference_set"]["members"]}
    assert members["action_pose"]["sha256"] == members["outfit"]["sha256"] == members["composition"]["sha256"]
    assert members["identity"]["sha256"] != members["action_pose"]["sha256"]
    assert members["identity"]["stage"] == "identity"
    assert members["action_pose"]["stage"] == "post_identity_restoration"


def test_qc4h2_reference_set_is_complete_and_human_recovery():
    report = json.loads(REPORT.read_text())
    assert report["reference_set"]["complete"] is True
    assert report["reference_set"]["unresolved_roles"] == []
    assert report["authority_origin"] == "HUMAN_APPROVED_RECOVERY"
    assert len(report["reference_set"]["sha256"]) == 64


def test_qc4h2_does_not_call_validator_or_change_images():
    report = json.loads(REPORT.read_text())
    assert report["execution"]["validator_called"] == "NO"
    assert report["execution"]["comfyui_rerun"] == "NO"
    assert report["execution"]["canonical_artifacts_unchanged"] is True
