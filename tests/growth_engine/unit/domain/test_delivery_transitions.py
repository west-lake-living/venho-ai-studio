from __future__ import annotations

from itertools import product

import pytest

from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.delivery.transitions import (
    InvalidTransition,
    TRANSITIONS,
    apply_transition,
    guard_is_satisfied,
    transition_target,
)
from growth_engine.domain.kernel.errors import DomainError, ErrorCode


EXPECTED_TRANSITIONS = {
    (None, DeliveryEvent.RESERVE): DeliveryState.DRAFT,
    (DeliveryState.DRAFT, DeliveryEvent.CREATE_REVISION): DeliveryState.IN_REVIEW,
    (DeliveryState.IN_REVIEW, DeliveryEvent.CREATE_REVISION): DeliveryState.IN_REVIEW,
    (DeliveryState.IN_REVIEW, DeliveryEvent.REJECT): DeliveryState.IN_REVIEW,
    (DeliveryState.IN_REVIEW, DeliveryEvent.APPROVE): DeliveryState.APPROVED,
    (DeliveryState.APPROVED, DeliveryEvent.REVOKE): DeliveryState.IN_REVIEW,
    (DeliveryState.APPROVED, DeliveryEvent.CREATE_REVISION): DeliveryState.IN_REVIEW,
    (DeliveryState.APPROVED, DeliveryEvent.ENQUEUE): DeliveryState.QUEUED,
    (DeliveryState.QUEUED, DeliveryEvent.REVOKE): DeliveryState.IN_REVIEW,
    (DeliveryState.QUEUED, DeliveryEvent.CREATE_REVISION): DeliveryState.IN_REVIEW,
    (DeliveryState.QUEUED, DeliveryEvent.AUTHORIZE): DeliveryState.EXECUTING,
    (DeliveryState.QUEUED, DeliveryEvent.PREFLIGHT_BLOCK): DeliveryState.BLOCKED,
    (DeliveryState.EXECUTING, DeliveryEvent.RECEIPT_CREATED): DeliveryState.REPORTED_PUBLISHED,
    (DeliveryState.EXECUTING, DeliveryEvent.RECEIPT_NO_SIDE_EFFECT_RETRYABLE): DeliveryState.BLOCKED,
    (DeliveryState.EXECUTING, DeliveryEvent.RECEIPT_NO_SIDE_EFFECT_NON_RETRYABLE): DeliveryState.FAILED_FINAL,
    (DeliveryState.EXECUTING, DeliveryEvent.RECEIPT_UNKNOWN): DeliveryState.UNKNOWN,
    (DeliveryState.EXECUTING, DeliveryEvent.RECEIPT_TIMEOUT): DeliveryState.UNKNOWN,
    (DeliveryState.UNKNOWN, DeliveryEvent.RECEIPT_CREATED): DeliveryState.REPORTED_PUBLISHED,
    (DeliveryState.UNKNOWN, DeliveryEvent.RESOLVE_PUBLISHED): DeliveryState.REPORTED_PUBLISHED,
    (DeliveryState.UNKNOWN, DeliveryEvent.RESOLVE_NO_SIDE_EFFECT): DeliveryState.BLOCKED,
    (DeliveryState.REPORTED_PUBLISHED, DeliveryEvent.VERIFY_OK): DeliveryState.PUBLISHED,
    (DeliveryState.REPORTED_PUBLISHED, DeliveryEvent.VERIFY_MISMATCH): DeliveryState.UNKNOWN,
    (DeliveryState.BLOCKED, DeliveryEvent.SAFE_RETRY): DeliveryState.QUEUED,
    (DeliveryState.BLOCKED, DeliveryEvent.MARK_FAILED_FINAL): DeliveryState.FAILED_FINAL,
    (DeliveryState.DRAFT, DeliveryEvent.EXPIRE): DeliveryState.EXPIRED,
    (DeliveryState.IN_REVIEW, DeliveryEvent.EXPIRE): DeliveryState.EXPIRED,
    (DeliveryState.APPROVED, DeliveryEvent.EXPIRE): DeliveryState.EXPIRED,
    (DeliveryState.QUEUED, DeliveryEvent.EXPIRE): DeliveryState.EXPIRED,
    (DeliveryState.BLOCKED, DeliveryEvent.EXPIRE): DeliveryState.EXPIRED,
    (DeliveryState.DRAFT, DeliveryEvent.CANCEL): DeliveryState.CANCELLED,
    (DeliveryState.IN_REVIEW, DeliveryEvent.CANCEL): DeliveryState.CANCELLED,
    (DeliveryState.APPROVED, DeliveryEvent.CANCEL): DeliveryState.CANCELLED,
    (DeliveryState.QUEUED, DeliveryEvent.CANCEL): DeliveryState.CANCELLED,
    (DeliveryState.BLOCKED, DeliveryEvent.CANCEL): DeliveryState.CANCELLED,
    (DeliveryState.DRAFT, DeliveryEvent.SUPERSEDE): DeliveryState.SUPERSEDED,
    (DeliveryState.IN_REVIEW, DeliveryEvent.SUPERSEDE): DeliveryState.SUPERSEDED,
    (DeliveryState.APPROVED, DeliveryEvent.SUPERSEDE): DeliveryState.SUPERSEDED,
    (DeliveryState.QUEUED, DeliveryEvent.SUPERSEDE): DeliveryState.SUPERSEDED,
    (DeliveryState.LEGACY_UNVERIFIED, DeliveryEvent.LEGACY_VERIFY): DeliveryState.PUBLISHED,
    (DeliveryState.PUBLISHED, DeliveryEvent.VISIBILITY_CHANGE): DeliveryState.PUBLISHED,
}


def test_transition_table_matches_every_state_event_pair() -> None:
    assert TRANSITIONS == EXPECTED_TRANSITIONS
    assert transition_target(None, DeliveryEvent.RESERVE) is DeliveryState.DRAFT
    assert guard_is_satisfied(DeliveryState.PUBLISHED, DeliveryEvent.VISIBILITY_CHANGE, {})
    for state, event in product(DeliveryState, DeliveryEvent):
        pair = (state, event)
        if pair in EXPECTED_TRANSITIONS:
            assert transition_target(state, event) is EXPECTED_TRANSITIONS[pair]
        else:
            with pytest.raises(InvalidTransition):
                transition_target(state, event)


def test_d05_approval_guard_accepts_only_complete_current_context() -> None:
    context = {
        "payload_hash_matches": True,
        "qc_status": "PASS",
        "facts_valid_at_scheduled": True,
        "now_ms": 10,
        "deadline_at_ms": 20,
        "channel_enabled": True,
        "config_hash_matches": True,
    }
    assert apply_transition(DeliveryState.IN_REVIEW, DeliveryEvent.APPROVE, context) is DeliveryState.APPROVED
    for key, value in (
        ("payload_hash_matches", False),
        ("qc_status", "FAIL"),
        ("facts_valid_at_scheduled", False),
        ("now_ms", 20),
        ("channel_enabled", False),
        ("config_hash_matches", False),
    ):
        failed = {**context, key: value}
        with pytest.raises(DomainError):
            apply_transition(DeliveryState.IN_REVIEW, DeliveryEvent.APPROVE, failed)


def test_d07_enqueue_guard_checks_time_mode_pause_and_epoch() -> None:
    context = {
        "scheduled_at_ms": 10,
        "now_ms": 10,
        "deadline_at_ms": 20,
        "mode": "LIVE_MANUAL",
        "paused": False,
        "epoch_current": True,
    }
    assert apply_transition(DeliveryState.APPROVED, DeliveryEvent.ENQUEUE, context) is DeliveryState.QUEUED
    for key, value in (
        ("now_ms", 9),
        ("now_ms", 21),
        ("mode", "DRY_RUN"),
        ("paused", True),
        ("epoch_current", False),
    ):
        with pytest.raises(DomainError):
            apply_transition(DeliveryState.APPROVED, DeliveryEvent.ENQUEUE, {**context, key: value})


def test_d19_safe_retry_requires_no_live_side_effect_and_valid_approval() -> None:
    context = {
        "no_execution_live": True,
        "all_prior_executions_no_side_effect": True,
        "window_open": True,
        "approval_valid": True,
    }
    assert apply_transition(DeliveryState.BLOCKED, DeliveryEvent.SAFE_RETRY, context) is DeliveryState.QUEUED
    for key in context:
        with pytest.raises(DomainError):
            apply_transition(DeliveryState.BLOCKED, DeliveryEvent.SAFE_RETRY, {**context, key: False})


def test_d23_supersede_refuses_live_execution() -> None:
    assert apply_transition(
        DeliveryState.IN_REVIEW,
        DeliveryEvent.SUPERSEDE,
        {"no_execution_live": True},
    ) is DeliveryState.SUPERSEDED
    with pytest.raises(DomainError):
        apply_transition(
            DeliveryState.IN_REVIEW,
            DeliveryEvent.SUPERSEDE,
            {"no_execution_live": False},
        )


def test_invalid_transition_uses_state_conflict_error() -> None:
    with pytest.raises(InvalidTransition) as caught:
        transition_target(DeliveryState.EXECUTING, DeliveryEvent.APPROVE)
    assert caught.value.code == ErrorCode.STATE_CONFLICT.value
    with pytest.raises(InvalidTransition):
        transition_target(None, DeliveryEvent.APPROVE)


def test_delivery_apply_returns_new_aggregate_and_event() -> None:
    delivery = Delivery(id="delivery-1", state=DeliveryState.IN_REVIEW)
    updated, events = delivery.apply(
        DeliveryEvent.APPROVE,
        {
            "payload_hash_matches": True,
            "qc_status": "PASS",
            "facts_valid_at_scheduled": True,
            "now_ms": 10,
            "deadline_at_ms": 20,
            "channel_enabled": True,
            "config_hash_matches": True,
        },
    )
    assert delivery.state is DeliveryState.IN_REVIEW
    assert updated.state is DeliveryState.APPROVED
    assert updated.row_version == delivery.row_version + 1
    assert updated.active is True
    assert len(events) == 1
    assert events[0].aggregate_id == delivery.id
    assert events[0].data["from_state"] == DeliveryState.IN_REVIEW.value
    assert events[0].data["to_state"] == DeliveryState.APPROVED.value


def test_active_is_false_only_for_superseded() -> None:
    assert all(Delivery(str(state), state).active for state in DeliveryState if state is not DeliveryState.SUPERSEDED)
    assert Delivery("old", DeliveryState.SUPERSEDED).active is False


def test_all_transition_guards_fail_closed_for_each_required_condition() -> None:
    cases = [
        (None, DeliveryEvent.RESERVE, {"target_available": True, "slot_not_cancelled": True}, ["target_available", "slot_not_cancelled"]),
        (DeliveryState.DRAFT, DeliveryEvent.CREATE_REVISION, {"revision_complete": True, "qc_status": "PASS"}, ["revision_complete"]),
        (DeliveryState.IN_REVIEW, DeliveryEvent.CREATE_REVISION, {"if_match_matches": True}, ["if_match_matches"]),
        (DeliveryState.IN_REVIEW, DeliveryEvent.REJECT, {"revision_is_current": True}, ["revision_is_current"]),
        (DeliveryState.APPROVED, DeliveryEvent.REVOKE, {"no_execution_live": True}, ["no_execution_live"]),
        (DeliveryState.APPROVED, DeliveryEvent.CREATE_REVISION, {"no_execution_live": True}, ["no_execution_live"]),
        (DeliveryState.QUEUED, DeliveryEvent.REVOKE, {"command_not_authorized": True}, ["command_not_authorized"]),
        (DeliveryState.QUEUED, DeliveryEvent.CREATE_REVISION, {"command_not_authorized": True}, ["command_not_authorized"]),
        (DeliveryState.QUEUED, DeliveryEvent.AUTHORIZE, {"preflight_pass": True}, ["preflight_pass"]),
        (DeliveryState.QUEUED, DeliveryEvent.PREFLIGHT_BLOCK, {"preflight_blocking": True}, ["preflight_blocking"]),
        (DeliveryState.EXECUTING, DeliveryEvent.RECEIPT_CREATED, {"receipt_matches": True, "platform_post_id_valid": True}, ["receipt_matches", "platform_post_id_valid"]),
        (DeliveryState.EXECUTING, DeliveryEvent.RECEIPT_NO_SIDE_EFFECT_RETRYABLE, {"error_class_verified": True}, ["error_class_verified"]),
        (DeliveryState.EXECUTING, DeliveryEvent.RECEIPT_NO_SIDE_EFFECT_NON_RETRYABLE, {"error_class_verified": True}, ["error_class_verified"]),
        (DeliveryState.UNKNOWN, DeliveryEvent.RECEIPT_CREATED, {"post_id_matches_page": True}, ["post_id_matches_page"]),
        (DeliveryState.UNKNOWN, DeliveryEvent.RESOLVE_PUBLISHED, {"post_id_matches_page": True}, ["post_id_matches_page"]),
        (DeliveryState.REPORTED_PUBLISHED, DeliveryEvent.VERIFY_OK, {"existence": "EXISTS", "ownership": "MATCH"}, ["existence", "ownership"]),
        (DeliveryState.REPORTED_PUBLISHED, DeliveryEvent.VERIFY_MISMATCH, {"existence": "NOT_FOUND"}, ["existence"]),
        (DeliveryState.BLOCKED, DeliveryEvent.MARK_FAILED_FINAL, {"actor_id": "operator", "reason": "reviewed"}, ["actor_id", "reason"]),
        (DeliveryState.DRAFT, DeliveryEvent.CANCEL, {"no_execution_live": True, "reason": "requested"}, ["no_execution_live", "reason"]),
        (DeliveryState.IN_REVIEW, DeliveryEvent.CANCEL, {"no_execution_live": True, "reason": "requested"}, ["no_execution_live", "reason"]),
        (DeliveryState.APPROVED, DeliveryEvent.CANCEL, {"no_execution_live": True, "reason": "requested"}, ["no_execution_live", "reason"]),
        (DeliveryState.QUEUED, DeliveryEvent.CANCEL, {"no_execution_live": True, "command_not_authorized": True, "reason": "requested"}, ["no_execution_live", "command_not_authorized", "reason"]),
        (DeliveryState.BLOCKED, DeliveryEvent.CANCEL, {"no_execution_live": True, "reason": "requested"}, ["no_execution_live", "reason"]),
        (DeliveryState.LEGACY_UNVERIFIED, DeliveryEvent.LEGACY_VERIFY, {"post_id_matches_page": True}, ["post_id_matches_page"]),
    ]
    for state, event, passing, required_keys in cases:
        assert guard_is_satisfied(state, event, passing), (state, event)
        for key in required_keys:
            failed = {**passing, key: False}
            assert not guard_is_satisfied(state, event, failed), (state, event, key)

    for qc_status in ("FAIL", "QUARANTINED"):
        assert not guard_is_satisfied(
            DeliveryState.DRAFT,
            DeliveryEvent.CREATE_REVISION,
            {"revision_complete": True, "qc_status": qc_status},
        )
    for existence in ("NOT_FOUND", "MISMATCH", "UNAVAILABLE", None):
        assert not guard_is_satisfied(
            DeliveryState.REPORTED_PUBLISHED,
            DeliveryEvent.VERIFY_OK,
            {"existence": existence, "ownership": "MATCH"},
        )
    assert all(
        guard_is_satisfied(DeliveryState.REPORTED_PUBLISHED, DeliveryEvent.VERIFY_MISMATCH, {"existence": value})
        for value in ("NOT_FOUND", "MISMATCH")
    )
    assert not guard_is_satisfied(DeliveryState.REPORTED_PUBLISHED, DeliveryEvent.VERIFY_MISMATCH, {"existence": "UNAVAILABLE"})


def test_time_guards_reject_missing_wrong_type_and_boundary_values() -> None:
    approve = {
        "payload_hash_matches": True,
        "qc_status": "PASS",
        "facts_valid_at_scheduled": True,
        "now_ms": 10,
        "deadline_at_ms": 20,
        "channel_enabled": True,
        "config_hash_matches": True,
    }
    for key, value in (("now_ms", None), ("now_ms", True), ("deadline_at_ms", None), ("deadline_at_ms", True)):
        assert not guard_is_satisfied(DeliveryState.IN_REVIEW, DeliveryEvent.APPROVE, {**approve, key: value})

    enqueue = {
        "scheduled_at_ms": 10,
        "now_ms": 10,
        "deadline_at_ms": 20,
        "mode": "LIVE_MANUAL",
        "paused": False,
        "epoch_current": True,
    }
    for key, value in (
        ("scheduled_at_ms", None),
        ("scheduled_at_ms", True),
        ("now_ms", None),
        ("now_ms", True),
        ("deadline_at_ms", None),
        ("deadline_at_ms", True),
        ("scheduled_at_ms", 11),
        ("now_ms", 21),
        ("mode", "DRY_RUN"),
        ("paused", True),
        ("epoch_current", False),
    ):
        assert not guard_is_satisfied(DeliveryState.APPROVED, DeliveryEvent.ENQUEUE, {**enqueue, key: value})

    for now, deadline, no_execution_live, expected in (
        (None, 20, True, False),
        (True, 20, True, False),
        (21, None, True, False),
        (21, True, True, False),
        (20, 20, True, False),
        (21, 20, False, False),
        (21, 20, True, True),
    ):
        assert guard_is_satisfied(
            DeliveryState.BLOCKED,
            DeliveryEvent.EXPIRE,
            {"now_ms": now, "deadline_at_ms": deadline, "no_execution_live": no_execution_live},
        ) is expected


def test_unknown_resolution_requires_actor_reason_and_evidence_text() -> None:
    state, event = DeliveryState.UNKNOWN, DeliveryEvent.RESOLVE_NO_SIDE_EFFECT
    assert guard_is_satisfied(state, event, {"actor_id": "operator", "reason": "checked", "evidence": "history id"})
    for context in (
        {"actor_id": " ", "reason": "checked", "evidence": "history id"},
        {"actor_id": "operator", "reason": "\n", "evidence": "history id"},
        {"actor_id": "operator", "reason": "checked", "evidence": None},
    ):
        assert not guard_is_satisfied(state, event, context)


def test_expire_cancel_and_supersede_guards_cover_every_source_state() -> None:
    expirable = (
        DeliveryState.DRAFT,
        DeliveryState.IN_REVIEW,
        DeliveryState.APPROVED,
        DeliveryState.QUEUED,
        DeliveryState.BLOCKED,
    )
    for state in expirable:
        assert guard_is_satisfied(
            state,
            DeliveryEvent.EXPIRE,
            {"now_ms": 21, "deadline_at_ms": 20, "no_execution_live": True},
        )
        cancel_ctx = {"no_execution_live": True, "reason": "operator request"}
        if state is DeliveryState.QUEUED:
            cancel_ctx["command_not_authorized"] = True
        assert guard_is_satisfied(state, DeliveryEvent.CANCEL, cancel_ctx)
    for state in (
        DeliveryState.DRAFT,
        DeliveryState.IN_REVIEW,
        DeliveryState.APPROVED,
        DeliveryState.QUEUED,
    ):
        assert guard_is_satisfied(state, DeliveryEvent.SUPERSEDE, {"no_execution_live": True})


def test_approval_decision_is_immutable_and_revoke_requires_source_decision() -> None:
    approval = ApprovalDecision(
        id="approval-1",
        revision_id="revision-1",
        payload_hash="a" * 64,
        decision=ApprovalType.APPROVE,
        actor_id="operator-1",
        created_at_ms=10,
    )
    assert approval.decision is ApprovalType.APPROVE
    with pytest.raises(ValueError, match="revokes_id"):
        ApprovalDecision(
            id="revoke-1",
            revision_id="revision-1",
            payload_hash="a" * 64,
            decision=ApprovalType.REVOKE,
            actor_id="operator-1",
            created_at_ms=11,
        )
