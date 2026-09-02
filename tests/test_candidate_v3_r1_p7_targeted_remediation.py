from pathlib import Path

import yaml

from identity_restoration.application.benchmark_orchestration import _scenario_profile_id


ROOT = Path(__file__).resolve().parents[1]


def _config():
    return yaml.safe_load(
        (ROOT / "config/projects/venho_hotel/identity_restoration/r1_p7_targeted_quality_remediation.yaml").read_text()
    )


def _cases():
    contract = yaml.safe_load((ROOT / "contracts/identity_restoration/benchmark_set.yaml").read_text())
    return {case["id"]: case for case in contract["cases"]}


def test_exact_five_failures_have_targeted_remediation_paths():
    config = _config()
    assert {(item["caseId"], lane) for item in config["cases"] for lane in item["lanes"]} == {
        ("B05", "FACE_LOCAL"), ("B07", "FACE_LOCAL"),
        ("B05", "SCENARIO_GLOBAL"), ("B06", "SCENARIO_GLOBAL"),
        ("B09", "SCENARIO_GLOBAL"),
    }
    assert all(item["remediation"]["nextTask"] == "R1-P7-R1" for item in config["cases"])


def test_safety_controls_and_authority_scope_are_unchanged():
    config = _config()
    assert config["authorization"]["targetedRecheckAuthorized"] is False
    assert config["authorization"]["providerCalls"] == 0
    assert config["sharedControls"] == {
        "thresholdsChanged": False, "rubricChanged": False, "validatorChanged": False,
        "architectureChanged": False, "featureFlag": "OFF", "productionPromotion": "NO",
        "frozenArtifactsModified": False,
    }
    cases = _cases()
    for case_id in ("B03", "B04", "B05", "B06"):
        assert _scenario_profile_id(cases[case_id]) == "action_full_body"
    for case_id in ("B01", "B02", "B07", "B08", "B09", "B10"):
        assert _scenario_profile_id(cases[case_id]) is None


def test_final_state_stays_pending_authoritative_recheck():
    final = _config()["finalState"]
    assert final["r1P7"] == "CLOSED_REMEDIATION_READY"
    assert final["qualityDisposition"] == "FAIL_PENDING_RECHECK"
    assert final["nextAction"] == "R1-P7-R1_TARGETED_AUTHORITATIVE_RECHECK"
