import json
from pathlib import Path

from image_studio_runtime.action_composite.regional_score_gateway import ValidatorExecutionContext

REPORT = Path("data/identity_restoration_runs/gw-p0-t2-qc4e-local-search/qc4h1/qc4h1-authority-record.json")


def test_qc4h1_human_recovery_is_not_historical_provenance():
    report = json.loads(REPORT.read_text())
    assert report["authority"]["authority_origin"] == "HUMAN_APPROVED_RECOVERY"
    assert report["manifest"]["path"] is None
    assert report["final"]["status"] == "BLOCKED"


def test_qc4h1_unresolved_reference_roles_fail_closed():
    report = json.loads(REPORT.read_text())
    assert set(report["reference_set"]["unresolved_roles"]) == {"action_pose", "outfit"}
    assert report["reference_set"]["materialized"] is False


def test_future_validator_context_requires_semantic_authority():
    incomplete = ValidatorExecutionContext(provider="gemini", model="gemini-flash-latest", samples=1)
    assert incomplete.has_complete_global_authority() is False
    complete = incomplete.model_copy(update={"project": "venho_linh_an", "image_dna_subject": "linh_an_action_composite", "scenario_profile_id": "outdoor_action_jogging_west_lake", "reference_set_id": "linh_an_action_composite_global_v1", "reference_set_version": "1.0", "reference_set_sha256": "a" * 64, "validation_config_sha256": "b" * 64})
    assert complete.has_complete_global_authority() is True
