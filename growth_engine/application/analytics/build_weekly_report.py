from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Mapping, Sequence

from growth_engine.domain.analytics.metric import ValueState


METRICS = (
    "reach",
    "post_media_view",
    "post_total_media_view_unique",
    "reactions_total",
    "comments_total",
    "shares",
    "reactions",
    "comments",
)


@dataclass(frozen=True)
class AnalyticsMetricSample:
    delivery_id: str
    channel_id: str
    page_name: str
    pillar: str
    image_kind: str
    metric: str
    value: int | None
    value_state: ValueState | None
    observed_at_ms: int | None
    channel_key: str = ""


def build_weekly_report(
    samples: Sequence[AnalyticsMetricSample], *, week_start: str, week_end: str, checkpoint: str,
    engagement_capabilities: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Build Page-scoped groups; missing observations never become zero."""
    latest: dict[tuple[str, str], AnalyticsMetricSample] = {}
    group_deliveries: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    group_channel_keys: dict[tuple[str, str, str, str], str] = {}
    for sample in samples:
        group_key = (sample.channel_id, sample.page_name, sample.pillar, sample.image_kind)
        group_deliveries[group_key].add(sample.delivery_id)
        if sample.channel_key:
            group_channel_keys[group_key] = sample.channel_key
        key = (sample.delivery_id, sample.metric)
        current = latest.get(key)
        if current is None or (sample.observed_at_ms or -1) >= (current.observed_at_ms or -1):
            latest[key] = sample

    by_group: dict[tuple[str, str, str, str], list[AnalyticsMetricSample]] = defaultdict(list)
    sample_by_delivery: dict[tuple[str, str, str, str, str], dict[str, AnalyticsMetricSample]] = defaultdict(dict)
    for sample in latest.values():
        group_key = (sample.channel_id, sample.page_name, sample.pillar, sample.image_kind)
        by_group[group_key].append(sample)
        sample_by_delivery[(*group_key, sample.delivery_id)][sample.metric] = sample

    groups: list[dict[str, object]] = []
    for group_key in sorted(group_deliveries):
        channel_id, page_name, pillar, image_kind = group_key
        delivery_ids = group_deliveries[group_key]
        sample_count = len(delivery_ids)
        group_metrics = by_group[group_key]
        reliability: dict[str, object] = {}
        effectiveness: dict[str, object] = {}
        for metric in METRICS:
            rows = [row for row in group_metrics if row.metric == metric]
            states = {state.value: 0 for state in ValueState}
            numeric: list[int] = []
            for row in rows:
                if row.value_state is None:
                    continue
                states[row.value_state.value] += 1
                if row.value_state in {ValueState.VALUE, ValueState.ZERO} and row.value is not None:
                    numeric.append(row.value)
            recorded = sum(states.values())
            reliability[metric] = {
                "recorded_samples": recorded,
                "missing_samples": max(0, sample_count - recorded),
                "value_samples": states[ValueState.VALUE.value],
                "zero_samples": states[ValueState.ZERO.value],
                "null_samples": states[ValueState.NULL.value],
                "unavailable_samples": states[ValueState.UNAVAILABLE.value],
                "error_samples": states[ValueState.ERROR.value],
                "coverage": (len(numeric) / sample_count) if sample_count else 0.0,
            }
            effectiveness[metric] = {
                "samples": len(numeric),
                "average": (sum(numeric) / len(numeric)) if numeric else None,
            }

        channel_key = group_channel_keys.get(group_key, channel_id)
        if channel_key.startswith("fb_"):
            configured_state = (engagement_capabilities or {}).get(
                channel_key, (engagement_capabilities or {}).get("default", "BLOCKED")
            )
            if str(configured_state).upper() != "SUPPORTED":
                engagement = {
                    "state": "UNAVAILABLE", "reason": "CAPABILITY_BLOCKED", "samples": 0, "average": None
                }
            else:
                rates: list[float] = []
                for delivery_id in delivery_ids:
                    values = sample_by_delivery.get((*group_key, delivery_id), {})
                    chosen = [
                        values.get("post_total_media_view_unique"),
                        values.get("reactions_total"),
                        values.get("comments_total"),
                        values.get("shares"),
                    ]
                    if any(
                        row is None or row.value_state not in {ValueState.VALUE, ValueState.ZERO}
                        for row in chosen
                    ):
                        continue
                    denominator = chosen[0].value
                    if denominator is None or denominator <= 0:
                        continue
                    interactions = sum(row.value or 0 for row in chosen[1:])
                    rates.append(interactions / denominator)
                engagement = {
                    "state": "VALUE" if rates else "UNAVAILABLE",
                    "reason": None if rates else "DATA_INCOMPLETE",
                    "samples": len(rates),
                    "average": (sum(rates) / len(rates)) if rates else None,
                }
        else:
            rates = []
            for delivery_id in delivery_ids:
                values = sample_by_delivery.get((*group_key, delivery_id), {})
                chosen = [values.get("reach"), values.get("reactions"), values.get("comments"), values.get("shares")]
                if any(row is None or row.value_state not in {ValueState.VALUE, ValueState.ZERO} for row in chosen):
                    continue
                denominator = chosen[0].value
                if denominator is None or denominator <= 0:
                    continue
                rates.append(sum(row.value or 0 for row in chosen[1:]) / denominator)
            engagement = {
                "state": "VALUE" if rates else "UNAVAILABLE",
                "reason": None if rates else "DATA_INCOMPLETE",
                "samples": len(rates),
                "average": (sum(rates) / len(rates)) if rates else None,
            }
        effectiveness["internal_engagement_rate"] = engagement

        groups.append(
            {
                "channel_id": channel_id,
                "page_name": page_name,
                "pillar": pillar,
                "image_kind": image_kind,
                "sample_count": sample_count,
                "comparison_allowed": sample_count >= 5,
                "comparison_note": None if sample_count >= 5 else "Ít hơn 5 bài: chỉ mô tả, không so sánh.",
                "operational_reliability": reliability,
                "content_effectiveness": effectiveness,
            }
        )
    return {
        "week_start": week_start,
        "week_end": week_end,
        "checkpoint": checkpoint,
        "source": "meta_graph",
        "groups": groups,
    }


def sample_from_mapping(row: Mapping[str, object]) -> AnalyticsMetricSample:
    state_value = row.get("value_state")
    state = ValueState(str(state_value)) if state_value is not None else None
    value = row.get("value")
    observed_at = row.get("observed_at_ms")
    return AnalyticsMetricSample(
        delivery_id=str(row["delivery_id"]),
        channel_id=str(row["channel_id"]),
        page_name=str(row["page_name"]),
        pillar=str(row["pillar"]),
        image_kind=str(row["image_kind"]),
        metric=str(row["metric"]),
        value=value if type(value) is int else None,
        value_state=state,
        observed_at_ms=observed_at if type(observed_at) is int else None,
        channel_key=str(row.get("channel_key") or row["channel_id"]),
    )
