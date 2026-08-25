from __future__ import annotations

import pytest

from shared.vision.structured import StructuredResponseError, extract_json


def test_extract_json_accepts_plain_fenced_and_wrapped_json() -> None:
    payload = {"gates": [], "weighted_scores": {"eyes_and_brows": 91}}
    plain = '{"gates": [], "weighted_scores": {"eyes_and_brows": 91}}'
    assert extract_json(plain) == payload
    assert extract_json("```json\n" + plain + "\n```") == payload
    assert extract_json("Here is the result:\n" + plain) == payload


@pytest.mark.parametrize("raw", [
    "",
    "validator output without JSON",
    '{"gates": [',
    '{"gates": [], "weighted_scores": }',
])
def test_extract_json_rejects_empty_truncated_and_malformed_response(raw: str) -> None:
    with pytest.raises(StructuredResponseError) as error:
        extract_json(raw)
    assert error.value.raw == raw


def test_extract_json_does_not_count_braces_inside_strings() -> None:
    payload = '{"reason": "literal } and ] are text", "ok": true}'
    assert extract_json(payload)["ok"] is True


def test_image_validator_persists_raw_before_parse(monkeypatch, tmp_path) -> None:
    import validator_studio.observe_adapter as module

    class FakeClient:
        last_raw_response = '{"dna_matches": ['

        def __init__(self, *args, **kwargs):
            pass

        def analyze_image(self, image_path, prompt):
            raise StructuredResponseError("Truncated JSON response", raw=self.last_raw_response)

    monkeypatch.setattr(module, "VisionClient", FakeClient)
    events = []
    with pytest.raises(StructuredResponseError):
        module.observe_image_against_dna(
            tmp_path / "image.png", {}, provider="gemini", samples=1,
            raw_response_sink=events.append,
        )
    assert events[-1]["parseStatus"] == "failed"
    assert events[-1]["rawResponse"] == '{"dna_matches": ['
