import types
from pathlib import Path

import pytest

import prompt_studio.optimizer as optimizer_module
from prompt_studio.builders.image_prompt_builder import build_image_prompt
from prompt_studio.knowledge_reader import read_dna
from prompt_studio.optimizer import OptimizerDisabled, optimize
from shared.vision.errors import ProviderError, RetryExhausted

REAL_DNA = Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json")
BRIEF = "Create a realistic booking-style image of the lake view room."

SETTINGS = {
    "optimizer": {"enabled": True, "provider": "claude", "model": "claude-sonnet-4-6", "temperature": 0, "max_attempts": 2},
    "default_language": {"prompt_instructions": "en", "content_target": "vi"},
    "max_length": {"image": 1800, "video": 3200, "content": 2000, "seo": 2200},
}


def _contract():
    dna = read_dna(REAL_DNA)
    return build_image_prompt(dna, BRIEF, brief_slug="booking-style", generated_at="2026-07-08T00:00:00+00:00")


class _FakeMessages:
    def __init__(self, responses, calls):
        self._responses = list(responses)
        self.calls = calls

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return types.SimpleNamespace(content=[types.SimpleNamespace(text=response)])


def _fake_anthropic_factory(responses, calls):
    class _FakeAnthropic:
        def __init__(self, api_key):
            self.api_key = api_key
            self.messages = _FakeMessages(responses, calls)

    return _FakeAnthropic


def test_optimize_calls_claude_at_temperature_zero_and_only_changes_final_prompt(monkeypatch):
    calls = []
    monkeypatch.setattr(optimizer_module.anthropic, "Anthropic", _fake_anthropic_factory(["Polished wording."], calls))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    contract = _contract()
    optimized = optimize(contract, settings=SETTINGS)

    assert len(calls) == 1
    assert calls[0]["temperature"] == 0
    assert calls[0]["model"] == "claude-sonnet-4-6"
    assert calls[0]["messages"] == [{"role": "user", "content": contract.final_prompt}]

    assert optimized.final_prompt == "Polished wording."
    assert optimized.negative_prompt == contract.negative_prompt
    assert optimized.forbidden == contract.forbidden
    assert optimized.required_dna == contract.required_dna
    assert optimized.optimizer.used is True
    assert optimized.optimizer.provider == "claude"
    assert optimized.optimizer.temperature == 0


def test_optimize_retries_then_succeeds(monkeypatch):
    calls = []
    monkeypatch.setattr(
        optimizer_module.anthropic,
        "Anthropic",
        _fake_anthropic_factory([RuntimeError("transient"), "Polished after retry."], calls),
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(optimizer_module.time, "sleep", lambda *_: None)

    optimized = optimize(_contract(), settings=SETTINGS)

    assert len(calls) == 2
    assert optimized.final_prompt == "Polished after retry."


def test_optimize_raises_retry_exhausted_after_max_attempts(monkeypatch):
    calls = []
    monkeypatch.setattr(
        optimizer_module.anthropic,
        "Anthropic",
        _fake_anthropic_factory([RuntimeError("down"), RuntimeError("still down")], calls),
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(optimizer_module.time, "sleep", lambda *_: None)

    with pytest.raises(RetryExhausted):
        optimize(_contract(), settings=SETTINGS)
    assert len(calls) == 2


def test_optimize_raises_optimizer_disabled_when_config_says_so():
    disabled_settings = {**SETTINGS, "optimizer": {**SETTINGS["optimizer"], "enabled": False}}
    with pytest.raises(OptimizerDisabled):
        optimize(_contract(), settings=disabled_settings)


def test_optimize_raises_provider_error_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ProviderError):
        optimize(_contract(), settings=SETTINGS)
