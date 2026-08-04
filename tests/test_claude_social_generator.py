from __future__ import annotations

import json

import anthropic

from content_studio.generators import claude_social_generator as gen_module
from content_studio.generators import social_prompts
from content_studio.schemas.content_request import ContentRequest


class _FakeMessage:
    def __init__(self, text: str) -> None:
        # Real Anthropic responses can include a ThinkingBlock (type="thinking")
        # before the TextBlock (type="text") -- the generator must pick the
        # text block by type, not assume content[0] is text.
        self.content = [
            type("Block", (), {"type": "thinking", "text": "reasoning..."})(),
            type("Block", (), {"type": "text", "text": text})(),
        ]


class _FakeMessages:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeMessage(self.response_text)


class _FakeAnthropic:
    def __init__(self, api_key: str, response_text: str = "") -> None:
        self.messages = _FakeMessages(response_text)


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


def test_daily_lane_uses_brand_system_prompt(monkeypatch) -> None:
    holder = {}
    monkeypatch.setattr(
        anthropic,
        "Anthropic",
        lambda api_key: holder.setdefault(
            "client", _FakeAnthropic(api_key, json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))
        ),
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    gen_module.claude_social_generator(_request(lane="daily"), _FakePrompt(), {})

    call = holder["client"].messages.calls[0]
    assert call["system"] == social_prompts.SYSTEM_PROMPT
    assert call["messages"][0]["content"] == "TOPIC: mot ngay o Ho Tay"


def test_saturday_lane_uses_weekend_events_prompt_and_appends_events(monkeypatch) -> None:
    holder = {}
    monkeypatch.setattr(
        anthropic,
        "Anthropic",
        lambda api_key: holder.setdefault(
            "client", _FakeAnthropic(api_key, json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))
        ),
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

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
    gen_module.claude_social_generator(_request(lane="saturday_trend", verified_events=events), _FakePrompt(), {})

    call = holder["client"].messages.calls[0]
    assert call["system"] == social_prompts.WEEKEND_EVENTS_SYSTEM_PROMPT
    assert "Cho phien dem" in call["messages"][0]["content"]
    assert "TOPIC: mot ngay o Ho Tay" in call["messages"][0]["content"]


def test_saturday_lane_with_no_events_tells_claude_none_verified(monkeypatch) -> None:
    holder = {}
    monkeypatch.setattr(
        anthropic,
        "Anthropic",
        lambda api_key: holder.setdefault(
            "client", _FakeAnthropic(api_key, json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))
        ),
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    gen_module.claude_social_generator(_request(lane="saturday_trend", verified_events=[]), _FakePrompt(), {})

    call = holder["client"].messages.calls[0]
    assert "không có sự kiện nào được xác thực" in call["messages"][0]["content"]


def test_west_lake_pillar_uses_west_lake_prompt(monkeypatch) -> None:
    holder = {}
    monkeypatch.setattr(
        anthropic,
        "Anthropic",
        lambda api_key: holder.setdefault(
            "client", _FakeAnthropic(api_key, json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))
        ),
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    gen_module.claude_social_generator(_request(lane="daily", dna_subject="westlake"), _FakePrompt(), {})

    call = holder["client"].messages.calls[0]
    assert call["system"] == social_prompts.WEST_LAKE_SYSTEM_PROMPT
    assert call["messages"][0]["content"] == "TOPIC: mot ngay o Ho Tay"


def test_non_west_lake_pillar_uses_brand_prompt(monkeypatch) -> None:
    holder = {}
    monkeypatch.setattr(
        anthropic,
        "Anthropic",
        lambda api_key: holder.setdefault(
            "client", _FakeAnthropic(api_key, json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))
        ),
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    gen_module.claude_social_generator(_request(lane="daily", dna_subject="lake_view_room"), _FakePrompt(), {})

    call = holder["client"].messages.calls[0]
    assert call["system"] == social_prompts.SYSTEM_PROMPT


def test_saturday_lane_wins_over_west_lake_pillar(monkeypatch) -> None:
    """Priority: even if a Saturday special-topic entry uses dna_subject
    'westlake'/'outside', the weekend-events brief must still win."""
    holder = {}
    monkeypatch.setattr(
        anthropic,
        "Anthropic",
        lambda api_key: holder.setdefault(
            "client", _FakeAnthropic(api_key, json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))
        ),
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    gen_module.claude_social_generator(
        _request(lane="saturday_trend", dna_subject="westlake", verified_events=[]), _FakePrompt(), {}
    )

    call = holder["client"].messages.calls[0]
    assert call["system"] == social_prompts.WEEKEND_EVENTS_SYSTEM_PROMPT
