from __future__ import annotations

import pytest

from analytics_feedback.attribution import (
    AttributionPolicy,
    attribute_conversion_event,
    build_content_performance_view,
    build_utm_content,
    dedupe_conversion_events,
    pseudonymize_contact,
)
from analytics_feedback.collection_scheduler import DEFAULT_WINDOWS
from analytics_feedback.metric_observation import assert_metrics_match_source, build_metric_observation
from analytics_feedback.meta_insights import build_metrics_adapter, meta_insights_enabled
from analytics_feedback.adapters.mock_metrics import MockMetricsAdapter


def _policy() -> AttributionPolicy:
    return AttributionPolicy(direct_window_hours=72, assisted_window_days=14, dedupe_fields=("normalized_contact_hash", "stay_date", "guest_count"))


def test_inquiry_with_utm_content_attributes_to_exact_publication() -> None:
    publication_id = "pub-p6-001"
    event = {
        "id": "conv-1",
        "event_type": "qualified_dm",
        "occurred_at": "2026-08-04T09:00:00Z",
        "utm_content": build_utm_content(publication_id),
        "normalized_contact_hash": pseudonymize_contact("+84901234567"),
        "stay_date": "2026-09-01",
        "guest_count": 2,
    }
    publications = [
        {"publication_id": publication_id, "published_at": "2026-08-03T09:00:00Z"},
        {"publication_id": "pub-p6-older", "published_at": "2026-07-25T09:00:00Z"},
    ]

    attributed = attribute_conversion_event(event, publications, _policy())

    assert attributed["publication_id"] == publication_id
    assert attributed["attribution_status"] == "direct"


def test_assisted_and_unattributed_windows_are_distinct() -> None:
    publications = [{"publication_id": "pub-p6-002", "published_at": "2026-08-01T00:00:00Z"}]
    assisted = attribute_conversion_event(
        {"id": "conv-2", "event_type": "phone_call", "occurred_at": "2026-08-07T00:00:00Z", "utm_content": None},
        publications,
        _policy(),
    )
    unattributed = attribute_conversion_event(
        {"id": "conv-3", "event_type": "phone_call", "occurred_at": "2026-09-01T00:00:00Z", "utm_content": None},
        publications,
        _policy(),
    )

    assert assisted["attribution_status"] == "assisted"
    assert assisted["publication_id"] == "pub-p6-002"
    assert unattributed["attribution_status"] == "unattributed"
    assert unattributed["publication_id"] is None


def test_conversion_dedupe_uses_policy_fields() -> None:
    base = {
        "event_type": "qualified_dm",
        "occurred_at": "2026-08-04T09:00:00Z",
        "normalized_contact_hash": pseudonymize_contact("guest@example.com"),
        "stay_date": "2026-09-01",
        "guest_count": 2,
    }
    events = [{**base, "id": "one"}, {**base, "id": "duplicate"}, {**base, "id": "different", "guest_count": 3}]

    unique = dedupe_conversion_events(events, _policy())

    assert [event["id"] for event in unique] == ["one", "different"]


def test_null_unavailable_and_zero_metric_states_are_distinct() -> None:
    raw = {"reach": 0, "clicks": None, "likes": 12}
    observation = build_metric_observation(
        publication_id="pub-p6-003",
        platform="facebook",
        window="24h",
        raw=raw,
        metric_names=["reach", "clicks", "shares", "likes"],
        observed_at="2026-08-04T09:00:00Z",
    )

    assert observation["metrics"]["reach"]["state"] == "ZERO"
    assert observation["metrics"]["clicks"]["state"] == "NULL"
    assert observation["metrics"]["shares"]["state"] == "UNAVAILABLE"
    assert observation["metrics"]["likes"]["state"] == "VALUE"
    assert_metrics_match_source(observation, raw)

    tampered = {**observation, "metrics": {**observation["metrics"], "likes": {**observation["metrics"]["likes"], "source_value": 99}}}
    with pytest.raises(ValueError, match="does not match source"):
        assert_metrics_match_source(tampered, raw)


def test_meta_insights_defaults_to_mock_and_p6_windows_include_required_set() -> None:
    assert {"1h", "24h", "72h", "7d", "28d"} <= set(DEFAULT_WINDOWS)
    assert meta_insights_enabled() is False
    assert isinstance(build_metrics_adapter("instagram"), MockMetricsAdapter)


def test_m10_content_performance_view_reads_m08_outputs_only() -> None:
    view = build_content_performance_view(
        snapshots=[
            {
                "snapshot_id": "snap-1",
                "package_id": "pkg-p6-001",
                "platform": "instagram",
                "metrics": {"reach": {"value": 100, "state": "VALUE"}},
            }
        ],
        scores=[{"snapshot_id": "snap-1", "performance_label": "NORMAL", "relative_score": 1.0}],
    )

    assert view["source"] == "M08"
    assert view["rows"][0]["publication_id"] == "pkg-p6-001"
    assert view["rows"][0]["performance_label"] == "NORMAL"
