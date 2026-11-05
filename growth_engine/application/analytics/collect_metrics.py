from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Sequence

from growth_engine.application.dto import ChannelConfigView, MetricSpec, RawMetric
from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.application.ports.platform import MetricsSource
from growth_engine.application.ports.uow import UnitOfWork
from growth_engine.domain.analytics.metric import (
    MetricCheckpoint,
    MetricObservation,
    ValueState,
    checkpoint_for_age,
)


_SAFE_ERROR_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_COLLECTOR_VERSION = "gc2-metrics-v1"
_JOB_LEASE_MS = 10 * 60 * 1000
_RETRY_DELAY_MS = 5 * 60 * 1000


@dataclass(frozen=True)
class MetricsCollectionTarget:
    delivery_id: str
    channel: ChannelConfigView
    post_id: str
    published_at_ms: int
    checkpoint: MetricCheckpoint
    metrics: tuple[MetricSpec, ...]

    def __post_init__(self) -> None:
        for name in ("delivery_id", "post_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if type(self.published_at_ms) is not int or self.published_at_ms < 0:
            raise ValueError("published_at_ms must be a non-negative integer")
        if not isinstance(self.checkpoint, MetricCheckpoint):
            raise ValueError("checkpoint must be a MetricCheckpoint")
        if len({metric.name for metric in self.metrics}) != len(self.metrics):
            raise ValueError("metric names must be unique per collection")


@dataclass(frozen=True)
class CollectMetricsResult:
    delivery_id: str
    checkpoint: MetricCheckpoint
    job_key: tuple[str, str, str]
    observation_count: int = 0
    error_count: int = 0
    skipped_duplicate: bool = False


class CollectMetrics:
    """Collect one checkpoint; provider I/O stays outside SQLite transactions."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        source: MetricsSource,
        ids: IdGenerator,
        clock: Clock,
        *,
        collector_version: str = _COLLECTOR_VERSION,
    ) -> None:
        if not collector_version.strip():
            raise ValueError("collector_version is required")
        self._uow_factory = uow_factory
        self._source = source
        self._ids = ids
        self._clock = clock
        self._collector_version = collector_version

    def execute(self, target: MetricsCollectionTarget) -> CollectMetricsResult:
        now_ms = self._clock.now_ms()
        if type(now_ms) is not int or now_ms < target.published_at_ms:
            raise ValueError("collector clock must be at or after publication")
        post_age_seconds = (now_ms - target.published_at_ms) // 1000
        actual_checkpoint = checkpoint_for_age(post_age_seconds)
        if actual_checkpoint is not target.checkpoint:
            raise ValueError("checkpoint does not match current post age")

        job_key = (target.delivery_id, target.checkpoint.value, self._collector_version)
        business_key = _business_key(job_key)
        with self._uow_factory().begin_immediate() as tx:
            lease = tx.metrics.claim_collection(
                job_id=self._ids.new_id(),
                business_key=business_key,
                now_ms=now_ms,
                lease_ms=_JOB_LEASE_MS,
            )
        if lease is None:
            return CollectMetricsResult(
                target.delivery_id,
                target.checkpoint,
                job_key,
                skipped_duplicate=True,
            )
        job_id, lease_token = lease

        source_failed = False
        try:
            raw_metrics = self._source.fetch(target.channel, target.post_id, list(target.metrics))
        except Exception:
            raw_metrics = [
                RawMetric(metric.name, None, ValueState.ERROR.value, now_ms, "SOURCE_ERROR")
                for metric in target.metrics
            ]
            source_failed = True
        observations = _to_observations(
            raw_metrics,
            target=target,
            now_ms=now_ms,
            post_age_seconds=post_age_seconds,
            source=_source_kind(self._source),
            api_version=target.channel.graph_api_version,
            ids=self._ids,
        )
        error_count = sum(item.value_state is ValueState.ERROR for item in observations)
        source_failed = source_failed or error_count > 0

        with self._uow_factory().begin_immediate() as tx:
            tx.metrics.append(observations)
            completed = tx.metrics.complete_collection(
                job_id,
                lease_token,
                now_ms=self._clock.now_ms(),
                failed=source_failed,
                retry_delay_ms=_RETRY_DELAY_MS,
            )
            if not completed:
                raise RuntimeError("metrics collection lease expired before result was saved")

        return CollectMetricsResult(
            target.delivery_id,
            target.checkpoint,
            job_key,
            observation_count=len(observations),
            error_count=error_count,
        )


def _business_key(job_key: tuple[str, str, str]) -> str:
    # JSON array encoding preserves the exact three-part key without delimiter collisions.
    import json

    return json.dumps(job_key, ensure_ascii=True, separators=(",", ":"))


def _source_kind(source: MetricsSource) -> str:
    value = getattr(source, "source_kind", "meta_graph")
    if value not in {"meta_graph", "mock"}:
        raise ValueError("metrics source_kind must be meta_graph or mock")
    return value


def _to_observations(
    raw_metrics: Sequence[RawMetric],
    *,
    target: MetricsCollectionTarget,
    now_ms: int,
    post_age_seconds: int,
    source: str,
    api_version: str,
    ids: IdGenerator,
) -> list[MetricObservation]:
    by_name: dict[str, RawMetric] = {}
    duplicates: set[str] = set()
    for raw in raw_metrics:
        if raw.name in by_name:
            duplicates.add(raw.name)
        by_name[raw.name] = raw

    observations: list[MetricObservation] = []
    for spec in target.metrics:
        raw = by_name.get(spec.name)
        state, value, error_code, observed_at_ms = _normalize_raw(raw, now_ms, duplicate=spec.name in duplicates)
        observations.append(
            MetricObservation(
                id=ids.new_id(),
                delivery_id=target.delivery_id,
                metric=spec.name,
                checkpoint=target.checkpoint,
                observed_at_ms=observed_at_ms,
                post_age_seconds=post_age_seconds,
                value=value,
                value_state=state,
                source=source,
                api_version=api_version,
                period=(
                    spec.period
                    if isinstance(spec.period, str) and "REQUIRED_FROM_P0" not in spec.period
                    else None
                ),
                dimensions={},
                error_code=error_code,
            )
        )
    return observations


def _normalize_raw(
    raw: RawMetric | None, now_ms: int, *, duplicate: bool
) -> tuple[ValueState, int | None, str | None, int]:
    if duplicate:
        return ValueState.ERROR, None, "DUPLICATE_METRIC", now_ms
    if raw is None:
        return ValueState.UNAVAILABLE, None, None, now_ms
    try:
        state = ValueState(raw.state)
    except (ValueError, TypeError):
        return ValueState.ERROR, None, "INVALID_STATE", now_ms
    value = raw.value
    if state is ValueState.VALUE and (type(value) is not int or value <= 0):
        return ValueState.ERROR, None, "INVALID_VALUE", raw.observed_at_ms
    if state is ValueState.ZERO and (type(value) is not int or value != 0):
        return ValueState.ERROR, None, "INVALID_VALUE", raw.observed_at_ms
    if state not in {ValueState.VALUE, ValueState.ZERO} and value is not None:
        return ValueState.ERROR, None, "INVALID_VALUE", raw.observed_at_ms
    if type(raw.observed_at_ms) is not int or raw.observed_at_ms < 0:
        return ValueState.ERROR, None, "INVALID_TIMESTAMP", now_ms
    error_code = None
    if state is ValueState.ERROR:
        code = raw.error_code or "SOURCE_ERROR"
        error_code = code if _SAFE_ERROR_CODE.fullmatch(code) else "SOURCE_ERROR"
    return state, value, error_code, raw.observed_at_ms
