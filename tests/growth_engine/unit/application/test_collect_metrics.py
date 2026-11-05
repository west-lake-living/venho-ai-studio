from __future__ import annotations

# _synthetic: true — cần thay bằng fixture thật từ P0-T03/P0-T04.

from dataclasses import dataclass

import pytest

from growth_engine.adapters.outbound.meta.metrics_source import MetaMetricsSource
from growth_engine.application.analytics.collect_metrics import (
    CollectMetrics,
    MetricsCollectionTarget,
)
from growth_engine.application.dto import ChannelConfigView, MetricSpec, RawMetric
from growth_engine.domain.analytics.metric import MetricCheckpoint, ValueState
from growth_engine.bootstrap import build_container
from growth_engine.adapters.inbound.workers.jobs_lane import build_jobs_tasks
from growth_engine.adapters.inbound.workers.loop import WorkerLoop
from growth_engine.adapters.inbound.workers.publish_lane import build_publish_tasks
from growth_engine.settings import Settings


class Clock:
    def __init__(self, now_ms: int) -> None:
        self.value = now_ms

    def now_ms(self) -> int:
        return self.value


class Ids:
    def __init__(self) -> None:
        self.value = 0

    def new_id(self) -> str:
        self.value += 1
        return f"metric-{self.value}"


@dataclass
class MemoryMetricRepo:
    claimed: set[str]
    observations: list[object]

    def claim_collection(self, **kwargs):
        key = kwargs["business_key"]
        if key in self.claimed:
            return None
        self.claimed.add(key)
        return "job-synthetic", "lease-synthetic"

    def append(self, observations):
        self.observations.extend(observations)
        return len(observations)

    def complete_collection(self, *args, **kwargs):
        return True


class MemoryUow:
    def __init__(self, repo: MemoryMetricRepo) -> None:
        self.metrics = repo

    class Transaction:
        def __init__(self, repo: MemoryMetricRepo) -> None:
            self.metrics = repo

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def begin_immediate(self):
        return self.Transaction(self.metrics)


class MetricsSource:
    source_kind = "mock"

    def __init__(self, result: list[RawMetric] | None = None, error: Exception | None = None) -> None:
        self.result = result or []
        self.error = error
        self.calls = 0

    def fetch(self, channel, post_id, metrics):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


def _spec(name: str, field: str | None = None, scope: str = "post", period: str = "day") -> MetricSpec:
    return MetricSpec(name, field or f"provider_{name}", scope, period)


def _target(metrics: list[MetricSpec]) -> MetricsCollectionTarget:
    return MetricsCollectionTarget(
        delivery_id="delivery-synthetic",
        channel=ChannelConfigView("fb_hanoi", "page-synthetic", "facebook", "vXX.X"),
        post_id="post-synthetic",
        published_at_ms=1_000_000,
        checkpoint=MetricCheckpoint.H24,
        metrics=tuple(metrics),
    )


def test_missing_zero_and_error_are_stored_as_distinct_states_and_replay_is_idempotent() -> None:
    now_ms = 1_000_000 + 24 * 60 * 60 * 1000
    repo = MemoryMetricRepo(set(), [])
    source = MetricsSource(
        [
            RawMetric("zero", 0, "ZERO", now_ms),
            RawMetric("failed", None, "ERROR", now_ms, "RATE_LIMIT"),
        ]
    )
    collector = CollectMetrics(lambda: MemoryUow(repo), source, Ids(), Clock(now_ms))
    target = _target([_spec("missing"), _spec("zero"), _spec("failed")])

    result = collector.execute(target)
    replay = collector.execute(target)

    assert result.observation_count == 3
    assert replay.skipped_duplicate is True
    assert {item.metric: item.value_state for item in repo.observations} == {
        "missing": ValueState.UNAVAILABLE,
        "zero": ValueState.ZERO,
        "failed": ValueState.ERROR,
    }
    assert {item.metric: item.value for item in repo.observations} == {
        "missing": None,
        "zero": 0,
        "failed": None,
    }


def test_source_failure_records_errors_and_returns_without_raising() -> None:
    now_ms = 1_000_000 + 24 * 60 * 60 * 1000
    repo = MemoryMetricRepo(set(), [])
    source = MetricsSource(error=RuntimeError("synthetic provider failure"))
    collector = CollectMetrics(lambda: MemoryUow(repo), source, Ids(), Clock(now_ms))

    result = collector.execute(_target([_spec("reach"), _spec("shares")]))

    assert result.error_count == 2
    assert all(item.value_state is ValueState.ERROR for item in repo.observations)
    assert all(item.error_code == "SOURCE_ERROR" for item in repo.observations)


def test_checkpoint_must_match_post_age() -> None:
    now_ms = 1_000_000 + 30 * 60 * 60 * 1000
    collector = CollectMetrics(
        lambda: MemoryUow(MemoryMetricRepo(set(), [])), MetricsSource(), Ids(), Clock(now_ms)
    )
    with pytest.raises(ValueError, match="checkpoint"):
        collector.execute(_target([_spec("reach")]))


class FakeGraphClient:
    def __init__(self, payload: dict[str, object], object_payload: dict[str, object] | None = None) -> None:
        self.payload = payload
        self.object_payload = object_payload or {}
        self.calls: list[tuple[str, tuple[str, ...], str]] = []
        self.object_calls: list[tuple[str, tuple[str, ...]]] = []

    def get_insights(self, object_id: str, metrics: list[str], period: str | None):
        self.calls.append((object_id, tuple(metrics), period))
        return self.payload

    def get_object(self, object_id: str, fields: list[str]):
        self.object_calls.append((object_id, tuple(fields)))
        return self.object_payload


def test_meta_source_uses_latest_snapshot_without_summing_and_marks_missing_unavailable() -> None:
    client = FakeGraphClient(
        {
            "data": [
                {"name": "provider_reach", "values": [{"value": 4}, {"value": 9}]},
            ]
        }
    )
    source = MetaMetricsSource(lambda _channel: client, now_ms=lambda: 7)
    metrics = [_spec("reach"), _spec("comments")]

    result = source.fetch(
        ChannelConfigView("fb_hanoi", "page-synthetic", "facebook", "vXX.X"),
        "post-synthetic",
        metrics,
    )

    assert result[0].value == 9
    assert result[0].state == "VALUE"
    assert result[1].state == "UNAVAILABLE"
    assert client.calls == [
        ("post-synthetic", ("provider_reach",), "day"),
        ("post-synthetic", ("provider_comments",), "day"),
    ]


def test_meta_source_reads_instagram_media_metrics_by_media_id() -> None:
    client = FakeGraphClient(
        {"data": [{"name": "synthetic_reach", "values": [{"value": 17}]}]}
    )
    source = MetaMetricsSource(lambda _channel: client, now_ms=lambda: 7)
    channel = ChannelConfigView(
        "ig_venho", "ig-business-synthetic", "instagram", "v-synthetic"
    )

    result = source.fetch(
        channel,
        "ig-media-synthetic-123",
        [_spec("reach", "synthetic_reach")],
    )

    assert result[0].value == 17
    assert client.calls == [("ig-media-synthetic-123", ("synthetic_reach",), "day")]


def test_meta_source_returns_zero_null_and_provider_errors_separately() -> None:
    client = FakeGraphClient(
        {
            "data": [
                {"name": "provider_zero", "values": [{"value": 0}]},
                {"name": "provider_null", "values": [{"value": None}]},
            ]
        }
    )
    source = MetaMetricsSource(lambda _channel: client, now_ms=lambda: 7)
    result = source.fetch(
        ChannelConfigView("fb_hanoi", "page-synthetic", "facebook", "vXX.X"),
        "post-synthetic",
        [_spec("zero"), _spec("null"), _spec("unsupported", "REQUIRED_FROM_P0")],
    )

    assert [metric.state for metric in result] == ["ZERO", "NULL", "UNAVAILABLE"]
    assert len(client.calls) == 2


def test_facebook_engagement_fields_are_skipped_when_capability_is_blocked() -> None:
    spec = MetricSpec(
        "reactions_total",
        "reactions.summary(total_count).limit(0)",
        "post_field",
        None,
        capability="facebook_engagement",
        capability_state="BLOCKED",
    )
    source = MetaMetricsSource(
        lambda _channel: pytest.fail("BLOCKED capability must not create a Meta client"),
        now_ms=lambda: 7,
    )

    result = source.fetch(
        ChannelConfigView("fb_hanoi", "page-synthetic", "facebook", "vXX.X"),
        "post-synthetic",
        [spec],
    )

    assert result == [RawMetric("reactions_total", None, "UNAVAILABLE", 7)]


def test_facebook_engagement_fields_use_fixture_and_missing_shares_are_zero() -> None:
    client = FakeGraphClient(
        {"data": []},
        {
            "reactions": {"data": [], "summary": {"total_count": 2}},
            "comments": {"data": [], "summary": {"total_count": 1}},
        },
    )
    source = MetaMetricsSource(lambda _channel: client, now_ms=lambda: 7, min_interval_seconds=0)
    specs = [
        MetricSpec("reactions_total", "reactions.summary(total_count).limit(0)", "post_field", None,
                   capability="facebook_engagement", capability_state="SUPPORTED"),
        MetricSpec("comments_total", "comments.summary(total_count).limit(0)", "post_field", None,
                   capability="facebook_engagement", capability_state="SUPPORTED"),
        MetricSpec("shares", "shares", "post_field", None,
                   capability="facebook_engagement", capability_state="SUPPORTED", missing_value_state="ZERO"),
    ]

    result = source.fetch(
        ChannelConfigView("fb_hanoi", "page-synthetic", "facebook", "vXX.X"),
        "post-synthetic",
        specs,
    )

    assert [(row.name, row.value, row.state) for row in result] == [
        ("reactions_total", 2, "VALUE"),
        ("comments_total", 1, "VALUE"),
        ("shares", 0, "ZERO"),
    ]
    assert client.object_calls == [
        ("post-synthetic", ("reactions.summary(total_count).limit(0)",)),
        ("post-synthetic", ("comments.summary(total_count).limit(0)",)),
        ("post-synthetic", ("shares",)),
    ]
    assert client.calls == []


def test_meta_source_rate_limits_by_page_and_unsupported_metrics_do_not_call_provider() -> None:
    client = FakeGraphClient({"data": []})
    clock = [0.0]
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock[0] += seconds

    source = MetaMetricsSource(
        lambda _channel: client,
        now_ms=lambda: 7,
        monotonic=lambda: clock[0],
        sleep=sleep,
        min_interval_seconds=2,
    )
    channel = ChannelConfigView("fb_hanoi", "page-synthetic", "facebook", "vXX.X")
    spec = _spec("unsupported", "REQUIRED_FROM_P0")

    source.fetch(channel, "post-synthetic", [spec])
    source.fetch(channel, "post-synthetic", [spec])

    assert client.calls == []
    assert sleeps == []


def test_per_page_rate_limiter_waits_between_supported_requests() -> None:
    client = FakeGraphClient({"data": []})
    clock = [0.0]
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock[0] += seconds

    source = MetaMetricsSource(
        lambda _channel: client,
        now_ms=lambda: 7,
        monotonic=lambda: clock[0],
        sleep=sleep,
        min_interval_seconds=2,
    )
    channel = ChannelConfigView("fb_hanoi", "page-synthetic", "facebook", "vXX.X")
    source.fetch(channel, "post-synthetic", [_spec("first")])
    source.fetch(channel, "post-synthetic", [_spec("second")])

    assert len(client.calls) == 2
    assert sleeps == [2]


def test_production_composition_rejects_mock_metrics_source() -> None:
    settings = Settings(
        env="production",
        db_path="/tmp/growth-synthetic.db",
        media_root="/tmp/growth-synthetic-media",
        public_base_url="https://growth.example.invalid",
        capability_keys="synthetic-only",
    )
    with pytest.raises(ValueError, match="production composition requires a meta_graph"):
        build_container(settings, metrics_source=MetricsSource())


def test_metrics_job_failure_isolated_from_publish_lane() -> None:
    now_ms = 1_793_752_200_000  # synthetic 2026-11-04 07:30 ICT
    clock = Clock(now_ms)
    job_errors: list[str] = []
    publish_events: list[str] = []

    def fail_metrics():
        raise RuntimeError("synthetic collector failure")

    jobs = build_jobs_tasks(
        {
            "ensure_slots": lambda: None,
            "weekly": lambda: None,
            "fast": lambda: None,
            "metrics": fail_metrics,
        }
    )
    metrics_task = next(task for task in jobs if task.name == "metrics-collector")
    assert metrics_task.interval_s == 15 * 60
    WorkerLoop(
        jobs,
        clock,
        sleep=lambda seconds: setattr(clock, "value", clock.value + round(seconds * 1000)),
        on_error=lambda task, _error: job_errors.append(task.name),
    ).run_until(now_ms + 15 * 60 * 1000)
    assert job_errors == ["metrics-collector"]

    publish_tasks = build_publish_tasks(
        {
            "enqueue_due": lambda: publish_events.append("enqueue"),
            "expire_overdue": lambda: publish_events.append("expire"),
        }
    )
    WorkerLoop(
        publish_tasks,
        clock,
        sleep=lambda seconds: setattr(clock, "value", clock.value + round(seconds * 1000)),
    ).run_until(clock.now_ms() + 60_000)
    assert publish_events == ["enqueue", "enqueue", "expire"]
