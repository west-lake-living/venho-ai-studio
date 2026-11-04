from __future__ import annotations

import pytest

from growth_engine.domain.delivery.allowed_actions import allowed_actions
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryState


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (DeliveryState.DRAFT, ["cancel"]),
        (DeliveryState.IN_REVIEW, ["approve", "edit_caption", "replace_image", "rotate_image", "reject", "cancel"]),
        (DeliveryState.APPROVED, ["revoke", "edit_caption", "replace_image", "cancel"]),
        (DeliveryState.QUEUED, ["revoke", "cancel"]),
        (DeliveryState.EXECUTING, ["open_post"]),
        (DeliveryState.REPORTED_PUBLISHED, ["open_post"]),
        (DeliveryState.UNKNOWN, ["reconcile"]),
        (DeliveryState.BLOCKED, ["view_reason", "safe_retry", "mark_failed", "cancel"]),
        (DeliveryState.PUBLISHED, ["open_post"]),
        (DeliveryState.FAILED_FINAL, []),
        (DeliveryState.EXPIRED, []),
        (DeliveryState.CANCELLED, []),
        (DeliveryState.SUPERSEDED, []),
        (DeliveryState.LEGACY_UNVERIFIED, []),
    ],
)
def test_allowed_actions_match_plan_table(state: DeliveryState, expected: list[str]) -> None:
    context = {
        "payload_hash_matches": True,
        "qc_status": "PASS",
        "facts_valid_at_scheduled": True,
        "now_ms": 10,
        "deadline_at_ms": 20,
        "channel_enabled": True,
        "config_hash_matches": True,
        "command_not_authorized": True,
        "no_execution_live": True,
        "all_prior_executions_no_side_effect": True,
        "window_open": True,
        "approval_valid": True,
        "permalink": "/synthetic-post",
        "revision_is_current": True,
        "no_execution_live": True,
        "reason": "synthetic reason",
        "actor_id": "synthetic-operator",
    }
    actions = allowed_actions(Delivery("delivery-1", state), context)
    assert [item.action for item in actions] == expected
    assert all(item.enabled for item in actions)
    assert all(item.reason_code is None for item in actions)


def test_conditional_actions_fail_closed() -> None:
    queued = allowed_actions(
        Delivery("queued", DeliveryState.QUEUED),
        {"command_not_authorized": False},
    )
    assert [item.action for item in queued] == ["revoke", "cancel"]
    assert not any(item.enabled for item in queued)
    assert all(item.reason_code == "ERR_GC2_STATE_CONFLICT" for item in queued)

    blocked = allowed_actions(Delivery("blocked", DeliveryState.BLOCKED), {})
    safe_retry = next(item for item in blocked if item.action == "safe_retry")
    assert safe_retry.enabled is False
    assert safe_retry.reason_code == "ERR_GC2_STATE_CONFLICT"


def test_open_post_is_shown_only_when_permalink_exists() -> None:
    assert allowed_actions(Delivery("published", DeliveryState.PUBLISHED), {}) == []
    actions = allowed_actions(
        Delivery("published", DeliveryState.PUBLISHED), {"permalink": "/synthetic-post"}
    )
    assert len(actions) == 1
    assert actions[0].action == "open_post"
    assert actions[0].enabled is True
