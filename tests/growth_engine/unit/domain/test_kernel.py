from __future__ import annotations

from datetime import date, datetime, timezone
from dataclasses import FrozenInstanceError

import pytest

from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.kernel.events import DomainEvent
from growth_engine.domain.kernel.time import BusinessCalendar


def test_business_calendar_converts_ict_local_time_to_epoch_ms() -> None:
    calendar = BusinessCalendar()
    assert calendar.local_to_epoch_ms(date(2026, 11, 9), "09:00") == 1_794_189_600_000


def test_month_period_uses_ict_not_utc() -> None:
    calendar = BusinessCalendar(tz="Asia/Ho_Chi_Minh")
    epoch_ms = int(datetime(2026, 12, 31, 23, 30, tzinfo=timezone.utc).timestamp() * 1000)
    assert calendar.period_key(epoch_ms) == "2027-01"
    assert calendar.epoch_ms_to_local(epoch_ms).isoformat() == "2027-01-01T06:30:00+07:00"


def test_domain_error_preserves_code_message_and_details() -> None:
    error = DomainError(
        ErrorCode.VALIDATION,
        "Dữ liệu không hợp lệ.",
        {"field": "caption"},
    )
    assert error.code == "ERR_GC2_VALIDATION"
    assert error.message_vi == "Dữ liệu không hợp lệ."
    assert error.details == {"field": "caption"}
    assert str(error) == "Dữ liệu không hợp lệ."


def test_error_code_contains_all_plan_domain_codes() -> None:
    assert {item.value for item in ErrorCode} == {
        "ERR_GC2_UNAUTHENTICATED",
        "ERR_GC2_FORBIDDEN",
        "ERR_GC2_CAPABILITY_INVALID",
        "ERR_GC2_NOT_FOUND",
        "ERR_GC2_STATE_CONFLICT",
        "ERR_GC2_ALREADY_AUTHORIZED",
        "ERR_GC2_IDEMPOTENCY_MISMATCH",
        "ERR_GC2_TARGET_TAKEN",
        "ERR_GC2_RECEIPT_CONFLICT",
        "ERR_GC2_REVISION_CONFLICT",
        "ERR_GC2_VALIDATION",
        "ERR_GC2_QC_FAILED",
        "ERR_GC2_MEDIA_NOT_READY",
        "ERR_GC2_MEDIA_REJECTED",
        "ERR_GC2_FACT_EXPIRED",
        "ERR_GC2_DEADLINE_PASSED",
        "ERR_GC2_BUDGET_EXCEEDED",
        "ERR_GC2_PAYLOAD_TOO_LARGE",
        "ERR_GC2_DB_BUSY",
        "ERR_GC2_DEPENDENCY_UNAVAILABLE",
    }


def test_domain_event_is_immutable() -> None:
    event = DomainEvent(
        name="delivery.created",
        aggregate_id="delivery-1",
        at_ms=1_794_189_600_000,
        data={"channel_id": "fb_hanoi"},
    )
    assert event.data == {"channel_id": "fb_hanoi"}
    with pytest.raises(FrozenInstanceError):
        event.name = "delivery.changed"  # type: ignore[misc]
