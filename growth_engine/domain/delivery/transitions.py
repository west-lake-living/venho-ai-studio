from __future__ import annotations

from collections.abc import Mapping
from typing import Callable

from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.kernel.errors import DomainError, ErrorCode


TransitionKey = tuple[DeliveryState | None, DeliveryEvent]
Guard = Callable[[Mapping[str, object]], bool]


class InvalidTransition(DomainError):
    def __init__(self, state: DeliveryState | None, event: DeliveryEvent) -> None:
        from_value = state.value if state is not None else None
        super().__init__(
            ErrorCode.STATE_CONFLICT,
            "Trạng thái bài đã thay đổi; hãy tải lại.",
            {"from_state": from_value, "event": event.value},
        )


TRANSITIONS: dict[TransitionKey, DeliveryState] = {
    (None, DeliveryEvent.RESERVE): DeliveryState.DRAFT,  # D01
    (DeliveryState.DRAFT, DeliveryEvent.CREATE_REVISION): DeliveryState.IN_REVIEW,  # D02
    (DeliveryState.IN_REVIEW, DeliveryEvent.CREATE_REVISION): DeliveryState.IN_REVIEW,  # D03
    (DeliveryState.IN_REVIEW, DeliveryEvent.REJECT): DeliveryState.IN_REVIEW,  # D04
    (DeliveryState.IN_REVIEW, DeliveryEvent.APPROVE): DeliveryState.APPROVED,  # D05
    (DeliveryState.APPROVED, DeliveryEvent.REVOKE): DeliveryState.IN_REVIEW,  # D06
    (DeliveryState.APPROVED, DeliveryEvent.CREATE_REVISION): DeliveryState.IN_REVIEW,  # D06
    (DeliveryState.APPROVED, DeliveryEvent.ENQUEUE): DeliveryState.QUEUED,  # D07
    (DeliveryState.QUEUED, DeliveryEvent.REVOKE): DeliveryState.IN_REVIEW,  # D08
    (DeliveryState.QUEUED, DeliveryEvent.CREATE_REVISION): DeliveryState.IN_REVIEW,  # D08
    (DeliveryState.QUEUED, DeliveryEvent.AUTHORIZE): DeliveryState.EXECUTING,  # D09
    (DeliveryState.QUEUED, DeliveryEvent.PREFLIGHT_BLOCK): DeliveryState.BLOCKED,  # D10
    (DeliveryState.EXECUTING, DeliveryEvent.RECEIPT_CREATED): DeliveryState.REPORTED_PUBLISHED,  # D11
    (DeliveryState.EXECUTING, DeliveryEvent.RECEIPT_NO_SIDE_EFFECT_RETRYABLE): DeliveryState.BLOCKED,  # D12
    (DeliveryState.EXECUTING, DeliveryEvent.RECEIPT_NO_SIDE_EFFECT_NON_RETRYABLE): DeliveryState.FAILED_FINAL,  # D13
    (DeliveryState.EXECUTING, DeliveryEvent.RECEIPT_UNKNOWN): DeliveryState.UNKNOWN,  # D14
    (DeliveryState.EXECUTING, DeliveryEvent.RECEIPT_TIMEOUT): DeliveryState.UNKNOWN,  # D14
    (DeliveryState.UNKNOWN, DeliveryEvent.RECEIPT_CREATED): DeliveryState.REPORTED_PUBLISHED,  # D15
    (DeliveryState.UNKNOWN, DeliveryEvent.RESOLVE_PUBLISHED): DeliveryState.REPORTED_PUBLISHED,  # D15
    (DeliveryState.UNKNOWN, DeliveryEvent.RESOLVE_NO_SIDE_EFFECT): DeliveryState.BLOCKED,  # D16
    (DeliveryState.REPORTED_PUBLISHED, DeliveryEvent.VERIFY_OK): DeliveryState.PUBLISHED,  # D17
    (DeliveryState.REPORTED_PUBLISHED, DeliveryEvent.VERIFY_MISMATCH): DeliveryState.UNKNOWN,  # D18
    (DeliveryState.BLOCKED, DeliveryEvent.SAFE_RETRY): DeliveryState.QUEUED,  # D19
    (DeliveryState.BLOCKED, DeliveryEvent.MARK_FAILED_FINAL): DeliveryState.FAILED_FINAL,  # D20
    (DeliveryState.DRAFT, DeliveryEvent.EXPIRE): DeliveryState.EXPIRED,  # D21
    (DeliveryState.IN_REVIEW, DeliveryEvent.EXPIRE): DeliveryState.EXPIRED,  # D21
    (DeliveryState.APPROVED, DeliveryEvent.EXPIRE): DeliveryState.EXPIRED,  # D21
    (DeliveryState.QUEUED, DeliveryEvent.EXPIRE): DeliveryState.EXPIRED,  # D21
    (DeliveryState.BLOCKED, DeliveryEvent.EXPIRE): DeliveryState.EXPIRED,  # D21
    (DeliveryState.DRAFT, DeliveryEvent.CANCEL): DeliveryState.CANCELLED,  # D22
    (DeliveryState.IN_REVIEW, DeliveryEvent.CANCEL): DeliveryState.CANCELLED,  # D22
    (DeliveryState.APPROVED, DeliveryEvent.CANCEL): DeliveryState.CANCELLED,  # D22
    (DeliveryState.QUEUED, DeliveryEvent.CANCEL): DeliveryState.CANCELLED,  # D22
    (DeliveryState.BLOCKED, DeliveryEvent.CANCEL): DeliveryState.CANCELLED,  # D22
    (DeliveryState.DRAFT, DeliveryEvent.SUPERSEDE): DeliveryState.SUPERSEDED,  # D23
    (DeliveryState.IN_REVIEW, DeliveryEvent.SUPERSEDE): DeliveryState.SUPERSEDED,  # D23
    (DeliveryState.APPROVED, DeliveryEvent.SUPERSEDE): DeliveryState.SUPERSEDED,  # D23
    (DeliveryState.QUEUED, DeliveryEvent.SUPERSEDE): DeliveryState.SUPERSEDED,  # D23
    (DeliveryState.LEGACY_UNVERIFIED, DeliveryEvent.LEGACY_VERIFY): DeliveryState.PUBLISHED,  # D24
    (DeliveryState.PUBLISHED, DeliveryEvent.VISIBILITY_CHANGE): DeliveryState.PUBLISHED,  # D25
}


_GUARDS: dict[TransitionKey, Guard] = {
    (None, DeliveryEvent.RESERVE): lambda ctx: _is_true(ctx, "target_available") and _is_true(ctx, "slot_not_cancelled"),
    (DeliveryState.DRAFT, DeliveryEvent.CREATE_REVISION): lambda ctx: _is_true(ctx, "revision_complete") and ctx.get("qc_status") not in {"FAIL", "QUARANTINED"},
    (DeliveryState.IN_REVIEW, DeliveryEvent.CREATE_REVISION): lambda ctx: _is_true(ctx, "if_match_matches"),
    (DeliveryState.IN_REVIEW, DeliveryEvent.REJECT): lambda ctx: _is_true(ctx, "revision_is_current"),
    (DeliveryState.IN_REVIEW, DeliveryEvent.APPROVE): lambda ctx: _guard_approve(ctx),
    (DeliveryState.APPROVED, DeliveryEvent.REVOKE): lambda ctx: _is_true(ctx, "no_execution_live"),
    (DeliveryState.APPROVED, DeliveryEvent.CREATE_REVISION): lambda ctx: _is_true(ctx, "no_execution_live"),
    (DeliveryState.APPROVED, DeliveryEvent.ENQUEUE): lambda ctx: _guard_enqueue(ctx),
    (DeliveryState.QUEUED, DeliveryEvent.REVOKE): lambda ctx: _is_true(ctx, "command_not_authorized"),
    (DeliveryState.QUEUED, DeliveryEvent.CREATE_REVISION): lambda ctx: _is_true(ctx, "command_not_authorized"),
    (DeliveryState.QUEUED, DeliveryEvent.AUTHORIZE): lambda ctx: _is_true(ctx, "preflight_pass"),
    (DeliveryState.QUEUED, DeliveryEvent.PREFLIGHT_BLOCK): lambda ctx: _is_true(ctx, "preflight_blocking"),
    (DeliveryState.EXECUTING, DeliveryEvent.RECEIPT_CREATED): lambda ctx: _is_true(ctx, "receipt_matches") and _is_true(ctx, "platform_post_id_valid"),
    (DeliveryState.EXECUTING, DeliveryEvent.RECEIPT_NO_SIDE_EFFECT_RETRYABLE): lambda ctx: _is_true(ctx, "error_class_verified"),
    (DeliveryState.EXECUTING, DeliveryEvent.RECEIPT_NO_SIDE_EFFECT_NON_RETRYABLE): lambda ctx: _is_true(ctx, "error_class_verified"),
    (DeliveryState.UNKNOWN, DeliveryEvent.RECEIPT_CREATED): lambda ctx: _is_true(ctx, "post_id_matches_page"),
    (DeliveryState.UNKNOWN, DeliveryEvent.RESOLVE_PUBLISHED): lambda ctx: _is_true(ctx, "post_id_matches_page"),
    (DeliveryState.UNKNOWN, DeliveryEvent.RESOLVE_NO_SIDE_EFFECT): lambda ctx: _has_text(ctx, "actor_id") and _has_text(ctx, "reason") and _has_text(ctx, "evidence"),
    (DeliveryState.REPORTED_PUBLISHED, DeliveryEvent.VERIFY_OK): lambda ctx: ctx.get("existence") == "EXISTS" and ctx.get("ownership") == "MATCH",
    (DeliveryState.REPORTED_PUBLISHED, DeliveryEvent.VERIFY_MISMATCH): lambda ctx: ctx.get("existence") in {"NOT_FOUND", "MISMATCH"},
    (DeliveryState.BLOCKED, DeliveryEvent.SAFE_RETRY): lambda ctx: _guard_safe_retry(ctx),
    (DeliveryState.BLOCKED, DeliveryEvent.MARK_FAILED_FINAL): lambda ctx: _has_text(ctx, "actor_id") and _has_text(ctx, "reason"),
    (DeliveryState.DRAFT, DeliveryEvent.EXPIRE): lambda ctx: _guard_expire(ctx),
    (DeliveryState.IN_REVIEW, DeliveryEvent.EXPIRE): lambda ctx: _guard_expire(ctx),
    (DeliveryState.APPROVED, DeliveryEvent.EXPIRE): lambda ctx: _guard_expire(ctx),
    (DeliveryState.QUEUED, DeliveryEvent.EXPIRE): lambda ctx: _guard_expire(ctx),
    (DeliveryState.BLOCKED, DeliveryEvent.EXPIRE): lambda ctx: _guard_expire(ctx),
    (DeliveryState.DRAFT, DeliveryEvent.CANCEL): lambda ctx: _is_true(ctx, "no_execution_live") and _has_text(ctx, "reason"),
    (DeliveryState.IN_REVIEW, DeliveryEvent.CANCEL): lambda ctx: _is_true(ctx, "no_execution_live") and _has_text(ctx, "reason"),
    (DeliveryState.APPROVED, DeliveryEvent.CANCEL): lambda ctx: _is_true(ctx, "no_execution_live") and _has_text(ctx, "reason"),
    (DeliveryState.QUEUED, DeliveryEvent.CANCEL): lambda ctx: _is_true(ctx, "no_execution_live") and _is_true(ctx, "command_not_authorized") and _has_text(ctx, "reason"),
    (DeliveryState.BLOCKED, DeliveryEvent.CANCEL): lambda ctx: _is_true(ctx, "no_execution_live") and _has_text(ctx, "reason"),
    (DeliveryState.DRAFT, DeliveryEvent.SUPERSEDE): lambda ctx: _guard_supersede(ctx),
    (DeliveryState.IN_REVIEW, DeliveryEvent.SUPERSEDE): lambda ctx: _guard_supersede(ctx),
    (DeliveryState.APPROVED, DeliveryEvent.SUPERSEDE): lambda ctx: _guard_supersede(ctx),
    (DeliveryState.QUEUED, DeliveryEvent.SUPERSEDE): lambda ctx: _guard_supersede(ctx),
    (DeliveryState.LEGACY_UNVERIFIED, DeliveryEvent.LEGACY_VERIFY): lambda ctx: _is_true(ctx, "post_id_matches_page"),
}


def transition_target(
    state: DeliveryState | None, event: DeliveryEvent
) -> DeliveryState:
    key = (state, event)
    try:
        return TRANSITIONS[key]
    except KeyError as exc:
        raise InvalidTransition(state, event) from exc


def guard_is_satisfied(
    state: DeliveryState | None,
    event: DeliveryEvent,
    context: Mapping[str, object] | None = None,
) -> bool:
    guard = _GUARDS.get((state, event))
    if guard is None:
        return True
    return guard(context or {})


def apply_transition(
    state: DeliveryState | None,
    event: DeliveryEvent,
    context: Mapping[str, object] | None = None,
) -> DeliveryState:
    target = transition_target(state, event)
    if not guard_is_satisfied(state, event, context):
        raise DomainError(
            ErrorCode.STATE_CONFLICT,
            "Điều kiện chuyển trạng thái chưa được đáp ứng.",
            {"from_state": state.value if state else None, "event": event.value},
        )
    return target


def _guard_approve(ctx: Mapping[str, object]) -> bool:
    deadline = ctx.get("deadline_at_ms")
    now = ctx.get("now_ms")
    return (
        _is_true(ctx, "payload_hash_matches")
        and ctx.get("qc_status") not in {"FAIL", "QUARANTINED"}
        and _is_true(ctx, "facts_valid_at_scheduled")
        and type(now) is int
        and type(deadline) is int
        and now < deadline
        and _is_true(ctx, "channel_enabled")
        and _is_true(ctx, "config_hash_matches")
    )


def _guard_enqueue(ctx: Mapping[str, object]) -> bool:
    scheduled = ctx.get("scheduled_at_ms")
    now = ctx.get("now_ms")
    deadline = ctx.get("deadline_at_ms")
    return (
        type(scheduled) is int
        and type(now) is int
        and type(deadline) is int
        and scheduled <= now <= deadline
        and ctx.get("mode") == "LIVE_MANUAL"
        and ctx.get("paused") is False
        and _is_true(ctx, "epoch_current")
    )


def _guard_safe_retry(ctx: Mapping[str, object]) -> bool:
    return all(
        _is_true(ctx, key)
        for key in (
            "no_execution_live",
            "all_prior_executions_no_side_effect",
            "window_open",
            "approval_valid",
        )
    )


def _guard_expire(ctx: Mapping[str, object]) -> bool:
    now = ctx.get("now_ms")
    deadline = ctx.get("deadline_at_ms")
    return type(now) is int and type(deadline) is int and now > deadline and _is_true(ctx, "no_execution_live")


def _guard_supersede(ctx: Mapping[str, object]) -> bool:
    return _is_true(ctx, "no_execution_live")


def _is_true(context: Mapping[str, object], key: str) -> bool:
    return context.get(key) is True


def _has_text(context: Mapping[str, object], key: str) -> bool:
    value = context.get(key)
    return isinstance(value, str) and bool(value.strip())
