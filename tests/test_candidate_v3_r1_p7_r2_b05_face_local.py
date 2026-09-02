from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/projects/venho_hotel/identity_restoration/r1_p7_r2_b05_face_local.yaml"


def _config():
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def test_r2_is_b05_face_local_only_and_recheck_is_separate():
    config = _config()
    assert config["target"] == {
        "caseId": "B05", "lane": "FACE_LOCAL", "currentScore": 88.50,
        "currentVerdict": "revise", "currentDisposition": "FAIL",
        "nextTask": "R1-P7-R2-R1 B05 FACE_LOCAL AUTHORITATIVE RECHECK",
    }
    assert config["authorization"]["b05FaceLocalRecheckAuthorized"] is False
    assert config["authorization"]["providerCalls"] == 0
    assert config["remediation"]["scope"] == "B05_ONLY"
    assert config["remediation"]["liveRecheckRequired"] is True


def test_r2_preserves_quality_policy_and_production_safety():
    config = _config()
    assert config["remediation"]["forbidden"] == [
        "global_parameter_tuning", "threshold_change", "rubric_change",
        "provider_switch", "frozen_artifact_mutation",
    ]
    assert config["protection"] == {
        "boundary": "9/9_PASS", "faceLocalPassingCases": 8,
        "scenarioGlobalPassingCases": 9, "featureFlag": "OFF",
        "productionPromotion": "NO", "architectureChanged": False,
    }
