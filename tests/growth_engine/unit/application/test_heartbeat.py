from __future__ import annotations

from datetime import datetime, timezone

import pytest

from growth_engine.adapters.inbound.workers.loop import WorkerLoop
from growth_engine.adapters.inbound.workers.publish_lane import build_publish_tasks
from growth_engine.application.ops.heartbeat import Heartbeat


class Clock:
    def __init__(self) -> None:
        self.value = int(datetime(2026, 11, 4, tzinfo=timezone.utc).timestamp() * 1000)

    def now_ms(self) -> int:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += round(seconds * 1000)


class Sender:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.urls: list[str] = []

    def ping(self, url: str) -> None:
        self.urls.append(url)
        if self.fail:
            raise RuntimeError("synthetic ping failure")


def _handlers(heartbeat, *, database=(True, 8), backup_fresh=None, enqueue=None):
    handlers = {
        "enqueue_due": enqueue or (lambda: None),
        "expire_overdue": lambda: None,
        "dispatch_outbox": lambda: None,
        "database_health": lambda: database,
        "heartbeat": heartbeat,
    }
    if backup_fresh is not None:
        handlers["backup_is_fresh"] = backup_fresh
    return handlers


def test_heartbeat_runs_only_after_scheduler_outbox_and_database_are_healthy() -> None:
    sender = Sender()
    heartbeat = Heartbeat("https://heartbeat.example.invalid/token", sender)
    clock = Clock()
    tasks = build_publish_tasks(_handlers(heartbeat.execute))

    WorkerLoop(tasks, clock, sleep=clock.advance).run_until(clock.now_ms() + 60_000)

    assert sender.urls == ["https://heartbeat.example.invalid/token"]


def test_database_failure_prevents_ping() -> None:
    sender = Sender()
    heartbeat = Heartbeat("https://heartbeat.example.invalid/token", sender)
    clock = Clock()
    tasks = build_publish_tasks(_handlers(heartbeat.execute, database=(False, None)))

    WorkerLoop(tasks, clock, sleep=clock.advance).run_until(clock.now_ms() + 60_000)

    assert sender.urls == []


def test_scheduler_failure_prevents_ping_and_ping_failure_does_not_stop_lane() -> None:
    sender = Sender(fail=True)
    heartbeat = Heartbeat("https://heartbeat.example.invalid/token", sender)
    clock = Clock()

    def broken_scheduler():
        raise RuntimeError("synthetic scheduler failure")

    tasks = build_publish_tasks(_handlers(heartbeat.execute, enqueue=broken_scheduler))
    loop = WorkerLoop(tasks, clock, sleep=clock.advance)
    loop.run_until(clock.now_ms() + 60_000)
    assert sender.urls == []

    healthy_clock = Clock()
    healthy_tasks = build_publish_tasks(_handlers(heartbeat.execute))
    healthy_loop = WorkerLoop(healthy_tasks, healthy_clock, sleep=healthy_clock.advance)
    healthy_loop.run_until(healthy_clock.now_ms() + 65_000)
    assert sender.urls
    # Heartbeat returns false on provider failure; the WorkerLoop does not stop.
    assert healthy_clock.now_ms() >= int(datetime(2026, 11, 4, tzinfo=timezone.utc).timestamp() * 1000) + 60_000


def test_stale_backup_suppresses_optional_heartbeat() -> None:
    sender = Sender()
    heartbeat = Heartbeat("https://heartbeat.example.invalid/token", sender)
    clock = Clock()
    tasks = build_publish_tasks(
        _handlers(heartbeat.execute, backup_fresh=lambda: False)
    )

    WorkerLoop(tasks, clock, sleep=clock.advance).run_until(clock.now_ms() + 60_000)

    assert sender.urls == []


def test_heartbeat_url_must_be_https() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        Heartbeat("http://heartbeat.example.invalid/token", Sender())
