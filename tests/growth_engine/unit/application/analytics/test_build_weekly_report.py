from __future__ import annotations

# _synthetic: true — cần thay bằng fixture thật từ P0-T03/P0-T04.

from growth_engine.application.analytics.build_weekly_report import (
    AnalyticsMetricSample,
    build_weekly_report,
)
from growth_engine.domain.analytics.metric import ValueState


def _sample(
    delivery: str,
    page: str,
    metric: str,
    value: int | None,
    state: ValueState | None,
) -> AnalyticsMetricSample:
    return AnalyticsMetricSample(
        delivery_id=delivery,
        channel_id=page,
        page_name=page,
        pillar="local_discovery",
        image_kind="ai_generated",
        metric=metric,
        value=value,
        value_state=state,
        observed_at_ms=10,
    )


def test_report_keeps_pages_separate_and_blocks_comparison_below_five_posts() -> None:
    samples: list[AnalyticsMetricSample] = []
    for index in range(5):
        delivery = f"hanoi-{index}"
        samples.extend(
            [
                _sample(delivery, "fb_hanoi", "post_total_media_view_unique", 0 if index == 4 else 10, ValueState.ZERO if index == 4 else ValueState.VALUE),
                _sample(delivery, "fb_hanoi", "reactions_total", 1, ValueState.VALUE),
                _sample(delivery, "fb_hanoi", "shares", 1, ValueState.VALUE),
            ]
        )
        if index == 0:
            samples.append(_sample(delivery, "fb_hanoi", "comments_total", 0, ValueState.ZERO))
        elif index == 1:
            samples.append(_sample(delivery, "fb_hanoi", "comments_total", None, ValueState.NULL))
        elif index == 2:
            samples.append(_sample(delivery, "fb_hanoi", "comments_total", None, ValueState.UNAVAILABLE))
        elif index == 3:
            samples.append(_sample(delivery, "fb_hanoi", "comments_total", None, ValueState.ERROR))

    samples.extend(
        [
            _sample("venho-1", "fb_venho", "post_total_media_view_unique", 100, ValueState.VALUE),
            _sample("venho-1", "fb_venho", "reactions_total", 1, ValueState.VALUE),
            _sample("venho-1", "fb_venho", "comments_total", 1, ValueState.VALUE),
            _sample("venho-1", "fb_venho", "shares", 1, ValueState.VALUE),
        ]
    )

    report = build_weekly_report(
        samples, week_start="2026-11-02", week_end="2026-11-08", checkpoint="7d",
        engagement_capabilities={"fb_hanoi": "SUPPORTED", "fb_venho": "SUPPORTED"},
    )

    by_page = {group["channel_id"]: group for group in report["groups"]}
    assert set(by_page) == {"fb_hanoi", "fb_venho"}
    assert by_page["fb_hanoi"]["sample_count"] == 5
    assert by_page["fb_hanoi"]["comparison_allowed"] is True
    assert by_page["fb_venho"]["sample_count"] == 1
    assert by_page["fb_venho"]["comparison_allowed"] is False
    assert by_page["fb_venho"]["content_effectiveness"]["post_total_media_view_unique"]["average"] == 100
    assert by_page["fb_venho"]["content_effectiveness"]["internal_engagement_rate"]["average"] == 0.03

    hanoi_comments = by_page["fb_hanoi"]["operational_reliability"]["comments_total"]
    assert hanoi_comments["zero_samples"] == 1
    assert hanoi_comments["null_samples"] == 1
    assert hanoi_comments["unavailable_samples"] == 1
    assert hanoi_comments["error_samples"] == 1
    assert hanoi_comments["missing_samples"] == 1
    assert by_page["fb_hanoi"]["content_effectiveness"]["comments_total"]["average"] == 0
    assert by_page["fb_hanoi"]["content_effectiveness"]["internal_engagement_rate"]["samples"] == 1


def test_facebook_engagement_is_unavailable_by_default() -> None:
    samples = [
        _sample("delivery-1", "fb_hanoi", "post_total_media_view_unique", 10, ValueState.VALUE),
        _sample("delivery-1", "fb_hanoi", "reactions_total", 2, ValueState.VALUE),
        _sample("delivery-1", "fb_hanoi", "comments_total", 1, ValueState.VALUE),
        _sample("delivery-1", "fb_hanoi", "shares", 0, ValueState.ZERO),
    ]

    report = build_weekly_report(samples, week_start="2026-11-02", week_end="2026-11-08", checkpoint="7d")

    engagement = report["groups"][0]["content_effectiveness"]["internal_engagement_rate"]
    assert engagement == {
        "state": "UNAVAILABLE", "reason": "CAPABILITY_BLOCKED", "samples": 0, "average": None
    }


def test_no_observations_produces_no_groups() -> None:
    report = build_weekly_report([], week_start="2026-11-02", week_end="2026-11-08", checkpoint="7d")
    assert report["groups"] == []
