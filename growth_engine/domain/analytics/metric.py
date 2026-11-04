from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class ValueState(str, Enum):
    VALUE = "VALUE"
    ZERO = "ZERO"
    NULL = "NULL"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


class MetricCheckpoint(str, Enum):
    H24 = "24h"
    H72 = "72h"
    D7 = "7d"
    ADHOC = "adhoc"


_CHECKPOINT_AGES = (
    (MetricCheckpoint.H24, 24 * 60 * 60),
    (MetricCheckpoint.H72, 72 * 60 * 60),
    (MetricCheckpoint.D7, 7 * 24 * 60 * 60),
)
_DEFAULT_TOLERANCE_SECONDS = 2 * 60 * 60
_METRIC_NAME = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def checkpoint_for_age(post_age_seconds: int, *, tolerance_seconds: int = _DEFAULT_TOLERANCE_SECONDS) -> MetricCheckpoint:
    if type(post_age_seconds) is not int or post_age_seconds < 0:
        raise ValueError("post_age_seconds must be a non-negative integer")
    if type(tolerance_seconds) is not int or tolerance_seconds < 0:
        raise ValueError("tolerance_seconds must be a non-negative integer")
    nearest: tuple[int, MetricCheckpoint] | None = None
    for checkpoint, expected_age in _CHECKPOINT_AGES:
        difference = abs(post_age_seconds - expected_age)
        if difference <= tolerance_seconds and (nearest is None or difference < nearest[0]):
            nearest = (difference, checkpoint)
    return nearest[1] if nearest is not None else MetricCheckpoint.ADHOC


@dataclass(frozen=True)
class MetricObservation:
    id: str
    delivery_id: str
    metric: str
    checkpoint: MetricCheckpoint
    observed_at_ms: int
    post_age_seconds: int
    value: int | None
    value_state: ValueState
    source: str
    api_version: str
    period: str | None = None
    dimensions: Mapping[str, object] = field(default_factory=dict)
    error_code: str | None = None

    def __post_init__(self) -> None:
        for name, value in (("id", self.id), ("delivery_id", self.delivery_id), ("api_version", self.api_version)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if not isinstance(self.metric, str) or not _METRIC_NAME.fullmatch(self.metric):
            raise ValueError("metric must be a lowercase internal identifier")
        if not isinstance(self.checkpoint, MetricCheckpoint):
            raise ValueError("checkpoint must be a MetricCheckpoint")
        if self.checkpoint is not checkpoint_for_age(self.post_age_seconds):
            raise ValueError("checkpoint label does not match post age tolerance")
        if type(self.observed_at_ms) is not int or self.observed_at_ms < 0:
            raise ValueError("observed_at_ms must be a non-negative integer")
        if not isinstance(self.value_state, ValueState):
            raise ValueError("value_state must be a ValueState")
        if self.source not in {"meta_graph", "mock"}:
            raise ValueError("source must be meta_graph or mock")
        if self.value_state is ValueState.VALUE:
            if type(self.value) is not int or self.value <= 0:
                raise ValueError("VALUE requires a positive integer value")
        elif self.value_state is ValueState.ZERO:
            if type(self.value) is not int or self.value != 0:
                raise ValueError("ZERO requires value 0")
        elif self.value is not None:
            raise ValueError(f"{self.value_state.value} requires value None")
        if self.period is not None and not self.period.strip():
            raise ValueError("period must be non-empty when supplied")
