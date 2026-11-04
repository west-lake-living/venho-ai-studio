from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from growth_engine.domain.delivery.canonical_payload import build_publish_payload
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.kernel.hashing import canonical_json_bytes


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPOSITORY_ROOT / "contracts/growth_engine/fixtures/publish_payload.v2/valid"
SCHEMA_PATH = REPOSITORY_ROOT / "contracts/growth_engine/publish_payload.v2.schema.json"


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("filename", "golden_hash"),
    [
        ("vietnamese_nfd.json", "9c700f1040998142f7bece9ec428ff29455863ddef3c77b047bd71b4c216a238"),
        ("emoji.json", "fa1cee1d22d9b910327948e1f091277d540a9bcc9ef738836d6ca63db5c90478"),
        ("crlf.json", "5d4355da87cbe0e6b5048bfe3fa2186c220be125ee779f087903c4de1753619a"),
    ],
)
def test_golden_payloads_are_normalized_and_hash_stable(
    filename: str, golden_hash: str
) -> None:
    fixture = _fixture(filename)
    payload = fixture["payload"]
    assert isinstance(payload, dict)
    revision = DeliveryRevision.create(
        {**payload, "caption": fixture["input_caption"]}
    )
    assert revision.payload == payload
    assert revision.payload_hash == golden_hash
    assert revision.canonical_bytes == canonical_json_bytes(payload)


def test_canonical_payload_validates_against_contract_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for path in sorted(FIXTURE_ROOT.glob("*.json")):
        payload = _fixture(path.name)["payload"]
        validator.validate(payload)


def test_canonical_json_rejects_all_floats_and_nan() -> None:
    with pytest.raises(ValueError, match="floating point"):
        canonical_json_bytes({"width": 1536.0})
    with pytest.raises(ValueError, match="floating point"):
        canonical_json_bytes({"score": float("nan")})


def test_payload_builder_rejects_float_dimensions() -> None:
    payload = _fixture("emoji.json")["payload"]
    assert isinstance(payload, dict)
    media = [dict(payload["media"][0])]
    media[0]["width"] = 1536.5
    with pytest.raises(ValueError, match="width must be an integer"):
        build_publish_payload(**{**payload, "media": media})


def test_key_order_does_not_change_canonical_bytes_or_hash() -> None:
    payload = _fixture("emoji.json")["payload"]
    assert isinstance(payload, dict)
    first_media = payload["media"][0]
    reversed_media = dict(reversed(list(first_media.items())))
    first = build_publish_payload(**payload)
    second = build_publish_payload(**{**dict(reversed(list(payload.items()))), "media": [reversed_media]})
    assert first[1:] == second[1:]


def test_one_caption_character_changes_the_hash() -> None:
    payload = _fixture("emoji.json")["payload"]
    assert isinstance(payload, dict)
    changed = dict(payload)
    changed["caption"] = f"{changed['caption']}!"
    assert build_publish_payload(**payload)[2] != build_publish_payload(**changed)[2]


def test_revision_creation_normalizes_nfc_and_line_endings_once() -> None:
    fixture = _fixture("vietnamese_nfd.json")
    payload = fixture["payload"]
    input_caption = fixture["input_caption"]
    assert isinstance(payload, dict)
    assert isinstance(input_caption, str)
    assert unicodedata.is_normalized("NFD", input_caption)
    assert "\r" not in payload["caption"]
    revision = DeliveryRevision.create({**payload, "caption": input_caption})
    assert revision.payload["caption"] == payload["caption"]
