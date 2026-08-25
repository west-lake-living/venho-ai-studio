from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any, Sequence

from shared.logging import log
from shared.vision.image_loader import image_to_base64
from shared.vision.structured import extract_json
from shared.vision.paid_call_guard import PaidCallGuard


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
        self.last_raw_response: str | None = None
        self.raw_response_sink = None
        self._last_guard: PaidCallGuard | None = None
        self._last_intent: dict[str, Any] | None = None
        self._last_response: Any = None

    def _generate(self, contents: list[Any], system_prompt: str, *, response_schema: dict[str, Any] | None = None, sample_index: int = 1) -> str:
        config = {
            "system_instruction": system_prompt,
            "temperature": self.temperature,
            # The schema is compact, but Gemini's unchanged thinking behavior
            # consumes output budget before the JSON body.  8192 is a ceiling,
            # not a request for prose; the response schema still fail-closes
            # any non-DTO output.
            "max_output_tokens": 8192,
            "response_mime_type": "application/json",
        }
        if response_schema is not None:
            config["response_schema"] = response_schema
        guard = PaidCallGuard()
        intent = guard.before_call(model=self.model, sample_index=sample_index, config=config)
        self._last_guard = guard
        self._last_intent = intent
        try:
            response = self.client.models.generate_content(model=self.model, contents=contents, config=config)
        except Exception as exc:
            guard.after_call(intent, error=exc)
            raise
        text = (response.text or "").strip()
        self.last_raw_response = text
        self._last_response = response
        if self.raw_response_sink is not None:
            self.raw_response_sink(text)
        if not text:
            error = RuntimeError("Gemini returned an empty response")
            guard.after_call(intent, response=response, error=error)
            raise error
        guard.after_call(intent, response=response)
        return text

    def analyze(self, image_path: Path, system_prompt: str, *, response_schema: dict[str, Any] | None = None, sample_index: int = 1) -> dict[str, Any]:
        return self.analyze_many([image_path], system_prompt, "Analyze this image and return JSON only.", response_schema=response_schema, sample_index=sample_index)

    def analyze_many(
        self,
        image_paths: Sequence[Path],
        system_prompt: str,
        text_prompt: str = "Analyze these images and return JSON only.",
        *,
        response_schema: dict[str, Any] | None = None,
        sample_index: int = 1,
    ) -> dict[str, Any]:
        from google.genai import types

        contents: list[Any] = []
        for image_path in image_paths:
            data, media_type = image_to_base64(image_path)
            contents.append(types.Part.from_bytes(data=base64.b64decode(data), mime_type=media_type))
        contents.append(text_prompt)
        raw = self._generate(contents, system_prompt, response_schema=response_schema, sample_index=sample_index)
        try:
            result = extract_json(raw)
        except Exception as exc:
            if self._last_guard is not None and self._last_intent is not None:
                self._last_guard.after_call(self._last_intent, response=self._last_response, error=exc)
            raise
        log(f"  Gemini vision: {len(image_paths)} image(s)")
        return result

    def synthesize(self, system_prompt: str, user_content: str) -> dict[str, Any]:
        raw = self._generate([user_content], system_prompt)
        result = extract_json(raw)
        log("  Gemini synthesis complete")
        return result
