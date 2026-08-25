from __future__ import annotations

import json

import pytest

from shared.vision.paid_call_guard import PaidCallBlocked, PaidCallGuard, paid_call_context


def test_paid_call_guard_blocks_test_transport_before_network(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test-paid-call")
    monkeypatch.setenv("VALIDATOR_LIVE_ENABLED", "true")
    with pytest.raises(PaidCallBlocked, match="during tests"):
        PaidCallGuard(ledger_path=ledger, max_calls=12).before_call(
            model="gemini-3.5-flash", sample_index=1, config={"response_mime_type": "application/json"}
        )
    assert not ledger.exists()


def test_paid_call_guard_enforces_explicit_gate_budget_and_ledger(tmp_path, monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("VALIDATOR_LIVE_ENABLED", "true")
    ledger = tmp_path / "ledger.jsonl"
    with paid_call_context({"benchmarkId": "B02", "branch": "nano-banana-edit", "imageSha256": "a" * 64}):
        intent = PaidCallGuard(ledger_path=ledger, max_calls=1).before_call(
            model="gemini-3.5-flash", sample_index=2, config={"response_mime_type": "application/json"}
        )
    PaidCallGuard(ledger_path=ledger, max_calls=1).after_call(intent, error=RuntimeError("truncated"))
    records = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert records[0]["event"] == "intent"
    assert records[1]["event"] == "result"
    assert records[1]["success"] is False
    with pytest.raises(PaidCallBlocked, match="exhausted"):
        PaidCallGuard(ledger_path=ledger, max_calls=1).before_call(
            model="gemini-3.5-flash", sample_index=3, config={}
        )


def test_structured_observation_maps_exactly_to_existing_image_dto(monkeypatch, tmp_path):
    import validator_studio.observe_adapter as module

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.last_raw_response = None

        def analyze_image(self, image_path, prompt, *, response_schema, sample_index):
            assert response_schema["title"] == "ImageObservation"
            payload = {"dna_matches": [], "forbidden": [], "allowed_imperfections": [], "notes": []}
            self.last_raw_response = json.dumps(payload)
            return payload

    monkeypatch.setattr(module, "VisionClient", FakeClient)
    result = module.observe_image_against_dna(tmp_path / "candidate.png", {}, provider="gemini", samples=1)
    assert result.model_dump() == {"dna_matches": [], "forbidden": [], "allowed_imperfections": [], "notes": []}
