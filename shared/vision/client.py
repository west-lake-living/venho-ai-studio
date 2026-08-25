from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Sequence

from shared.vision.providers.openai_vision import OpenAIVisionProvider
from shared.vision.providers.claude_vision import ClaudeProvider
from shared.vision.providers.gemini_vision import GeminiVisionProvider


class VisionClient:
    """Unified access point for vision (image analysis) and text synthesis providers."""

    def __init__(
        self,
        image_provider: str = "openai",
        synthesis_provider: str = "claude",
        image_model: str = "gpt-4o",
        synthesis_model: str = "claude-sonnet-4-6",
        gemini_model: str = "gemini-3.5-flash",
        temperature: float = 0.0,
        raw_response_sink: Callable[[str], None] | None = None,
    ) -> None:
        self.image_provider_name = image_provider
        self.synthesis_provider_name = synthesis_provider
        self.image_model = image_model
        self.synthesis_model = synthesis_model
        self.last_raw_response: str | None = None
        self.raw_response_sink = raw_response_sink

        if image_provider == "openai":
            self._image_provider = OpenAIVisionProvider(model=image_model, temperature=temperature)
        elif image_provider == "gemini":
            self._image_provider = GeminiVisionProvider(model=gemini_model, temperature=temperature)
        else:
            raise ValueError(f"Unsupported image provider: {image_provider}")
        if synthesis_provider == "claude":
            self._synthesis_provider = ClaudeProvider(model=synthesis_model)
        elif synthesis_provider == "gemini":
            self._synthesis_provider = GeminiVisionProvider(model=gemini_model, temperature=temperature)
        else:
            raise ValueError(f"Unsupported synthesis provider: {synthesis_provider}")

    def analyze_image(self, image_path: Path, system_prompt: str, *, response_schema: dict[str, Any] | None = None, sample_index: int = 1) -> dict[str, Any]:
        try:
            setattr(self._image_provider, "raw_response_sink", self.raw_response_sink)
            result = self._image_provider.analyze(image_path, system_prompt, response_schema=response_schema, sample_index=sample_index)
        finally:
            self.last_raw_response = getattr(self._image_provider, "last_raw_response", None)
        return result

    def analyze_images(
        self,
        image_paths: Sequence[Path],
        system_prompt: str,
        text_prompt: str = "Analyze these images and return JSON only.",
        *,
        response_schema: dict[str, Any] | None = None,
        sample_index: int = 1,
    ) -> dict[str, Any]:
        """Analyze multiple images (e.g. a candidate plus approved reference photos) in one call."""
        try:
            setattr(self._image_provider, "raw_response_sink", self.raw_response_sink)
            result = self._image_provider.analyze_many(image_paths, system_prompt, text_prompt, response_schema=response_schema, sample_index=sample_index)
        finally:
            self.last_raw_response = getattr(self._image_provider, "last_raw_response", None)
        return result

    def synthesize(self, system_prompt: str, user_content: str) -> dict[str, Any]:
        return self._synthesis_provider.synthesize(system_prompt, user_content)


class MockVisionClient(VisionClient):
    """VisionClient backed by mock providers — no API calls, no network."""

    def __init__(self) -> None:
        from shared.vision.providers.mock_vision import MockVisionProvider
        self.image_provider_name = "mock"
        self.synthesis_provider_name = "mock"
        self.image_model = "mock"
        self.synthesis_model = "mock"
        self.last_raw_response = None
        self.raw_response_sink = None
        self._mock = MockVisionProvider()
        self._image_provider = self._mock
        self._synthesis_provider = self._mock
