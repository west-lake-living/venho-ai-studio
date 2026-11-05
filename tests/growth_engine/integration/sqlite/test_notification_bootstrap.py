from __future__ import annotations

from pathlib import Path

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

