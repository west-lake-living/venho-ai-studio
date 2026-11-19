from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from validator_studio.observe_adapter import (
    ObservationNonFiniteNumberError,
    ObservationSchemaError,
    _normalize_provider_numbers,
    parse_image_observation_response,
)
from validator_studio.schemas.image_validation import ImageObservation
from growth_engine.domain.kernel.hashing import canonical_json_bytes


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
    assert result.dna_matches[0].confidence_bp == 9_200
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


def test_nested_provider_floats_use_decimal_half_even_basis_points() -> None:
    nested = _normalize_provider_numbers({"items": [0.00005, {"score": 0.00015}]})
    assert nested == {"items": [0, {"score": 2}]}

    parsed = parse_image_observation_response({
        "dna_matches": [
            {"key": "a", "match_state": "match", "confidence": 0.92},
            {"key": "b", "match_state": "partial", "confidence": 0.00005},
        ],
        "forbidden": [{"rule": "c", "confidence": 0.00015}],
    })
    assert [item.confidence_bp for item in parsed.dna_matches] == [9_200, 0]
    assert parsed.forbidden[0].confidence_bp == 2


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_provider_float_has_distinct_code_and_field_path(value: float) -> None:
    with pytest.raises(ObservationNonFiniteNumberError, match=r"field \$\.items\[1\]\.score") as error:
        _normalize_provider_numbers({"items": [0, {"score": value}]})
    assert error.value.code == "ERR_GC2_QC_NONFINITE_NUMBER"


def test_canonical_json_still_rejects_any_unconverted_float() -> None:
    with pytest.raises(ValueError, match=r"field \$\.nested\[0\]\.score: floating point values are not allowed"):
        canonical_json_bytes({"nested": [{"score": 0.92}]})


@pytest.mark.parametrize(("score", "verdict", "status"), [
    (59.99, "reject", "FAIL"), (60, "regenerate", "WARNING"),
    (69.99, "regenerate", "WARNING"), (70, "revise", "WARNING"),
    (79.99, "revise", "WARNING"), (80, "revise", "WARNING"),
    (89.99, "revise", "WARNING"), (90, "approve", "OK"),
])
def test_image_score_cutoffs_use_points(score: float, verdict: str, status: str) -> None:
    from validator_studio.scoring import status_for_score, verdict_for_score

    assert verdict_for_score(score).value == verdict
    assert status_for_score(score).name == status


def test_image_scoring_uses_confidence_bp_as_weight_and_not_as_policy_cutoff() -> None:
    from validator_studio.scoring import IMAGE_CATEGORIES, score_image_observation

    config = {
        "image_validation_weights": {key: int(key == "dna_match") for key in IMAGE_CATEGORIES},
        "rubric": {"match": 100, "partial": 60, "mismatch": 0},
        "kill_switch": {"forbidden_high_cap": 40},
    }
    observation = parse_image_observation_response(json.dumps({
        "dna_matches": [
            {"key": "window", "match_state": "match", "confidence": 0.6999},
            {"key": "wall", "match_state": "partial", "confidence": 1},
        ],
        "forbidden": [{"rule": "logo", "violated": False, "confidence": 0.6999}],
    }))
    assert observation.dna_matches[0].confidence_bp == 6999
    score = score_image_observation(observation, config)
    assert score.overall_score == 76.47
    assert score.verdict.value == "revise"
    assert not score.kill_switch.triggered
    observation.forbidden[0].violated = True
    blocked = score_image_observation(observation, config)
    assert blocked.overall_score == 40
    assert blocked.kill_switch.triggered
    assert blocked.verdict.value == "reject"
