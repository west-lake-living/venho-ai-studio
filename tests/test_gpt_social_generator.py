from __future__ import annotations

import json

import openai

from content_studio.generators import gpt_social_generator as gen_module
from content_studio.generators import social_prompts
from content_studio.schemas.content_request import ContentRequest


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeCompletion(self.response_text)


class _FakeChat:
    def __init__(self, response_text: str) -> None:
        self.completions = _FakeCompletions(response_text)


class _FakeOpenAI:
    def __init__(self, api_key: str, response_text: str = "") -> None:
        self.chat = _FakeChat(response_text)


class _FakePrompt:
    final_prompt = "TOPIC: mot ngay o Ho Tay"


def _request(*, lane: str = "daily", verified_events=None, dna_subject=None) -> ContentRequest:
    return ContentRequest(
        project="venho_hotel",
        content_type="facebook_post",
        topic="mot ngay o Ho Tay",
        target_audience="Vietnamese leisure guests",
        content_pillar="growth_agent",
        tone="warm, clear, trustworthy",
        lane=lane,
        verified_events=verified_events or [],
        dna_subject=dna_subject,
    )


def _patch_openai(monkeypatch, holder: dict, response_text: str) -> None:
    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda api_key: holder.setdefault("client", _FakeOpenAI(api_key, response_text)),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


def test_daily_lane_uses_brand_system_prompt(monkeypatch) -> None:
    holder: dict = {}
    _patch_openai(monkeypatch, holder, json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))

    gen_module.gpt_social_generator(_request(lane="daily"), _FakePrompt(), {})

    call = holder["client"].chat.completions.calls[0]
    assert call["model"] == "gpt-5.5"
    assert call["response_format"] == {"type": "json_object"}
    assert call["messages"][0] == {"role": "system", "content": social_prompts.SYSTEM_PROMPT}
    assert call["messages"][1]["content"] == "TOPIC: mot ngay o Ho Tay"


def test_saturday_lane_uses_weekend_events_prompt_and_appends_events(monkeypatch) -> None:
    holder: dict = {}
    _patch_openai(monkeypatch, holder, json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))

    events = [
        {
            "name": "Cho phien dem",
            "start_date": "2026-08-08",
            "end_date": "2026-08-09",
            "location": "Ho Tay",
            "description": "Cho dem cuoi tuan",
            "source_link": "https://example.com/event",
        }
    ]
    gen_module.gpt_social_generator(_request(lane="saturday_trend", verified_events=events), _FakePrompt(), {})

    call = holder["client"].chat.completions.calls[0]
    assert call["messages"][0]["content"] == social_prompts.WEEKEND_EVENTS_SYSTEM_PROMPT
    assert "Cho phien dem" in call["messages"][1]["content"]
    assert "TOPIC: mot ngay o Ho Tay" in call["messages"][1]["content"]


def test_saturday_lane_with_no_events_tells_model_none_verified(monkeypatch) -> None:
    holder: dict = {}
    _patch_openai(monkeypatch, holder, json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))

    gen_module.gpt_social_generator(_request(lane="saturday_trend", verified_events=[]), _FakePrompt(), {})

    call = holder["client"].chat.completions.calls[0]
    assert "không có sự kiện nào được xác thực" in call["messages"][1]["content"]


def test_west_lake_pillar_uses_west_lake_prompt(monkeypatch) -> None:
    holder: dict = {}
    _patch_openai(monkeypatch, holder, json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))

    gen_module.gpt_social_generator(_request(lane="daily", dna_subject="westlake"), _FakePrompt(), {})

    call = holder["client"].chat.completions.calls[0]
    assert call["messages"][0]["content"] == social_prompts.WEST_LAKE_SYSTEM_PROMPT


def test_non_west_lake_pillar_uses_brand_prompt(monkeypatch) -> None:
    holder: dict = {}
    _patch_openai(monkeypatch, holder, json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))

    gen_module.gpt_social_generator(_request(lane="daily", dna_subject="lake_view_room"), _FakePrompt(), {})

    call = holder["client"].chat.completions.calls[0]
    assert call["messages"][0]["content"] == social_prompts.SYSTEM_PROMPT


def test_saturday_lane_wins_over_west_lake_pillar(monkeypatch) -> None:
    """Priority: even if a Saturday special-topic entry uses dna_subject
    'westlake'/'outside', the weekend-events brief must still win."""
    holder: dict = {}
    _patch_openai(monkeypatch, holder, json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))

    gen_module.gpt_social_generator(
        _request(lane="saturday_trend", dna_subject="westlake", verified_events=[]), _FakePrompt(), {}
    )

    call = holder["client"].chat.completions.calls[0]
    assert call["messages"][0]["content"] == social_prompts.WEEKEND_EVENTS_SYSTEM_PROMPT


def test_missing_api_key_raises(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    try:
        gen_module.gpt_social_generator(_request(), _FakePrompt(), {})
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "OPENAI_API_KEY" in str(exc)
