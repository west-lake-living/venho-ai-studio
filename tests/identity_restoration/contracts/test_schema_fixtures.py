from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = REPO_ROOT / "contracts" / "identity_restoration"
FIXTURES = CONTRACTS / "fixtures"


def _load(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


REQUEST_SCHEMA = _load("restoration_request.schema.json")
RESULT_SCHEMA = _load("restoration_result.schema.json")


@pytest.mark.parametrize("fixture_name", ["request_valid.json"])
def test_valid_request_fixtures_pass(fixture_name: str) -> None:
    payload = json.loads((FIXTURES / fixture_name).read_text(encoding="utf-8"))
    jsonschema.validate(payload, REQUEST_SCHEMA)


@pytest.mark.parametrize("fixture_name", ["request_invalid_denoise.json"])
def test_invalid_request_fixtures_fail(fixture_name: str) -> None:
    payload = json.loads((FIXTURES / fixture_name).read_text(encoding="utf-8"))
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, REQUEST_SCHEMA)


@pytest.mark.parametrize("fixture_name", ["result_full_gate_pass.json", "result_pixel_violation.json"])
def test_result_fixtures_pass(fixture_name: str) -> None:
    payload = json.loads((FIXTURES / fixture_name).read_text(encoding="utf-8"))
    jsonschema.validate(payload, RESULT_SCHEMA)


def test_all_five_schemas_are_valid_json_schema() -> None:
    for name in [
        "restoration_request.schema.json", "restoration_result.schema.json",
        "restoration_manifest_1_3.schema.json", "worker_health.schema.json", "benchmark_row.schema.json",
    ]:
        schema = _load(name)
        jsonschema.Draft202012Validator.check_schema(schema)
