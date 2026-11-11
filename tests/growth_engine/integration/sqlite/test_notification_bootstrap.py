from __future__ import annotations

from datetime import date, datetime, time, timezone
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

from growth_engine.bootstrap import build_container
from growth_engine.settings import Settings


def _task_names(container) -> tuple[set[str], set[str]]:
    return (
        {task.name for task in container.publish_lane._loop._tasks},
        {task.name for task in container.jobs_lane._loop._tasks},
    )


def test_notification_services_are_composed_but_not_scheduled_without_external_credentials(
    tmp_path: Path,
) -> None:
    settings = Settings(
        env="test",
        db_path=str(tmp_path / "growth.sqlite"),
        media_root=str(tmp_path / "media"),
        public_base_url="https://growth.example.test",
        service_tokens="synthetic-only",
    )
    container = build_container(settings)
    container.migration_service.run(Path(settings.db_path), check=False)

    publish_names, jobs_names = _task_names(container)
    assert container.notification_queue is not None
    assert container.notifications is None
    assert container.reminders is not None
    assert "notifications" not in publish_names
    assert "review-reminders" not in jobs_names
    assert "daily-digest" not in jobs_names


def test_notification_services_and_worker_ticks_are_composed_when_configured(tmp_path: Path) -> None:
    settings = Settings(
        env="test",
        db_path=str(tmp_path / "growth.sqlite"),
        media_root=str(tmp_path / "media"),
        public_base_url="https://growth.example.test",
        dashboard_base_url="https://dashboard.example.test",
        service_tokens="synthetic-only",
        telegram={"BOT_TOKEN": "synthetic-token", "CHAT_ID": "synthetic-chat"},
    )
    container = build_container(settings)
    container.migration_service.run(Path(settings.db_path), check=False)

    publish_names, jobs_names = _task_names(container)
    assert container.notifications is not None
    assert {"notifications"} <= publish_names
    assert {"review-reminders", "daily-digest"} <= jobs_names
    # Empty test database: processing reminder candidates performs no outbound call.
    assert container.reminders.tick(1_800_000_000_000) == ()


def test_production_expiry_monitor_warns_and_enqueues_deduplicated_telegram_notice(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database = tmp_path / "growth.sqlite"
    media = tmp_path / "media"
    media.mkdir()
    settings = Settings(
        env="production",
        db_path=str(database),
        media_root=str(media),
        public_base_url="https://growth.example.test",
        dashboard_base_url="https://dashboard.example.test",
        capability_keys="synthetic-kid:synthetic-key",
        service_tokens="make-ig:synthetic-hash",
        make_webhook_urls={"IG_VENHO": "https://hook.example.test/opaque"},
        meta_read_tokens={"IG_VENHO": "synthetic-meta-token"},
        meta_token_expiries={"IG_VENHO": "2027-01-10"},
        meta_data_access_expiries={"IG_VENHO": "2027-02-09"},
        telegram={"BOT_TOKEN": "synthetic-token", "CHAT_ID": "synthetic-chat"},
    )
    container = build_container(settings)
    container.migration_service.run(database, check=False)
    now = datetime.combine(date(2026, 12, 27), time(12), ZoneInfo("Asia/Ho_Chi_Minh"))
    now_ms = int(now.astimezone(timezone.utc).timestamp() * 1000)
    monkeypatch.setattr("growth_engine.bootstrap.time.time_ns", lambda: now_ms * 1_000_000)

    publish_names, _jobs_names = _task_names(container)
    assert "meta-token-expiry" in publish_names
    monitor_task = next(
        task for task in container.publish_lane._loop._tasks if task.name == "meta-token-expiry"
    )
    monitor_task.fn()
    report = container.doctor_service.run()
    expiry_check = next(check for check in report.checks if check.name == "Meta token expiry")

    assert expiry_check.status == "WARN"
    assert "2027-01-10" in expiry_check.detail
    connection = sqlite3.connect(database)
    try:
        notification_count = connection.execute(
            "SELECT count(*) FROM jobs WHERE kind='notify' AND business_key='meta-expiry:IG_VENHO:long-lived-user-token:2027-01-10'"
        ).fetchone()[0]
    finally:
        connection.close()
    assert notification_count == 1

