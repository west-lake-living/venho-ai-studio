from __future__ import annotations

import copy
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from identity_restoration.application.dto.candidate_v3 import CandidateV3Request
from identity_restoration.interface.json_bridge import (
    CandidateV3ContractError,
    dump_candidate_v3_result,
    parse_candidate_v3_request,
    validate_candidate_v3_result_payload,
)
from tests.identity_restoration.contracts.test_candidate_v3_schemas import _request, _result


def test_valid_request_parses_into_immutable_typed_dto() -> None:
    request = parse_candidate_v3_request(_request())

    assert isinstance(request, CandidateV3Request)
    assert request.run_id == "run-candidate-v3-001"
    assert request.attempt_id == "attempt-001"
    assert request.candidate_profile_id == "candidate-v3-sd15-faceid-canonical-512"
    assert request.seed == 42
    assert request.canonical_image.sha256 == "a" * 64
    assert request.transform.model_size == 512
    assert len(request.selected_identity_references) == 1

    with pytest.raises(FrozenInstanceError):
        request.seed = 7  # type: ignore[misc]


def test_request_loader_accepts_json_without_reading_artifact_paths(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(_request()), encoding="utf-8")

    from identity_restoration.interface.json_bridge import load_candidate_v3_request

    request = load_candidate_v3_request(request_path)

    assert request.run_id == "run-candidate-v3-001"


@pytest.mark.parametrize("payload", [[], "payload", None])
def test_non_object_request_is_rejected(payload) -> None:
    with pytest.raises(CandidateV3ContractError, match="expected a JSON object"):
        parse_candidate_v3_request(payload)


def test_missing_required_request_field_is_rejected_before_dto_creation() -> None:
    payload = _request()
    payload.pop("effectiveConfigSha256")

    with pytest.raises(CandidateV3ContractError, match="effectiveConfigSha256"):
        parse_candidate_v3_request(payload)


def test_unknown_top_level_request_property_is_rejected() -> None:
    payload = _request()
    payload["unsafeOverride"] = True

    with pytest.raises(CandidateV3ContractError, match="unsafeOverride"):
        parse_candidate_v3_request(payload)


def test_malformed_request_sha_is_rejected() -> None:
    payload = _request()
    payload["canonicalImage"]["sha256"] = "abc123"

    with pytest.raises(CandidateV3ContractError, match="sha256"):
        parse_candidate_v3_request(payload)


def test_non_512_canonical_artifact_is_rejected() -> None:
    payload = _request()
    payload["canonicalImage"]["width"] = 768
    payload["canonicalImage"]["height"] = 512

    with pytest.raises(CandidateV3ContractError, match="512"):
        parse_candidate_v3_request(payload)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("modelSize", 256, "512"),
        ("forwardMatrix3x3", [1] * 8, "too short"),
        ("borderMode", "REPLICATE", "REFLECT_101"),
    ],
)
def test_invalid_transform_is_rejected(field: str, value, message: str) -> None:
    payload = _request()
    payload["transform"][field] = value

    with pytest.raises(CandidateV3ContractError, match=message):
        parse_candidate_v3_request(payload)


def test_no_selected_identity_reference_is_rejected() -> None:
    payload = _request()
    payload["selectedIdentityReferences"] = []

    with pytest.raises(CandidateV3ContractError, match="selectedIdentityReferences"):
        parse_candidate_v3_request(payload)


def test_valid_result_is_schema_validated() -> None:
    payload = _result()

    assert validate_candidate_v3_result_payload(payload) == payload


def test_result_missing_qc_scope_is_rejected() -> None:
    payload = _result()
    payload["quality"].pop("boundary")

    with pytest.raises(CandidateV3ContractError, match="boundary"):
        validate_candidate_v3_result_payload(payload)


def test_result_invalid_promotion_state_is_rejected() -> None:
    payload = _result()
    payload["promotionEligibility"] = "PRODUCTION_APPROVED"

    with pytest.raises(CandidateV3ContractError, match="promotionEligibility"):
        validate_candidate_v3_result_payload(payload)


def test_unknown_result_property_is_rejected() -> None:
    payload = _result()
    payload["forcePromotion"] = True

    with pytest.raises(CandidateV3ContractError, match="forcePromotion"):
        validate_candidate_v3_result_payload(payload)


def test_result_serialization_is_deterministic_and_validated() -> None:
    payload = _result()

    first = dump_candidate_v3_result(payload)
    second = dump_candidate_v3_result(copy.deepcopy(payload))

    assert first == second
    assert json.loads(first) == payload
