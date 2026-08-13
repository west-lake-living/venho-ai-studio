from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any, Sequence

from shared.logging import log
from shared.vision.image_loader import image_to_base64
from shared.vision.structured import extract_json


DEFAULT_GEMINI_MODEL = "gemini-flash-latest"


class GeminiVisionProvider:
    """Gemini Flash adapter for image observation and text synthesis.

    The Google SDK is imported lazily so the offline test suite never needs an
    API key or network access. Set GEMINI_API_KEY (or GOOGLE_API_KEY) for live
    calls; GEMINI_VISION_MODEL can override the configured model.
    """

    def __init__(self, model: str = DEFAULT_GEMINI_MODEL, temperature: float = 0.0) -> None:
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("google-genai is required for Gemini; install: pip install google-genai") from exc
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) not set in environment")
        self._genai = genai
        self.client = genai.Client(api_key=api_key)
        self.model = os.environ.get("GEMINI_VISION_MODEL", model)
        self.temperature = temperature

    def _generate(self, contents: list[Any], system_prompt: str) -> str:
        config = {
            "system_instruction": system_prompt,
            "temperature": self.temperature,
            "max_output_tokens": 4096,
            "response_mime_type": "application/json",
        }
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned an empty response")
        return text

    def analyze(self, image_path: Path, system_prompt: str) -> dict[str, Any]:
        return self.analyze_many([image_path], system_prompt, "Analyze this image and return JSON only.")

    def analyze_many(
        self,
        image_paths: Sequence[Path],
        system_prompt: str,
        text_prompt: str = "Analyze these images and return JSON only.",
    ) -> dict[str, Any]:
        from google.genai import types

        contents: list[Any] = []
        for image_path in image_paths:
            data, media_type = image_to_base64(image_path)
            contents.append(types.Part.from_bytes(data=base64.b64decode(data), mime_type=media_type))
        contents.append(text_prompt)
        raw = self._generate(contents, system_prompt)
        result = extract_json(raw)
        log(f"  Gemini vision: {len(image_paths)} image(s)")
        return result

    def synthesize(self, system_prompt: str, user_content: str) -> dict[str, Any]:
        raw = self._generate([user_content], system_prompt)
        result = extract_json(raw)
        log("  Gemini synthesis complete")
        return result
