from __future__ import annotations

import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"


def schema_names() -> list[str]:
    return sorted(path.name.removesuffix(".schema.json") for path in CONTRACTS.glob("*.schema.json"))


def test_every_phase1_schema_has_valid_and_invalid_fixtures() -> None:
    names = schema_names()
    # Master plan v3.1 §5.10 header says "16" but its own enumerated list has 17
    # entries (it counts weather_signal + publishing_slot as additions to the
    # original 15 without updating the header) -- 17 is the real total.
    assert len(names) == 17
    for name in names:
        valid = CONTRACTS / "fixtures" / name / "valid"
        invalid = CONTRACTS / "fixtures" / name / "invalid"
        assert list(valid.glob("*.json")), f"missing valid fixture for {name}"
        assert list(invalid.glob("*.json")), f"missing invalid fixture for {name}"


def test_contract_fixtures_validate_as_declared() -> None:
    for name in schema_names():
        schema = json.loads((CONTRACTS / f"{name}.schema.json").read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        for fixture in (CONTRACTS / "fixtures" / name / "valid").glob("*.json"):
            payload = json.loads(fixture.read_text(encoding="utf-8"))
            errors = sorted(validator.iter_errors(payload), key=lambda error: error.path)
            assert not errors, f"{fixture} should be valid: {[error.message for error in errors]}"
        for fixture in (CONTRACTS / "fixtures" / name / "invalid").glob("*.json"):
            payload = json.loads(fixture.read_text(encoding="utf-8"))
            assert list(validator.iter_errors(payload)), f"{fixture} should be invalid"


def test_contracts_cover_master_plan_required_set() -> None:
    required = {
        "creative_brief",
        "knowledge_fact",
        "research_note",
        "trend_candidate",
        "copy_candidate",
        "content_package",
        "image_prompt_contract",
        "image_manifest",
        "validation_report",
        "approval_snapshot",
        "publication_command",
        "publication_callback",
        "metric_observation",
        "conversion_event",
        "strategy_memory",
        "weather_signal",
        "publishing_slot",
    }
    assert set(schema_names()) == required
