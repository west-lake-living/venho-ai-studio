from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from shared.vision.providers.openai_vision import OpenAIVisionProvider
from shared.vision.providers.claude_vision import ClaudeProvider


class VisionClient:
    """Unified access point for vision (image analysis) and text synthesis providers."""

    def __init__(
        self,
        image_provider: str = "openai",
        synthesis_provider: str = "claude",
        image_model: str = "gpt-4o",
        synthesis_model: str = "claude-sonnet-4-6",
        temperature: float = 0.0,
    ) -> None:
        self.image_provider_name = image_provider
        self.synthesis_provider_name = synthesis_provider
        self.image_model = image_model
        self.synthesis_model = synthesis_model

        self._image_provider = OpenAIVisionProvider(
            model=image_model, temperature=temperature
        )
        self._synthesis_provider = ClaudeProvider(model=synthesis_model)

    def analyze_image(self, image_path: Path, system_prompt: str) -> dict[str, Any]:
        return self._image_provider.analyze(image_path, system_prompt)

    def analyze_images(
        self,
        image_paths: Sequence[Path],
        system_prompt: str,
        text_prompt: str = "Analyze these images and return JSON only.",
    ) -> dict[str, Any]:
        """Analyze multiple images (e.g. a candidate plus approved reference photos) in one call."""
        return self._image_provider.analyze_many(image_paths, system_prompt, text_prompt)

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
        self._mock = MockVisionProvider()
        self._image_provider = self._mock
        self._synthesis_provider = self._mock
