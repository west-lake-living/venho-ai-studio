"""VAL-02 — multi-image vision support (candidate + reference photos in one call)."""

from __future__ import annotations

import pytest

from shared.vision.providers import openai_vision as ov


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]
        self.usage = None


class _FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse('{"ok": true}')


class _FakeChat:
    def __init__(self) -> None:
        self.completions = _FakeCompletions()


class _FakeOpenAI:
    def __init__(self, *args, **kwargs) -> None:
        self.chat = _FakeChat()


def test_analyze_many_builds_ordered_multi_image_payload(monkeypatch, tmp_path):
    monkeypatch.setattr(ov, "OpenAI", _FakeOpenAI)
    provider = ov.OpenAIVisionProvider(model="gpt-4o")

    candidate = tmp_path / "candidate.png"
    candidate.write_bytes(b"fake-candidate-bytes")
    ref1 = tmp_path / "ref1.png"
    ref1.write_bytes(b"fake-ref1-bytes")
    ref2 = tmp_path / "ref2.png"
    ref2.write_bytes(b"fake-ref2-bytes")

    result = provider.analyze_many(
        [candidate, ref1, ref2], "system prompt", text_prompt="compare these"
    )
    assert result == {"ok": True}

    call = provider.client.chat.completions.calls[0]
    content = call["messages"][1]["content"]
    assert len(content) == 4  # 3 image blocks + 1 text block
    assert [block["type"] for block in content] == ["image_url", "image_url", "image_url", "text"]
    assert content[-1] == {"type": "text", "text": "compare these"}
    # image order preserved: candidate first, then references in call order
    assert "fake-candidate-bytes".encode().hex() not in content[0]["image_url"]["url"]  # sanity: it's base64, not raw hex
    import base64
    assert base64.standard_b64encode(b"fake-candidate-bytes").decode() in content[0]["image_url"]["url"]
    assert base64.standard_b64encode(b"fake-ref1-bytes").decode() in content[1]["image_url"]["url"]
    assert base64.standard_b64encode(b"fake-ref2-bytes").decode() in content[2]["image_url"]["url"]


def test_analyze_single_image_still_works_via_analyze(monkeypatch, tmp_path):
    monkeypatch.setattr(ov, "OpenAI", _FakeOpenAI)
    provider = ov.OpenAIVisionProvider(model="gpt-4o")
    image = tmp_path / "solo.png"
    image.write_bytes(b"fake-solo-bytes")

    result = provider.analyze(image, "system prompt")
    assert result == {"ok": True}
    call = provider.client.chat.completions.calls[0]
    content = call["messages"][1]["content"]
    assert len(content) == 2  # 1 image block + 1 text block
    assert content[1] == {"type": "text", "text": "Analyze this image and return JSON only."}
