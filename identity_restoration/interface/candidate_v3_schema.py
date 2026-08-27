from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema


class CandidateV3ContractError(ValueError):
    """Raised when a Candidate v3 payload cannot cross the JSON boundary."""


_CONTRACT_DIR = Path(__file__).resolve().parents[2] / "contracts" / "identity_restoration"
_SCHEMA_FILES = {
    "request": "candidate_v3_request_v1.schema.json",
    "result": "candidate_v3_result_v1.schema.json",
}
_FORMAT_CHECKER = jsonschema.FormatChecker()


@lru_cache(maxsize=None)
def _validator(kind: str) -> jsonschema.Draft202012Validator:
    try:
        filename = _SCHEMA_FILES[kind]
    except KeyError as exc:
        raise CandidateV3ContractError(f"unsupported Candidate v3 schema kind: {kind}") from exc

    schema_path = _CONTRACT_DIR / filename
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
    except (OSError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        raise CandidateV3ContractError(
            f"candidate-v3 {kind} schema unavailable or invalid: {schema_path}"
        ) from exc
    return jsonschema.Draft202012Validator(schema, format_checker=_FORMAT_CHECKER)


def _path(error: jsonschema.ValidationError) -> str:
    parts = list(error.absolute_path)
    if not parts:
        return "$"
    rendered = "$"
    for part in parts:
        rendered += f"[{part}]" if isinstance(part, int) else f".{part}"
    return rendered


def _validate(payload: Any, kind: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise CandidateV3ContractError(
            f"candidate-v3 {kind} invalid at $: expected a JSON object"
        )

    errors = sorted(
        _validator(kind).iter_errors(payload),
        key=lambda error: (tuple(str(part) for part in error.absolute_path), error.validator),
    )
    if errors:
        error = errors[0]
        raise CandidateV3ContractError(
            f"candidate-v3 {kind} invalid at {_path(error)}: {error.message}"
        )
    return payload


def validate_candidate_v3_request_payload(payload: Any) -> dict[str, Any]:
    return _validate(payload, "request")


def validate_candidate_v3_result_payload(payload: Any) -> dict[str, Any]:
    return _validate(payload, "result")
