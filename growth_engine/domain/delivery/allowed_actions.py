from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping

from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.delivery.transitions import guard_is_satisfied
from growth_engine.domain.kernel.errors import ErrorCode


@dataclass(frozen=True)
class ActionView:
    action: str
    enabled: bool
    reason_code: str | None = None


_CONFLICT = ErrorCode.STATE_CONFLICT.value


def allowed_actions(
    delivery: Delivery,
    ctx: Mapping[str, object] | None = None,
) -> list[ActionView]:
    context = ctx or {}
    state = delivery.state
    if state is DeliveryState.DRAFT:
        return [_action("cancel", guard_is_satisfied(state, DeliveryEvent.CANCEL, context))]
    if state is DeliveryState.IN_REVIEW:
        return [
            _action("approve", guard_is_satisfied(state, DeliveryEvent.APPROVE, context)),
            _action("edit_caption", True),
            _action("replace_image", True),
            _action("rotate_image", True),
            _action("reject", guard_is_satisfied(state, DeliveryEvent.REJECT, context)),
            _action("cancel", guard_is_satisfied(state, DeliveryEvent.CANCEL, context)),
        ]
    if state is DeliveryState.APPROVED:
        editable = guard_is_satisfied(state, DeliveryEvent.CREATE_REVISION, context)
        return [
            _action("revoke", guard_is_satisfied(state, DeliveryEvent.REVOKE, context)),
            _action("edit_caption", editable),
            _action("replace_image", editable),
            _action("cancel", guard_is_satisfied(state, DeliveryEvent.CANCEL, context)),
        ]
    if state is DeliveryState.QUEUED:
        can_change = guard_is_satisfied(state, DeliveryEvent.REVOKE, context)
        return [
            _action("revoke", can_change),
            _action("cancel", can_change and guard_is_satisfied(state, DeliveryEvent.CANCEL, context)),
        ]
    if state in {DeliveryState.EXECUTING, DeliveryState.REPORTED_PUBLISHED}:
        return [_action("open_post", _has_permalink(delivery, context))] if _has_permalink(delivery, context) else []
    if state is DeliveryState.UNKNOWN:
        return [ActionView("reconcile", True)]
    if state is DeliveryState.BLOCKED:
        return [
            ActionView("view_reason", True),
            _action("safe_retry", guard_is_satisfied(state, DeliveryEvent.SAFE_RETRY, context)),
            _action("mark_failed", guard_is_satisfied(state, DeliveryEvent.MARK_FAILED_FINAL, context)),
            _action("cancel", guard_is_satisfied(state, DeliveryEvent.CANCEL, context)),
        ]
    if state is DeliveryState.PUBLISHED and _has_permalink(delivery, context):
        return [ActionView("open_post", True)]
    return []


def _action(action: str, enabled: bool) -> ActionView:
    return ActionView(action, enabled, None if enabled else _CONFLICT)


def _has_permalink(delivery: Delivery, context: Mapping[str, object]) -> bool:
    value = context.get("permalink", delivery.permalink)
    return isinstance(value, str) and bool(value.strip())
