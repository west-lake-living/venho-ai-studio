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


def classify_gemini_failure(error: Exception) -> str:
    """Map transport/contract failures to the frozen Validator classes."""
    text = str(error).upper()
    if "429" in text or "RESOURCE_EXHAUSTED" in text:
        return "PROVIDER_429"
    if "503" in text or "UNAVAILABLE" in text:
        return "PROVIDER_503"
    if "TIMEOUT" in text or "TIMED OUT" in text:
        return "PROVIDER_TIMEOUT"
    if "MAX_TOKENS" in text or "TRUNCATED" in text or "INCOMPLETE JSON" in text or "EMPTY RESPONSE" in text:
        return "PROVIDER_TRUNCATED_RESPONSE"
    if "ADDITIONALPROPERTIES" in text or "SCHEMA" in text and "SUPPORTED" in text:
        return "LOCAL_SCHEMA_BUILD_FAIL"
    if "JSON" in text and ("SERIAL" in text or "ENCOD" in text):
        return "LOCAL_REQUEST_SERIALIZATION_FAIL"
    return "PROVIDER_RESPONSE_SCHEMA_FAIL"


class ProviderCircuitBreaker:
    """Fail-closed batch breaker for provider availability incidents."""

    def __init__(self) -> None:
        self.opened = False
        self.provider_availability = "READY"
        self.failure_class: str | None = None

    def record(self, error: Exception) -> str:
        failure_class = classify_gemini_failure(error)
        if failure_class in {"PROVIDER_503", "PROVIDER_429"}:
            self.opened = True
            self.provider_availability = "DEGRADED"
            self.failure_class = failure_class
        return failure_class


def _gemini_response_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove JSON-Schema keywords rejected by Gemini structured output."""
    if isinstance(schema, dict):
        return {
            key: _gemini_response_schema(value)
            for key, value in schema.items()
            if key != "additionalProperties"
        }
    if isinstance(schema, list):
        return [_gemini_response_schema(value) for value in schema]
    return schema


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
        self.last_failure_class: str | None = None
        self.provider_availability = "UNKNOWN"

    def _generate_config(self, system_prompt: str, response_schema: dict[str, Any] | None) -> dict[str, Any]:
        config = {
            "system_instruction": system_prompt,
            "temperature": self.temperature,
            "max_output_tokens": 8192,
            # Face-QC is a small, schema-constrained observation.  Leaving
            # Gemini thinking on can consume the complete response budget
            # before it emits the DTO (observed as MAX_TOKENS plus a padded,
            # partial JSON body).  The observation rubric, prompt, schema,
            # thresholds, and output ceiling remain unchanged.
            "thinking_config": {"thinking_budget": 0, "include_thoughts": False},
            "response_mime_type": "application/json",
        }
        if response_schema is not None:
            config["response_schema"] = _gemini_response_schema(response_schema)
        return config

    def _generate(self, contents: list[Any], system_prompt: str, *, response_schema: dict[str, Any] | None = None, sample_index: int = 1) -> str:
        config = self._generate_config(system_prompt, response_schema)
        guard = PaidCallGuard()
        intent = guard.before_call(model=self.model, sample_index=sample_index, config=config)
        self._last_guard = guard
        self._last_intent = intent
        try:
            response = self.client.models.generate_content(model=self.model, contents=contents, config=config)
        except Exception as exc:
            self.last_failure_class = classify_gemini_failure(exc)
            if self.last_failure_class in {"PROVIDER_503", "PROVIDER_429"}:
                self.provider_availability = "DEGRADED"
            guard.after_call(intent, error=exc)
            raise
        text = (response.text or "").strip()
        self.last_raw_response = text
        self._last_response = response
        if self.raw_response_sink is not None:
            self.raw_response_sink(text)
        if not text:
            error = RuntimeError("Gemini returned an empty response")
            self.last_failure_class = "PROVIDER_TRUNCATED_RESPONSE"
            guard.after_call(intent, response=response, error=error)
            raise error
        self.provider_availability = "READY"
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
