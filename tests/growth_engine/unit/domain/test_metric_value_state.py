from __future__ import annotations

import pytest

from growth_engine.domain.analytics.metric import (
    MetricCheckpoint,
    MetricObservation,
    ValueState,
    checkpoint_for_age,
)


# Fixtures are synthetic; provider fields require evidence from P0-T04.
SYNTHETIC = {"_synthetic": True, "note": "cần thay bằng fixture thật từ P0-T03/P0-T04"}


def observation(state: ValueState, value: int | None, **overrides: object) -> MetricObservation:
    fields: dict[str, object] = {
        "id": "metric-synthetic-1",
        "delivery_id": "delivery-synthetic-1",
        "metric": "reach",
        "checkpoint": MetricCheckpoint.H24,
        "observed_at_ms": 2_000_000,
        "post_age_seconds": 86_400,
        "value": value,
        "value_state": state,
        "source": "meta_graph",
        "api_version": "REQUIRED_FROM_P0",
    }
    fields.update(overrides)
    return MetricObservation(**fields)  # type: ignore[arg-type]


def test_value_states_preserve_positive_zero_null_unavailable_and_error() -> None:
    assert observation(ValueState.VALUE, 17).value == 17
    assert observation(ValueState.ZERO, 0).value_state is ValueState.ZERO
    assert observation(ValueState.NULL, None).value_state is ValueState.NULL
    assert observation(ValueState.UNAVAILABLE, None).value_state is ValueState.UNAVAILABLE
    assert observation(ValueState.ERROR, None, error_code="synthetic_error").error_code == "synthetic_error"
    assert SYNTHETIC["_synthetic"] is True


@pytest.mark.parametrize(
    ("state", "value"),
    [
        (ValueState.VALUE, 0),
        (ValueState.VALUE, None),
        (ValueState.ZERO, 1),
        (ValueState.ZERO, None),
        (ValueState.NULL, 0),
        (ValueState.UNAVAILABLE, 1),
        (ValueState.ERROR, 1),
    ],
)
def test_state_value_mismatch_is_rejected(state: ValueState, value: int | None) -> None:
    with pytest.raises(ValueError):
        observation(state, value)


def test_checkpoints_require_age_within_tolerance_else_adhoc() -> None:
    assert checkpoint_for_age(22 * 3600) is MetricCheckpoint.H24
    assert checkpoint_for_age(26 * 3600) is MetricCheckpoint.H24
    assert checkpoint_for_age(70 * 3600) is MetricCheckpoint.H72
    assert checkpoint_for_age(166 * 3600) is MetricCheckpoint.D7
    assert checkpoint_for_age(20 * 3600) is MetricCheckpoint.ADHOC
    assert checkpoint_for_age(30 * 3600) is MetricCheckpoint.ADHOC


def test_checkpoint_age_rejects_negative_or_invalid_tolerance() -> None:
    with pytest.raises(ValueError):
        checkpoint_for_age(-1)
    with pytest.raises(ValueError):
        checkpoint_for_age(86_400, tolerance_seconds=-1)
