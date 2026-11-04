from __future__ import annotations

from typing import Mapping, Sequence

from growth_engine.adapters.outbound.analytics.sqlite_insights_repository import SQLiteInsightsRepository
from growth_engine.application.analytics.insights_backfill import (
    BackfillTarget,
    MetricDefinition,
    MetricSample,
    MetricValueState,
    backfill_insights,
    build_weekly_report,
)


_SYNTHETIC = {
    "_synthetic": True,
    "replacement_note": "cần thay bằng fixture thật từ P0-T03/P0-T04",
}
_DEFINITIONS = (
    MetricDefinition("metric_x", "provider_metric_x", "period_x"),
)


class FakeMetricReader:
    def __init__(self, samples: Mapping[str, Mapping[str, MetricSample]]) -> None:
        self.fixture = {**_SYNTHETIC, "samples": dict(samples)}
        self.samples = self.fixture["samples"]
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def read_metrics(
        self,
        target: BackfillTarget,
        definitions: Sequence[MetricDefinition],
    ) -> Mapping[str, MetricSample]:
        self.calls.append((target.delivery_id, tuple(item.metric for item in definitions)))
        return self.samples.get(target.post_id, {})


def _target(
    delivery_id: str,
    *,
    channel_id: str = "channel_a",
    post_id: str | None = None,
    pillar: str = "synthetic_pillar",
    image_kind: str = "synthetic_image",
    manual: bool = False,
    reconcile_status: str = "TRACKED",
) -> BackfillTarget:
    return BackfillTarget(
        channel_id=channel_id,
        delivery_id=delivery_id,
        post_id=post_id or "post-" + delivery_id,
        published_at_ms=1_000_000,
        api_version="vTEST",
        pillar=pillar,
        image_kind=image_kind,
        manual=manual,
        reconcile_status=reconcile_status,
    )


def test_value_zero_null_unavailable_and_error_stay_distinct() -> None:
    reader = FakeMetricReader(
        {
            "post-value": {"metric_x": MetricSample(MetricValueState.VALUE, 12)},
            "post-zero": {"metric_x": MetricSample(MetricValueState.ZERO, 0)},
            "post-unavailable": {"metric_x": MetricSample(MetricValueState.UNAVAILABLE)},
            "post-error": {"metric_x": MetricSample(MetricValueState.ERROR, error_code="synthetic_error")},
        }
    )
    targets = [
        _target("value", post_id="post-value"),
        _target("zero", post_id="post-zero"),
        _target("null", post_id="post-null"),
        _target("unavailable", post_id="post-unavailable"),
        _target("error", post_id="post-error"),
    ]

    result = backfill_insights(targets, _DEFINITIONS, reader, observed_at_ms=2_000_000)

    assert [row.value_state for row in result.observations] == [
        MetricValueState.VALUE,
        MetricValueState.ZERO,
        MetricValueState.NULL,
        MetricValueState.UNAVAILABLE,
        MetricValueState.ERROR,
    ]
    assert [row.value for row in result.observations] == [12, 0, None, None, None]
    assert all(row.source == "meta_graph" and row.checkpoint == "adhoc" for row in result.observations)
    assert all(row.api_version == "vTEST" and row.post_age_seconds == 1000 for row in result.observations)


def test_placeholder_and_deleted_targets_are_skipped_with_reasons() -> None:
    result = backfill_insights(
        [
            _target("placeholder", reconcile_status="PLACEHOLDER"),
            _target("deleted", reconcile_status="DELETED"),
        ],
        _DEFINITIONS,
        FakeMetricReader({}),
        observed_at_ms=2_000_000,
    )

    assert result.observations == []
    assert [item.reason for item in result.skipped] == ["PLACEHOLDER", "DELETED"]


def test_sqlite_unique_key_makes_same_backfill_replay_idempotent(tmp_path) -> None:
    reader = FakeMetricReader({"post-1": {"metric_x": MetricSample(MetricValueState.VALUE, 7)}})
    result = backfill_insights([_target("delivery-1")], _DEFINITIONS, reader, observed_at_ms=2_000_000)
    repository = SQLiteInsightsRepository(tmp_path / "insights.db")

    assert repository.append(result.observations) == 1
    assert repository.append(result.observations) == 0
    assert len(repository.load_all()) == 1
    repository.close()


def test_weekly_report_keeps_channels_separate_and_marks_small_samples_descriptive() -> None:
    reader = FakeMetricReader({
        "post-a": {"metric_x": MetricSample(MetricValueState.VALUE, 100)},
        "post-b": {"metric_x": MetricSample(MetricValueState.VALUE, 10)},
    })
    targets = [
        _target("delivery-a", channel_id="fb_hanoi", post_id="post-a", manual=True),
        _target("delivery-b", channel_id="fb_venho", post_id="post-b"),
    ]
    backfill = backfill_insights(targets, _DEFINITIONS, reader, observed_at_ms=2_000_000)

    report = build_weekly_report(backfill.observations, targets)

    assert len(report.groups) == 2
    assert {group.channel_id for group in report.groups} == {"fb_hanoi", "fb_venho"}
    assert all(group.sample_count == 1 and group.mode == "descriptive_only" for group in report.groups)
    hanoi = next(group for group in report.groups if group.channel_id == "fb_hanoi")
    assert hanoi.manual_label == "đăng tay"
    assert hanoi.metrics[0].average_value is None


def test_report_only_aggregates_metric_after_five_samples() -> None:
    targets = [_target(f"delivery-{i}", post_id=f"post-{i}") for i in range(5)]
    reader = FakeMetricReader(
        {
            target.post_id: {"metric_x": MetricSample(MetricValueState.VALUE, 10)}
            for target in targets
        }
    )
    backfill = backfill_insights(targets, _DEFINITIONS, reader, observed_at_ms=2_000_000)

    report = build_weekly_report(backfill.observations, targets)

    assert report.groups[0].sample_count == 5
    assert report.groups[0].mode == "aggregate"
    assert report.groups[0].metrics[0].average_value == 10
