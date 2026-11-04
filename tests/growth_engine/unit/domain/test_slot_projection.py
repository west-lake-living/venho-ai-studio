from __future__ import annotations

from datetime import date

import pytest

from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.scheduling.slot import Slot, SlotTarget
from growth_engine.domain.scheduling.slot_projection import (
    DeliveryProgress,
    SlotViewState,
    derive_slot_view,
)


def make_slot(*, cancelled_at_ms: int | None = None) -> Slot:
    return Slot(
        id="slot-synthetic-1",
        project_id="venho_hotel",
        local_date=date(2026, 11, 9),
        local_time="09:00",
        timezone="Asia/Ho_Chi_Minh",
        lane="regular",
        cadence_version="2",
        scheduled_at_ms=1_000,
        deadline_at_ms=1_801_000,
        cancelled_at_ms=cancelled_at_ms,
    )


def make_targets() -> tuple[SlotTarget, SlotTarget]:
    return (
        SlotTarget("target-a", "slot-synthetic-1", "page_a", required=True),
        SlotTarget("target-b", "slot-synthetic-1", "page_b", required=True),
    )


def progress(target_id: str, state: DeliveryState, **values: object) -> DeliveryProgress:
    return DeliveryProgress(target_id=target_id, state=state, **values)  # type: ignore[arg-type]


def test_cancelled_has_highest_projection_priority() -> None:
    view = derive_slot_view(
        make_slot(cancelled_at_ms=900),
        make_targets(),
        [progress("target-a", DeliveryState.UNKNOWN)],
        now_ms=9_000_000,
    )
    assert view.state is SlotViewState.CANCELLED


def test_page_b_unknown_overrides_partial_and_sets_attention_flag() -> None:
    view = derive_slot_view(
        make_slot(),
        make_targets(),
        [
            progress("target-a", DeliveryState.PUBLISHED),
            progress("target-b", DeliveryState.UNKNOWN),
        ],
        now_ms=2_000,
    )
    assert view.state is SlotViewState.NEEDS_ATTENTION
    assert view.attention_flags == ("PAGE_B_UNKNOWN",)
    assert view.progress == {"published": 1, "total": 2}


@pytest.mark.parametrize(
    ("state", "quality", "reported_at_ms", "now_ms", "expected_flag"),
    [
        (DeliveryState.BLOCKED, None, None, 2_000, "PAGE_A_BLOCKED"),
        (DeliveryState.FAILED_FINAL, None, None, 2_000, "PAGE_A_FAILED_FINAL"),
        (DeliveryState.PUBLISHED, "FAIL", None, 2_000, "PAGE_A_QUALITY_FAIL"),
        (DeliveryState.REPORTED_PUBLISHED, None, 1_000, 3_601_001, "PAGE_A_VERIFY_OVERDUE"),
    ],
)
def test_each_attention_condition_has_priority(
    state: DeliveryState,
    quality: str | None,
    reported_at_ms: int | None,
    now_ms: int,
    expected_flag: str,
) -> None:
    view = derive_slot_view(
        make_slot(),
        make_targets(),
        [progress("target-a", state, quality=quality, reported_at_ms=reported_at_ms)],
        now_ms=now_ms,
    )
    assert view.state is SlotViewState.NEEDS_ATTENTION
    assert expected_flag in view.attention_flags


def test_complete_counts_required_targets_only() -> None:
    targets = (*make_targets(), SlotTarget("optional", "slot-synthetic-1", "page_optional", required=False))
    view = derive_slot_view(
        make_slot(),
        targets,
        [
            progress("target-a", DeliveryState.PUBLISHED),
            progress("target-b", DeliveryState.PUBLISHED),
            progress("optional", DeliveryState.DRAFT),
        ],
        now_ms=2_000,
    )
    assert view.state is SlotViewState.COMPLETE
    assert view.progress == {"published": 2, "total": 2}


def test_partial_missed_ready_awaiting_review_and_planned_projection_branches() -> None:
    targets = make_targets()
    cases = [
        ([progress("target-a", DeliveryState.PUBLISHED), progress("target-b", DeliveryState.APPROVED)], 2_000, SlotViewState.PARTIAL),
        ([progress("target-a", DeliveryState.DRAFT), progress("target-b", DeliveryState.DRAFT)], 1_801_001, SlotViewState.MISSED),
        ([progress("target-a", DeliveryState.APPROVED), progress("target-b", DeliveryState.QUEUED)], 2_000, SlotViewState.READY),
        ([progress("target-a", DeliveryState.IN_REVIEW)], 2_000, SlotViewState.AWAITING_REVIEW),
        ([progress("target-a", DeliveryState.DRAFT)], 2_000, SlotViewState.PLANNED),
        ([], 2_000, SlotViewState.PLANNED),
    ]
    for deliveries, now_ms, expected in cases:
        view = derive_slot_view(make_slot(), targets, deliveries, now_ms=now_ms)
        assert view.state is expected


def test_live_execution_prevents_missed_projection_and_duplicate_target_delivery_is_rejected() -> None:
    live = derive_slot_view(
        make_slot(),
        make_targets(),
        [progress("target-a", DeliveryState.EXECUTING), progress("target-b", DeliveryState.QUEUED)],
        now_ms=1_801_001,
    )
    assert live.state is SlotViewState.READY
    with pytest.raises(ValueError, match="duplicate"):
        derive_slot_view(
            make_slot(),
            make_targets(),
            [progress("target-a", DeliveryState.DRAFT), progress("target-a", DeliveryState.PUBLISHED)],
            now_ms=2_000,
        )
