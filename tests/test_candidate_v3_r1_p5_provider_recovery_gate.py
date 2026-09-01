from __future__ import annotations

import pytest

from shared.vision.provider_recovery_gate import (
    ProviderHoldState,
    ProviderRecoveryBlocked,
    ProviderRecoveryGate,
    assess_recovery_probe,
)


HOLD = {"provider_hold": {"active": True, "provider": "Gemini", "model": "gemini-flash-latest"}}


def gate(value: str | None = None) -> ProviderRecoveryGate:
    environment = {} if value is None else {"PROVIDER_RECOVERY_RECHECK_AUTHORIZED": value}
    return ProviderRecoveryGate(HOLD, environment=environment)


def complete_evidence(**overrides: bool | str) -> dict[str, bool | str]:
    evidence: dict[str, bool | str] = {
        "request_succeeded": True, "no_503": True, "no_timeout": True,
        "no_truncation": True, "no_malformed_json": True, "no_unsupported_schema": True,
        "parsed_without_repair": True, "required_fields_present": True,
        "dto_schema_valid": True, "raw_response_preserved": True,
        "raw_response_hash_recorded": True, "lineage_complete": True,
        "authoritative_response": True, "quality_verdict": "FAIL",
    }
    evidence.update(overrides)
    return evidence


# Authorization: missing, FALSE, malformed, TRUE.
def test_missing_authorization_blocks_without_calls() -> None:
    candidate = gate()
    with pytest.raises(ProviderRecoveryBlocked):
        candidate.begin_recovery_probe()
    assert candidate.state == ProviderHoldState.ACTIVE
    assert candidate.probe_count == 0


def test_false_authorization_blocks_without_calls() -> None:
    candidate = gate("FALSE")
    with pytest.raises(ProviderRecoveryBlocked):
        candidate.begin_recovery_probe()
    assert candidate.probe_count == 0


def test_malformed_authorization_blocks_without_calls() -> None:
    candidate = gate("true")
    with pytest.raises(ProviderRecoveryBlocked):
        candidate.begin_recovery_probe()
    assert candidate.state == ProviderHoldState.ACTIVE


def test_explicit_true_authorizes_exact_probe_path() -> None:
    candidate = gate("TRUE")
    candidate.begin_recovery_probe()
    assert candidate.state == ProviderHoldState.RECOVERY_PROBE_IN_PROGRESS
    assert candidate.probe_count == 1


# Hold enforcement and provider lock.
@pytest.mark.parametrize("lane", ["FACE_LOCAL", "SCENARIO_GLOBAL"])
def test_active_hold_blocks_bulk_lane(lane: str) -> None:
    with pytest.raises(ProviderRecoveryBlocked, match="BULK_EVALUATION_BLOCKED"):
        gate().assert_bulk_evaluation_blocked(lane)


def test_active_hold_blocks_bulk_even_when_recovery_is_authorized() -> None:
    candidate = gate("TRUE")
    with pytest.raises(ProviderRecoveryBlocked):
        candidate.assert_bulk_evaluation_blocked("FACE_LOCAL")


def test_provider_fallback_is_rejected() -> None:
    with pytest.raises(ProviderRecoveryBlocked, match="PROVIDER_LOCK_MISMATCH"):
        gate().assert_provider_lock("OpenAI", "gpt-5")


def test_model_switch_is_rejected() -> None:
    with pytest.raises(ProviderRecoveryBlocked, match="PROVIDER_LOCK_MISMATCH"):
        gate().assert_provider_lock("Gemini", "gemini-2.5-flash")


# Probe limits.
def test_authorized_recovery_allows_one_probe_only() -> None:
    candidate = gate("TRUE")
    candidate.begin_recovery_probe()
    with pytest.raises(ProviderRecoveryBlocked, match="RECOVERY_PROBE_BLOCKED"):
        candidate.begin_recovery_probe()
    assert candidate.probe_count == 1


def test_failed_probe_cannot_trigger_second_probe() -> None:
    candidate = gate("TRUE")
    candidate.begin_recovery_probe()
    candidate.complete_recovery_probe({})
    assert candidate.state == ProviderHoldState.ACTIVE
    with pytest.raises(ProviderRecoveryBlocked):
        candidate.begin_recovery_probe()


# Recovery pass/fail criteria.
def test_complete_schema_valid_response_recovers_hold() -> None:
    candidate = gate("TRUE")
    candidate.begin_recovery_probe()
    assessment = candidate.complete_recovery_probe(complete_evidence(quality_verdict="PASS"))
    assert assessment.passed
    assert candidate.state == ProviderHoldState.RECOVERED


def test_quality_fail_is_still_valid_provider_recovery() -> None:
    assessment = assess_recovery_probe(complete_evidence(quality_verdict="FAIL"))
    assert assessment.passed
    assert assessment.quality_verdict == "FAIL"


@pytest.mark.parametrize("criterion", [
    "no_503", "no_timeout", "no_truncation", "no_malformed_json",
    "no_unsupported_schema", "parsed_without_repair",
])
def test_transport_or_parse_failure_keeps_hold_active(criterion: str) -> None:
    candidate = gate("TRUE")
    candidate.begin_recovery_probe()
    candidate.complete_recovery_probe(complete_evidence(**{criterion: False}))
    assert candidate.state == ProviderHoldState.ACTIVE


@pytest.mark.parametrize("criterion", [
    "request_succeeded", "required_fields_present", "dto_schema_valid",
    "raw_response_preserved", "raw_response_hash_recorded", "lineage_complete",
])
def test_evidence_failure_keeps_hold_active(criterion: str) -> None:
    candidate = gate("TRUE")
    candidate.begin_recovery_probe()
    assessment = candidate.complete_recovery_probe(complete_evidence(**{criterion: False}))
    assert not assessment.passed
    assert criterion in assessment.failed_criteria
    assert candidate.state == ProviderHoldState.ACTIVE


# State integrity.
def test_recovery_does_not_authorize_bulk_without_separate_resume_flag() -> None:
    candidate = gate("TRUE")
    candidate.begin_recovery_probe()
    candidate.complete_recovery_probe(complete_evidence())
    with pytest.raises(ProviderRecoveryBlocked):
        candidate.assert_bulk_evaluation_authorized("FACE_LOCAL")


def test_pending_count_remains_eighteen_after_recovery() -> None:
    candidate = gate("TRUE")
    candidate.begin_recovery_probe()
    candidate.complete_recovery_probe(complete_evidence())
    assert candidate.snapshot()["pendingAuthoritativeEvaluations"] == 18


def test_boundary_feature_and_promotion_integrity_are_unchanged() -> None:
    snapshot = gate().snapshot()
    assert snapshot["state"] == "ACTIVE"
    assert snapshot["pendingAuthoritativeEvaluations"] == 18
    assert snapshot["bulkEvaluation"] == "BLOCKED_IN_R1_P5"
