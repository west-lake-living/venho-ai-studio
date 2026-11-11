from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
from types import SimpleNamespace

from growth_engine import bootstrap
from growth_engine.application.ops.meta_token_expiry import (
    MetaTokenExpiryMonitor,
    evaluate_meta_token_expiry,
)


def _ict_ms(day: str) -> int:
    local = datetime.combine(date.fromisoformat(day), time(12), ZoneInfo("Asia/Ho_Chi_Minh"))
    return int(local.astimezone(timezone.utc).timestamp() * 1000)


def test_doctor_warning_and_durable_alert_within_fourteen_days() -> None:
    report = evaluate_meta_token_expiry(
        {"IG_VENHO": "2027-01-10"},
        {"IG_VENHO": "2027-02-09"},
        now_ms=_ict_ms("2026-12-27"),
    )

    assert report.status == "WARN"
    assert "long-lived user token 2027-01-10 (14 ngày)" in report.detail
    assert len(report.alerts) == 1
    assert report.alerts[0].key == "meta-expiry:IG_VENHO:long-lived-user-token:2027-01-10"
    assert "GE_META_TOKEN_EXPIRY_IG_VENHO" in report.alerts[0].message


def test_doctor_exposes_the_expiry_warning(monkeypatch) -> None:
    target_ms = _ict_ms("2026-12-27")
    monkeypatch.setattr(bootstrap.time, "time_ns", lambda: target_ms * 1_000_000)
    service = bootstrap.DoctorService(
        SimpleNamespace(
            env="production",
            meta_token_expiries={"IG_VENHO": "2027-01-10"},
            meta_data_access_expiries={"IG_VENHO": "2027-02-09"},
        ),
        connect=lambda _path: None,
        migration_runner=lambda _path: None,
        sqlite_version_check=lambda _version: None,
        sqlite_version_error=ValueError,
    )

    check = service._meta_token_expiry_check()

    assert check.name == "Meta token expiry"
    assert check.status == "WARN"
    assert "2027-01-10" in check.detail


def test_no_expiry_warning_before_fourteen_day_window() -> None:
    report = evaluate_meta_token_expiry(
        {"IG_VENHO": "2027-01-10"},
        {"IG_VENHO": "2027-02-09"},
        now_ms=_ict_ms("2026-12-26"),
    )

    assert report.status == "PASS"
    assert report.alerts == ()


def test_missing_data_access_expiry_is_reported_without_inventing_a_date() -> None:
    report = evaluate_meta_token_expiry(
        {"IG_VENHO": "2027-01-10"},
        {},
        now_ms=_ict_ms("2026-11-11"),
    )

    assert report.status == "WARN"
    assert "GE_META_DATA_ACCESS_EXPIRY_IG_VENHO" in report.detail
    assert report.alerts == ()


def test_monitor_queues_one_deduplicated_message_per_due_expiry() -> None:
    class Queue:
        def __init__(self) -> None:
            self.items: dict[str, str] = {}

        def enqueue_unique(self, key: str, message: str, *, created_at_ms: int) -> None:
            assert created_at_ms == _ict_ms("2026-12-27")
            self.items.setdefault(key, message)

    queue = Queue()
    monitor = MetaTokenExpiryMonitor(
        {"IG_VENHO": "2027-01-10"},
        {"IG_VENHO": "2027-02-09"},
        queue,
        lambda: _ict_ms("2026-12-27"),
    )

    monitor.execute()
    monitor.execute()

    assert len(queue.items) == 1
    message = next(iter(queue.items.values()))
    assert "Meta IG_VENHO long-lived user token" in message
    assert "2027-01-10" in message
