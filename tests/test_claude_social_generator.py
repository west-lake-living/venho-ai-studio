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


class _OverloadedMessages(_FakeMessages):
    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) < 3:
            error = RuntimeError("Error code: 529 overloaded")
            error.status_code = 529
            raise error
        return _FakeMessage(self.response_text)


class _StatusMessages(_FakeMessages):
    def __init__(self, response_text: str, status_code: int) -> None:
        super().__init__(response_text)
        self.status_code = status_code

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            error = RuntimeError(f"Error code: {self.status_code}")
            error.status_code = self.status_code
            raise error
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
    assert call["model"] == gen_module.DEFAULT_CLAUDE_CONTENT_MODEL
    assert call["max_tokens"] == 4096
    assert call["system"] == social_prompts.SYSTEM_PROMPT
    assert call["messages"][0]["content"] == "TOPIC: mot ngay o Ho Tay"


def test_master_system_prompt_is_sent_with_json_contract(monkeypatch) -> None:
    holder = {}
    monkeypatch.setattr(
        anthropic,
        "Anthropic",
        lambda api_key: holder.setdefault(
            "client", _FakeAnthropic(api_key, json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))
        ),
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    gen_module.claude_social_generator(_request(), _FakePrompt(), {})

    system = holder["client"].messages.calls[0]["system"]
    assert "Senior Brand Content Strategist & Copywriter" in system
    assert "SELL THE DESTINATION BEFORE SELLING THE ROOM" in system
    assert "M05 AUTOMATION OUTPUT CONTRACT — HIGHEST PRIORITY" in system
    assert "Return ONLY one valid JSON object" in system


def test_content_model_can_be_overridden_for_the_anthropic_deployment(monkeypatch) -> None:
    holder = {}
    monkeypatch.setattr(
        anthropic,
        "Anthropic",
        lambda api_key: holder.setdefault(
            "client", _FakeAnthropic(api_key, json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))
        ),
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("CLAUDE_CONTENT_MODEL", "claude-3-opus-20240229")

    gen_module.claude_social_generator(_request(), _FakePrompt(), {})

    assert holder["client"].messages.calls[0]["model"] == "claude-3-opus-20240229"


def test_content_model_falls_back_when_env_var_is_set_but_empty(monkeypatch) -> None:
    """The growth-replace-rejected workflow always injects CLAUDE_CONTENT_MODEL
    (from `vars.CLAUDE_CONTENT_MODEL`), which is "" for an unset repo var --
    os.environ.get(key, default) does NOT fall back in that case, so a naive
    lookup sent model="" straight to Anthropic and every run 400'd
    (2026-08-13: "model: String should have at least 1 character")."""
    holder = {}
    monkeypatch.setattr(
        anthropic,
        "Anthropic",
        lambda api_key: holder.setdefault(
            "client", _FakeAnthropic(api_key, json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))
        ),
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("CLAUDE_CONTENT_MODEL", "")

    gen_module.claude_social_generator(_request(), _FakePrompt(), {})

    assert holder["client"].messages.calls[0]["model"] == gen_module.DEFAULT_CLAUDE_CONTENT_MODEL


def test_overloaded_opus_call_retries_with_backoff(monkeypatch) -> None:
    holder_client = _FakeAnthropic("test-key", json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))
    holder_client.messages = _OverloadedMessages(json.dumps({"title": "t", "hook": "h", "body": "b", "cta": "c"}))
    monkeypatch.setattr(anthropic, "Anthropic", lambda api_key: holder_client)
    monkeypatch.setattr(gen_module.time, "sleep", lambda seconds: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    result = gen_module.claude_social_generator(_request(), _FakePrompt(), {})

    assert result["title"] == "t"
    assert len(holder_client.messages.calls) == 3


def test_retry_queue_uses_bounded_jitter_for_a_transient_rate_limit(monkeypatch) -> None:
    messages = _StatusMessages(json.dumps({"title": "t"}), 429)
    client = type("Client", (), {"messages": messages})()
    delays: list[float] = []
    monkeypatch.setattr(gen_module.time, "sleep", delays.append)
    monkeypatch.setattr(gen_module.random, "uniform", lambda start, end: end)
    monkeypatch.setenv("ANTHROPIC_RETRY_BASE_SECONDS", "2")
    monkeypatch.setenv("ANTHROPIC_RETRY_MAX_SECONDS", "30")

    response = gen_module.create_anthropic_message(client, model="test")

    assert response.content[1].type == "text"
    assert len(messages.calls) == 2
    assert delays == [2.5]  # 2 seconds plus bounded 0.5-second jitter


def test_retry_queue_does_not_retry_non_transient_api_errors(monkeypatch) -> None:
    messages = _StatusMessages(json.dumps({"title": "t"}), 401)
    client = type("Client", (), {"messages": messages})()
    monkeypatch.setattr(gen_module.time, "sleep", lambda seconds: None)

    try:
        gen_module.create_anthropic_message(client, model="test")
    except RuntimeError as exc:
        assert "401" in str(exc)
    else:
        raise AssertionError("401 must fail without retry")
    assert len(messages.calls) == 1


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
