from __future__ import annotations

from pathlib import Path

from validator_studio.schemas.face_validation import FaceValidationObservation
from shared.vision.providers.gemini_vision import (
    GeminiVisionProvider,
    ProviderCircuitBreaker,
    _gemini_response_schema,
    classify_gemini_failure,
)


def test_production_face_request_schema_is_accepted_and_serializable_offline() -> None:
    """Build the same DTO/config used by Face Validator without HTTP or API key."""
    from google.genai import types

    schema = _gemini_response_schema(FaceValidationObservation.model_json_schema())
    config = types.GenerateContentConfig(
        system_instruction="production Face Validator prompt",
        temperature=0.0,
        max_output_tokens=8192,
        response_mime_type="application/json",
        response_schema=schema,
    )
    serialized = config.model_dump(exclude_none=True)
    assert serialized["response_mime_type"] == "application/json"
    assert serialized["max_output_tokens"] == 8192
    assert "additionalProperties" not in str(serialized)


def test_schema_adapter_removes_only_sdk_unsupported_keyword() -> None:
    schema = {"type": "object", "additionalProperties": False, "properties": {"x": {"type": "string"}}}
    assert _gemini_response_schema(schema) == {"type": "object", "properties": {"x": {"type": "string"}}}


def test_provider_failure_classes_are_distinct() -> None:
    assert classify_gemini_failure(RuntimeError("503 UNAVAILABLE")) == "PROVIDER_503"
    assert classify_gemini_failure(RuntimeError("429 RESOURCE_EXHAUSTED")) == "PROVIDER_429"
    assert classify_gemini_failure(RuntimeError("FinishReason.MAX_TOKENS")) == "PROVIDER_TRUNCATED_RESPONSE"
    assert classify_gemini_failure(RuntimeError("Truncated JSON response")) == "PROVIDER_TRUNCATED_RESPONSE"
    assert classify_gemini_failure(ValueError("additionalProperties is not supported in the Gemini API")) == "LOCAL_SCHEMA_BUILD_FAIL"


def test_generate_config_is_bounded_and_structured_without_constructing_client() -> None:
    provider = object.__new__(GeminiVisionProvider)
    provider.temperature = 0.0
    config = provider._generate_config("prompt", FaceValidationObservation.model_json_schema())
    assert config["response_mime_type"] == "application/json"
    assert config["max_output_tokens"] == 8192
    assert config["thinking_config"] == {"thinking_budget": 0, "include_thoughts": False}
    assert "additionalProperties" not in str(config["response_schema"])


def test_503_and_429_open_the_batch_circuit_without_retry_policy() -> None:
    breaker = ProviderCircuitBreaker()
    assert breaker.record(RuntimeError("503 UNAVAILABLE")) == "PROVIDER_503"
    assert breaker.opened is True
    assert breaker.provider_availability == "DEGRADED"
    assert breaker.record(RuntimeError("429 RESOURCE_EXHAUSTED")) == "PROVIDER_429"


def test_c1_runner_has_no_separate_live_readiness_probe() -> None:
    source = (Path(__file__).parents[1] / "scripts/run_gw_p4_t2_c1_face_qc_gate.py").read_text()
    assert "models.get" not in source
    assert "samples=1" in source
    assert "sampleIndex" in source
