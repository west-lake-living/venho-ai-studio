from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from validator_studio.observe_adapter import (
    ObservationSchemaError,
    parse_image_observation_response,
)
from validator_studio.schemas.image_validation import ImageObservation


def _variant_observation() -> dict[str, object]:
    # Provider-shaped variation seen in structured vision responses: enum case
    # differs, optional arrays are omitted, and scalar values arrive as strings.
    return {
        "dna_matches": [
            {
                "key": "window_frame",
                "match_state": "MATCH",
                "confidence": "0.92",
            }
        ],
        "forbidden": [
            {"rule": "no visible logo", "violated": "false", "severity": "HIGH"}
        ],
    }


def test_parse_clean_json_and_numeric_string_fields() -> None:
    result = parse_image_observation_response(json.dumps(_variant_observation()))
    assert result.dna_matches[0].match_state.value == "match"
    assert result.dna_matches[0].confidence == pytest.approx(0.92)
    assert result.forbidden[0].violated is False
    assert result.allowed_imperfections == []
    assert result.notes == []


def test_normalizes_enum_case_that_legacy_direct_model_mapping_rejected() -> None:
    payload = _variant_observation()
    with pytest.raises(ValidationError):
        ImageObservation.model_validate(payload)

    parsed = parse_image_observation_response(payload)
    assert parsed.dna_matches[0].match_state.value == "match"
    assert parsed.forbidden[0].severity.value == "high"


@pytest.mark.parametrize(
    "response",
    [
        "```json\n" + json.dumps(_variant_observation()) + "\n```",
        "Vision result follows:\n" + json.dumps(_variant_observation()) + "\nEnd of result.",
    ],
)
def test_parse_fenced_and_wrapper_text_json(response: str) -> None:
    result = parse_image_observation_response(response)
    assert result.dna_matches[0].key == "window_frame"


def test_missing_required_field_fails_with_field_name() -> None:
    with pytest.raises(ObservationSchemaError, match=r"field \$\.dna_matches\[0\]\.key: required field is missing"):
        parse_image_observation_response({"dna_matches": [{"match_state": "match"}]})


def test_invalid_confidence_fails_with_field_and_reason_without_guessing() -> None:
    payload = {"dna_matches": [{"key": "window_frame", "match_state": "match", "confidence": "high"}]}
    with pytest.raises(ObservationSchemaError, match=r"field \$\.dna_matches\[0\]\.confidence: expected a number"):
        parse_image_observation_response(payload)
