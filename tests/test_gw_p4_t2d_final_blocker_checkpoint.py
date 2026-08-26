from __future__ import annotations

import hashlib
import json
from pathlib import Path

from image_studio_runtime.action_composite.regional_score_gateway import (
    RegionalScoreBlocked,
    RegionalScoreEvidence,
    RegionalScoreGateway,
)


ROOT = Path(__file__).parents[1]
CHECKPOINT = ROOT / "artifacts/identity-restoration/benchmarks/gw-p4-final-provider-blocker-checkpoint.json"


def _checkpoint() -> dict:
    return json.loads(CHECKPOINT.read_text(encoding="utf-8"))


def test_final_checkpoint_freezes_three_cap_provider_blocker() -> None:
    report = _checkpoint()
    assert report["decision"] == "PROVIDER_BLOCKED"
    assert report["roadmap_execution"] == "STOPPED_AT_GW_P4_PROVIDER_BLOCKER"
    assert [item["max_output_tokens"] for item in report["transport_attempts"]] == [2048, 4096, 8192]
    assert all(item["finish_reason"].upper().endswith("MAX_TOKENS") for item in report["transport_attempts"])
    assert all(item["valid_samples"] == 0 for item in report["transport_attempts"])


def test_final_checkpoint_preserves_unknown_quality_and_roadmap_boundary() -> None:
    report = _checkpoint()
    assert report["pilot"]["C1"]["quality"] == "UNKNOWN"
    assert report["final_blocker"]["pilot_fail"] is False
    assert report["final_blocker"]["provider_blocked_is_not_pilot_fail"] is True
    assert report["pilot"]["B04_validated"] is False
    assert report["scope_guard"]["C2"] == "UNTOUCHED_AFTER_C1_BLOCKER"
    assert report["scope_guard"]["C3"] == "UNTOUCHED_AFTER_C1_BLOCKER"
    assert report["scope_guard"]["GW-P5"] == "NOT_STARTED"
    assert report["next_allowed_action"] == "NONE_WITHIN_CURRENT_LOCKED_ROADMAP"


def test_regional_gateway_remains_blocked_without_face_authority() -> None:
    try:
        RegionalScoreGateway().build(RegionalScoreEvidence())
    except RegionalScoreBlocked:
        return
    raise AssertionError("Regional authority must remain blocked without Face-QC evidence")


def test_all_three_raw_evidence_hashes_are_unchanged() -> None:
    report = _checkpoint()
    for attempt in report["transport_attempts"]:
        evidence = attempt["raw_evidence"]
        path = ROOT / evidence["path"]
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == evidence["container_sha256"]
        assert len(data) == evidence["container_bytes"]


def test_t2d_is_offline_and_does_not_escalate_transport_or_scope() -> None:
    report = _checkpoint()
    assert report["validator"]["max_output_tokens"] == 8192
    assert report["scope_guard"]["provider_network_calls_during_T2D"] == 0
    assert report["scope_guard"]["gpu_jobs"] == 0
    assert report["scope_guard"]["nano_calls"] == 0
    assert report["scope_guard"]["paid_test_calls"] == 0

    runner = (ROOT / "scripts/run_gw_p4_t2c_output_cap_recovery.py").read_text(encoding="utf-8")
    assert "16384" not in runner
    assert 'find_candidate("B04")' not in runner
    assert "VALIDATOR_MAX_NEW_CALLS\"] = \"1\"" in runner
