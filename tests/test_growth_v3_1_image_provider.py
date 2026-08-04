from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import pytest

from image_studio_runtime.adapters.gpt_image_provider import (
    GPTImageProvider,
    gpt_image_provider_from_env,
    map_api_quality,
    map_api_size,
)
from image_studio_runtime.application.generate_image import generate_image_run


class _FakeImageData:
    def __init__(self, b64_json: str | None) -> None:
        self.b64_json = b64_json


class _FakeResponse:
    def __init__(self, b64_json: str | None) -> None:
        self.data = [_FakeImageData(b64_json)]


class _FakeImagesAPI:
    def __init__(self, b64_json: str | None) -> None:
        self._b64_json = b64_json
        self.generate_calls: list[dict[str, Any]] = []
        self.edit_calls: list[dict[str, Any]] = []

    def generate(self, **kwargs: Any) -> _FakeResponse:
        self.generate_calls.append(kwargs)
        return _FakeResponse(self._b64_json)

    def edit(self, **kwargs: Any) -> _FakeResponse:
        self.edit_calls.append(kwargs)
        return _FakeResponse(self._b64_json)


class _FakeClient:
    def __init__(self, b64_json: str | None = None) -> None:
        self.images = _FakeImagesAPI(b64_json if b64_json is not None else base64.b64encode(b"PNGDATA").decode("ascii"))


def test_map_api_size_snaps_portrait_landscape_and_square() -> None:
    assert map_api_size("1024x1024") == "1024x1024"
    assert map_api_size("1024x1280") == "1024x1536"
    assert map_api_size("1280x1024") == "1536x1024"
    assert map_api_size("garbage") == "auto"


def test_map_api_quality_falls_back_to_medium_for_unknown() -> None:
    assert map_api_quality("high") == "high"
    assert map_api_quality("ultra") == "medium"


def test_generate_raises_when_disabled() -> None:
    provider = GPTImageProvider(enabled=False)
    with pytest.raises(RuntimeError, match="disabled by feature flag"):
        provider.generate("a prompt", size="1024x1024", quality="medium")


def test_generate_calls_text_to_image_when_no_reference_images() -> None:
    client = _FakeClient()
    provider = GPTImageProvider(enabled=True, client=client)
    result = provider.generate("a prompt", size="1024x1280", quality="high")

    assert result == b"PNGDATA"
    assert client.images.generate_calls[0]["model"] == "gpt-image-2"
    assert client.images.generate_calls[0]["size"] == "1024x1536"
    assert client.images.generate_calls[0]["quality"] == "high"
    assert client.images.edit_calls == []


def test_generate_calls_edit_when_reference_images_given() -> None:
    client = _FakeClient()
    provider = GPTImageProvider(enabled=True, client=client)
    result = provider.generate("a prompt", size="1024x1024", quality="medium", reference_images=[b"ref-bytes"])

    assert result == b"PNGDATA"
    assert client.images.generate_calls == []
    assert client.images.edit_calls[0]["model"] == "gpt-image-2"


def test_generate_raises_when_response_has_no_image_data() -> None:
    client = _FakeClient(b64_json="")
    provider = GPTImageProvider(enabled=True, client=client)
    with pytest.raises(RuntimeError, match="no b64_json"):
        provider.generate("a prompt", size="1024x1024", quality="medium")


def test_gpt_image_provider_from_env_enabled_only_with_real_key() -> None:
    assert gpt_image_provider_from_env({}).enabled is False
    assert gpt_image_provider_from_env({"OPENAI_API_KEY": "YOUR_OPENAI_API_KEY"}).enabled is False
    assert gpt_image_provider_from_env({"OPENAI_API_KEY": "sk-real-key"}).enabled is True


def test_generate_image_run_forwards_reference_images_to_provider(tmp_path: Path) -> None:
    client = _FakeClient()
    provider = GPTImageProvider(enabled=True, client=client)
    prompt_contract = {
        "creative_brief_id": "brief-1",
        "scenario_key": "venho_rooftop_sunrise",
        "base_prompt": "A warm rooftop breakfast scene.",
        "size": "1024x1280",
        "quality": "high",
    }

    generate_image_run(
        prompt_contract,
        content_package_id="pkg-1",
        provider=provider,
        data_root=tmp_path,
        reference_images=[b"ref-bytes"],
    )

    assert client.images.edit_calls
    assert client.images.generate_calls == []
