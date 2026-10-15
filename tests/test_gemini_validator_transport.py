from __future__ import annotations

from pathlib import Path

import pytest
from google import genai

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


def test_face_validation_fixture_parses_against_the_pinned_response_contract_offline() -> None:
    fixture = {
        "gates": [
            {"gate": "single_subject", "passed": True, "reason": "one face", "evidence": ""},
            {"gate": "reference_consistency", "passed": True, "reason": "match", "evidence": ""},
        ],
        "weighted_scores": {
            "facial_shape": 92.0,
            "eyes_and_brows": 93.0,
            "nose": 91.0,
            "mouth_and_chin": 92.0,
            "technical_quality": 94.0,
        },
        "notes": ["Offline contract fixture; no provider request."],
    }

    observation = FaceValidationObservation.model_validate(fixture)

    assert len(observation.gates) == 2
    assert all(gate.passed for gate in observation.gates)
    assert observation.weighted_scores.facial_shape == 92.0


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
    provider.model = "gemini-3.8-flash"
    config = provider._generate_config("prompt", FaceValidationObservation.model_json_schema())
    assert config["response_mime_type"] == "application/json"
    assert config["max_output_tokens"] == 8192
    assert config["thinking_config"] == {"thinking_level": "low", "include_thoughts": False}
    assert "additionalProperties" not in str(config["response_schema"])


def test_client_pins_gemini_api_version_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_client(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setenv("GEMINI_API_KEY", "offline-test-key")
    monkeypatch.setattr(genai, "Client", fake_client)
    provider = GeminiVisionProvider(model="gemini-3.8-flash", api_version="v1beta")
    assert provider.api_version == "v1beta"
    assert captured["api_key"] == "offline-test-key"
    assert captured["http_options"].api_version == "v1beta"


def test_client_rejects_unpinned_gemini_api_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "offline-test-key")
    with pytest.raises(ValueError, match="GEMINI_API_VERSION"):
        GeminiVisionProvider(api_version="v2")


def test_gemini_25_keeps_the_existing_zero_thinking_budget() -> None:
    provider = object.__new__(GeminiVisionProvider)
    provider.temperature = 0.0
    provider.model = "gemini-2.5-flash"
    config = provider._generate_config("prompt", {"type": "object"})
    assert config["thinking_config"] == {"thinking_budget": 0, "include_thoughts": False}


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
