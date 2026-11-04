from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from growth_engine.adapters.inbound.workers.jobs_lane import build_jobs_tasks
from growth_engine.adapters.inbound.workers.loop import PeriodicTask, WorkerLoop
from growth_engine.application.content.run_lanes import (
    LanePackage,
    LaneTarget,
    RunLanes,
)
from growth_engine.application.scheduling.reserve_target import TargetAlreadyReserved
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryState


ICT = ZoneInfo("Asia/Ho_Chi_Minh")


class FakeClock:
    def __init__(self, value: datetime) -> None:
        self.current_ms = int(value.timestamp() * 1000)

    def now_ms(self) -> int:
        return self.current_ms

    def advance(self, seconds: float) -> None:
        self.current_ms += round(seconds * 1000)


def _ict_time(epoch_ms: int) -> str:
    return datetime.fromtimestamp(epoch_ms / 1000, timezone.utc).astimezone(ICT).strftime(
        "%a %H:%M"
    )


def test_jobs_worker_runs_ict_cron_tasks_at_the_scheduled_times_for_a_week():
    clock = FakeClock(datetime(2026, 11, 1, 17, 0, tzinfo=timezone.utc))  # Mon 00:00 ICT
    seen: dict[str, list[str]] = {"ensure_slots": [], "weekly": [], "fast": []}
    tasks = build_jobs_tasks(
        {
            name: (lambda key=name: seen[key].append(_ict_time(clock.now_ms())))
            for name in seen
        }
    )
    loop = WorkerLoop(tasks, clock, sleep=clock.advance)

    loop.run_until(clock.now_ms() + 7 * 24 * 60 * 60 * 1000)

    assert seen["ensure_slots"] == [
        "Mon 00:10",
        "Tue 00:10",
        "Wed 00:10",
        "Thu 00:10",
        "Fri 00:10",
        "Sat 00:10",
        "Sun 00:10",
    ]
    assert seen["weekly"] == ["Sun 20:00", "Sun 22:00"]
    assert "Mon 07:40" in seen["fast"] and "Mon 22:40" in seen["fast"]
    assert len(seen["fast"]) == 16 * 7


class FakeLaneStore:
    def __init__(self, targets: list[LaneTarget], recent: tuple[str, ...] = ()) -> None:
        self.targets = {target.target_id: target for target in targets}
        self.recent = recent
        self.refreshed: list[str] = []
        self.ensure_calls: list[tuple[int, int]] = []

    def ensure_slots(self, now_ms: int, *, horizon_days: int) -> None:
        self.ensure_calls.append((now_ms, horizon_days))

    def select_targets(self, lane: str, *, now_ms: int, horizon_days: int) -> list[LaneTarget]:
        self.selection_modes = getattr(self, "selection_modes", []) + [lane]
        return list(self.targets.values())

    def list_recent_topic_keys(self, since_ms: int) -> tuple[str, ...]:
        return self.recent

    def refresh_target(self, target_id: str) -> LaneTarget | None:
        self.refreshed.append(target_id)
        return self.targets.get(target_id)


class FakePackageFactory:
    def __init__(self, packages: list[LanePackage]) -> None:
        self.packages = iter(packages)
        self.requests: list[tuple[str, str, tuple[str, ...]]] = []

    def create(self, slot_id: str, lane: str, *, excluded_topic_keys: tuple[str, ...]) -> LanePackage:
        self.requests.append((slot_id, lane, excluded_topic_keys))
        return next(self.packages)


class FakeReserveTarget:
    def __init__(self, *, lose_for: str | None = None) -> None:
        self.lose_for = lose_for
        self.calls: list[tuple[str, str, str]] = []

    def execute(self, target_id: str, *, package_id: str, lane: str, correlation_id: str) -> object:
        self.calls.append((target_id, package_id, lane))
        if target_id == self.lose_for:
            raise TargetAlreadyReserved("another worker reserved this target")
        return object()


def _target(
    target_id: str,
    channel_id: str,
    *,
    state: DeliveryState | None = None,
    live_execution: bool = False,
    lane: str = "fast",
) -> LaneTarget:
    delivery = Delivery(f"delivery-{target_id}", state) if state is not None else None
    return LaneTarget(
        target_id=target_id,
        slot_id="slot-1",
        channel_id=channel_id,
        lane=lane,
        delivery=delivery,
        live_execution=live_execution,
    )


def _runner(store, package_factory, reserve, clock):
    return RunLanes(store, package_factory, reserve, clock)


def test_fast_lane_skips_published_page_a_and_reserves_only_unprocessed_page_b():
    clock = FakeClock(datetime(2026, 11, 4, 4, 0, tzinfo=timezone.utc))
    store = FakeLaneStore(
        [
            _target("target-a", "fb_hanoi", state=DeliveryState.PUBLISHED, lane="regular"),
            _target("target-b", "fb_venho", lane="regular"),
        ]
    )
    packages = FakePackageFactory([LanePackage("package-1", "topic-new")])
    reserve = FakeReserveTarget()

    result = _runner(store, packages, reserve, clock).run_fast(horizon_days=14)

    assert result.reserved_target_ids == ("target-b",)
    assert reserve.calls == [("target-b", "package-1", "regular")]
    assert store.ensure_calls == []


def test_fast_lane_rereads_target_after_reservation_race_without_creating_a_slot():
    clock = FakeClock(datetime(2026, 11, 4, 4, 0, tzinfo=timezone.utc))
    store = FakeLaneStore([_target("target-b", "fb_venho", lane="regular")])
    packages = FakePackageFactory([LanePackage("package-1", "topic-new")])
    reserve = FakeReserveTarget(lose_for="target-b")

    result = _runner(store, packages, reserve, clock).run_fast(horizon_days=14)

    assert result.raced_target_ids == ("target-b",)
    assert store.refreshed == ["target-b"]
    assert store.ensure_calls == []


def test_topic_key_used_in_last_120_days_is_not_reserved():
    clock = FakeClock(datetime(2026, 11, 4, 4, 0, tzinfo=timezone.utc))
    store = FakeLaneStore(
        [_target("target-b", "fb_venho", lane="regular")], recent=("topic-recent",)
    )
    packages = FakePackageFactory([LanePackage("package-1", "topic-recent")])
    reserve = FakeReserveTarget()

    result = _runner(store, packages, reserve, clock).run_fast(horizon_days=14)

    assert result.reserved_target_ids == ()
    assert result.duplicate_topic_slot_ids == ("slot-1",)
    assert packages.requests[0][2] == ("topic-recent",)
    assert reserve.calls == []


def test_replacement_lane_never_replaces_target_with_live_execution_or_published_delivery():
    clock = FakeClock(datetime(2026, 11, 4, 4, 0, tzinfo=timezone.utc))
    store = FakeLaneStore(
        [
            _target("live", "fb_hanoi", state=DeliveryState.UNKNOWN, live_execution=True, lane="replacement"),
            _target("published", "fb_venho", state=DeliveryState.PUBLISHED, lane="replacement"),
        ]
    )
    packages = FakePackageFactory([])
    reserve = FakeReserveTarget()

    result = _runner(store, packages, reserve, clock).run_replacement(horizon_days=14)

    assert result.skipped_target_ids == ("live", "published")
    assert reserve.calls == []
    assert packages.requests == []


def test_weekly_lane_ensures_two_weeks_and_reuses_one_package_for_all_page_targets():
    clock = FakeClock(datetime(2026, 11, 4, 4, 0, tzinfo=timezone.utc))
    store = FakeLaneStore(
        [
            _target("target-a", "fb_hanoi", lane="regular"),
            _target("target-b", "fb_venho", lane="regular"),
        ]
    )
    packages = FakePackageFactory([LanePackage("package-1", "topic-weekly")])
    reserve = FakeReserveTarget()

    result = _runner(store, packages, reserve, clock).run_weekly(horizon_days=14)

    assert store.ensure_calls == [(clock.now_ms(), 14)]
    assert store.selection_modes == ["weekly"]
    assert result.reserved_target_ids == ("target-a", "target-b")
    assert reserve.calls == [
        ("target-a", "package-1", "regular"),
        ("target-b", "package-1", "regular"),
    ]
    assert len(packages.requests) == 1


def test_replacement_lane_reserves_only_superseded_non_live_target():
    clock = FakeClock(datetime(2026, 11, 4, 4, 0, tzinfo=timezone.utc))
    store = FakeLaneStore(
        [
            _target("replacement", "fb_venho", state=DeliveryState.SUPERSEDED, lane="regular"),
            _target("live", "fb_hanoi", state=DeliveryState.EXECUTING, lane="regular"),
        ]
    )
    packages = FakePackageFactory([LanePackage("package-1", "replacement-topic")])
    reserve = FakeReserveTarget()

    result = _runner(store, packages, reserve, clock).run_replacement(horizon_days=14)

    assert result.reserved_target_ids == ("replacement",)
    assert result.skipped_target_ids == ("live",)
    assert reserve.calls == [("replacement", "package-1", "regular")]


def test_worker_records_task_errors_and_continues_to_next_task():
    clock = FakeClock(datetime(2026, 11, 1, 16, 0, tzinfo=timezone.utc))
    seen: list[str] = []
    errors: list[tuple[str, str]] = []
    tasks = (
        PeriodicTask("broken", lambda: (_ for _ in ()).throw(RuntimeError("boom")), interval_s=5),
        PeriodicTask("healthy", lambda: seen.append("ok"), interval_s=5),
    )
    loop = WorkerLoop(tasks, clock, sleep=clock.advance, on_error=lambda task, error: errors.append((task.name, str(error))))

    loop.run_until(clock.now_ms() + 5_000)

    assert seen == ["ok"]
    assert errors == [("broken", "boom")]
