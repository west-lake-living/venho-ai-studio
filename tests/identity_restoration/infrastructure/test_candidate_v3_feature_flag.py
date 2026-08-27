from __future__ import annotations

import pytest

from identity_restoration.infrastructure.composition.env import read_restoration_env


FEATURE_FLAG = "IDR_CANDIDATE_V3_ENABLED"


def test_missing_candidate_v3_flag_defaults_to_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(FEATURE_FLAG, raising=False)

    assert read_restoration_env().candidate_v3_enabled is False


@pytest.mark.parametrize("value", ["false", "0", "off", "no", "FALSE", " Off "])
def test_explicit_false_values_disable_candidate_v3(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(FEATURE_FLAG, value)

    assert read_restoration_env().candidate_v3_enabled is False


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", "TRUE", " On "])
def test_explicit_true_values_enable_the_configuration_flag(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(FEATURE_FLAG, value)

    assert read_restoration_env().candidate_v3_enabled is True


def test_unknown_value_fails_closed_to_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(FEATURE_FLAG, "banana")

    assert read_restoration_env().candidate_v3_enabled is False

