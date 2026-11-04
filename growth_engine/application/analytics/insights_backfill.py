from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from statistics import mean
from typing import Mapping, Optional, Protocol, Sequence


class MetricValueState(str, Enum):
    VALUE = "VALUE"
    ZERO = "ZERO"
    NULL = "NULL"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


@dataclass(frozen=True)
class MetricDefinition:
    metric: str
    provider_metric: str
    period: str


@dataclass(frozen=True)
class MetricSample:
    value_state: MetricValueState
    value: Optional[int] = None
    error_code: Optional[str] = None

    def __post_init__(self) -> None:
        if self.value_state is MetricValueState.VALUE and (self.value is None or self.value <= 0):
            raise ValueError("VALUE requires a positive integer")
        if self.value_state is MetricValueState.ZERO and self.value != 0:
            raise ValueError("ZERO requires value 0")
        if self.value_state not in (MetricValueState.VALUE, MetricValueState.ZERO) and self.value is not None:
            raise ValueError("non-numeric value states must not carry a value")


@dataclass(frozen=True)
class BackfillTarget:
    channel_id: str
    delivery_id: str
    post_id: str
    published_at_ms: int
    api_version: str
    pillar: str
    image_kind: str
    manual: bool = False
    reconcile_status: str = "TRACKED"


@dataclass(frozen=True)
class MetricObservation:
    id: str
    delivery_id: str
    metric: str
    checkpoint: str
    observed_at: int
    post_age_seconds: int
    value: Optional[int]
    value_state: MetricValueState
    source: str
    api_version: str
    period: Optional[str]
    dimensions_json: str
    error_code: Optional[str]


@dataclass(frozen=True)
class SkippedTarget:
    channel_id: str
    delivery_id: str
    post_id: str
    reason: str


@dataclass(frozen=True)
class BackfillResult:
    observations: list[MetricObservation]
    skipped: list[SkippedTarget]


class MetricReader(Protocol):
    def read_metrics(
        self,
        target: BackfillTarget,
        definitions: Sequence[MetricDefinition],
    ) -> Mapping[str, MetricSample]:
        """Return values keyed by internal metric name using verified provider fields."""


@dataclass(frozen=True)
class MetricSummary:
    metric: str
    sample_count: int
    average_value: Optional[float]


@dataclass(frozen=True)
class ReportGroup:
    channel_id: str
    pillar: str
    image_kind: str
    sample_count: int
    mode: str
    metrics: tuple[MetricSummary, ...]
    manual_delivery_ids: tuple[str, ...]

    @property
    def manual_label(self) -> Optional[str]:
        return "đăng tay" if self.manual_delivery_ids else None


@dataclass(frozen=True)
class WeeklyReport:
    groups: tuple[ReportGroup, ...]


def backfill_insights(
    targets: Sequence[BackfillTarget],
    definitions: Sequence[MetricDefinition],
    reader: MetricReader,
    *,
    observed_at_ms: int,
) -> BackfillResult:
    if observed_at_ms < 0:
        raise ValueError("observed_at_ms must be non-negative")
    if any(not definition.metric.strip() or not definition.provider_metric.strip() or not definition.period.strip() for definition in definitions):
        raise ValueError("metric definitions must come from verified configuration")

    observations: list[MetricObservation] = []
    skipped: list[SkippedTarget] = []
    for target in targets:
        status = target.reconcile_status.upper()
        if status in {"PLACEHOLDER", "DELETED"}:
            skipped.append(SkippedTarget(target.channel_id, target.delivery_id, target.post_id, status))
            continue
        if not target.api_version.strip() or target.api_version.lower() == "latest" or target.api_version == "REQUIRED_FROM_P0":
            raise ValueError("a pinned Meta Graph API version is required")
        try:
            samples = reader.read_metrics(target, definitions)
        except Exception as exc:
            error_code = getattr(exc, "error_code", None)
            samples = {
                definition.metric: MetricSample(MetricValueState.ERROR, error_code=error_code)
                for definition in definitions
            }
        age_seconds = max(0, (observed_at_ms - target.published_at_ms) // 1000)
        dimensions = json.dumps(
            {
                "channel_id": target.channel_id,
                "pillar": target.pillar,
                "image_kind": target.image_kind,
                "manual": target.manual,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        for definition in definitions:
            sample = samples.get(definition.metric, MetricSample(MetricValueState.NULL))
            if not isinstance(sample, MetricSample):
                sample = MetricSample(MetricValueState.ERROR)
            key = f"{target.delivery_id}\0{definition.metric}\0adhoc\0{observed_at_ms}\0meta_graph"
            row_id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
            observations.append(
                MetricObservation(
                    id=row_id,
                    delivery_id=target.delivery_id,
                    metric=definition.metric,
                    checkpoint="adhoc",
                    observed_at=observed_at_ms,
                    post_age_seconds=age_seconds,
                    value=sample.value,
                    value_state=sample.value_state,
                    source="meta_graph",
                    api_version=target.api_version,
                    period=definition.period,
                    dimensions_json=dimensions,
                    error_code=sample.error_code,
                )
            )
    return BackfillResult(observations, skipped)


def build_weekly_report(
    observations: Sequence[MetricObservation],
    targets: Sequence[BackfillTarget],
    *,
    minimum_aggregate_samples: int = 5,
) -> WeeklyReport:
    if minimum_aggregate_samples < 1:
        raise ValueError("minimum_aggregate_samples must be positive")
    target_by_channel_delivery = {
        (target.channel_id, target.delivery_id): target for target in targets
    }
    grouped: dict[tuple[str, str, str], list[tuple[MetricObservation, BackfillTarget]]] = {}
    for observation in observations:
        try:
            channel_id = json.loads(observation.dimensions_json).get("channel_id")
        except (TypeError, json.JSONDecodeError):
            continue
        target = target_by_channel_delivery.get((channel_id, observation.delivery_id))
        if target is None:
            continue
        key = (target.channel_id, target.pillar, target.image_kind)
        grouped.setdefault(key, []).append((observation, target))

    report_groups: list[ReportGroup] = []
    for (channel_id, pillar, image_kind), rows in sorted(grouped.items()):
        unique_targets = {target.delivery_id: target for _, target in rows}
        sample_count = len(unique_targets)
        metric_values: dict[str, list[int]] = {}
        for observation, _ in rows:
            if observation.value_state in (MetricValueState.VALUE, MetricValueState.ZERO) and observation.value is not None:
                metric_values.setdefault(observation.metric, []).append(observation.value)
        summaries = tuple(
            MetricSummary(
                metric=metric,
                sample_count=len(values),
                average_value=mean(values) if sample_count >= minimum_aggregate_samples and len(values) >= minimum_aggregate_samples else None,
            )
            for metric, values in sorted(metric_values.items())
        )
        manual_ids = tuple(sorted(target.delivery_id for target in unique_targets.values() if target.manual))
        report_groups.append(
            ReportGroup(
                channel_id=channel_id,
                pillar=pillar,
                image_kind=image_kind,
                sample_count=sample_count,
                mode="aggregate" if sample_count >= minimum_aggregate_samples else "descriptive_only",
                metrics=summaries,
                manual_delivery_ids=manual_ids,
            )
        )
    return WeeklyReport(tuple(report_groups))
