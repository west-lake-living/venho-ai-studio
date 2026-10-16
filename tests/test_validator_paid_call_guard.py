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


def test_paid_call_guard_scopes_budget_to_run_id(tmp_path, monkeypatch):
    # Regression 2026-10-15: one historical intent in a shared ledger blocked every later
    # faceless-video validation forever because the budget counted the whole ledger.
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("VALIDATOR_LIVE_ENABLED", "true")
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setenv("VALIDATOR_RUN_ID", "job-a:1")
    PaidCallGuard(ledger_path=ledger, max_calls=1).before_call(model="gemini-3.8-flash", sample_index=1, config={})
    with pytest.raises(PaidCallBlocked, match="for run job-a:1"):
        PaidCallGuard(ledger_path=ledger, max_calls=1).before_call(model="gemini-3.8-flash", sample_index=1, config={})

    monkeypatch.setenv("VALIDATOR_RUN_ID", "job-b:1")
    intent = PaidCallGuard(ledger_path=ledger, max_calls=1).before_call(model="gemini-3.8-flash", sample_index=1, config={})
    assert intent["runId"] == "job-b:1"
    assert intent["callNumber"] == 1


def test_paid_call_guard_without_run_id_keeps_cumulative_budget(tmp_path, monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("VALIDATOR_LIVE_ENABLED", "true")
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setenv("VALIDATOR_RUN_ID", "job-a:1")
    PaidCallGuard(ledger_path=ledger, max_calls=1).before_call(model="gemini-3.8-flash", sample_index=1, config={})
    monkeypatch.delenv("VALIDATOR_RUN_ID")
    with pytest.raises(PaidCallBlocked, match="exhausted: 1/1"):
        PaidCallGuard(ledger_path=ledger, max_calls=1).before_call(model="gemini-3.8-flash", sample_index=1, config={})


def test_face_cli_reports_blocked_paid_call_with_distinct_exit_code(monkeypatch, tmp_path):
    from typer.testing import CliRunner

    import validator_studio.cli as cli

    def blocked(*_args, **_kwargs):
        raise PaidCallBlocked("Validator paid-call budget exhausted: 1/1")

    monkeypatch.setattr(cli, "run_face_validation", blocked)
    image = tmp_path / "x.png"
    image.write_bytes(b"x")
    result = CliRunner().invoke(cli.app, ["face", "--subject", "linh_an", "--image", str(image)])
    assert result.exit_code == cli.PAID_CALL_BLOCKED_EXIT_CODE
    assert cli.PAID_CALL_BLOCKED_MARKER in result.output


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


def _response(prompt, candidates, thoughts):
    class Usage:
        prompt_token_count = prompt
        candidates_token_count = candidates
        thoughts_token_count = thoughts

    class Response:
        usage_metadata = Usage()
        candidates = []

    return Response()


@pytest.fixture
def fresh_usage(monkeypatch):
    import shared.vision.paid_call_guard as guard

    monkeypatch.setattr(guard, "_usage", {"calls": 0, "input_tokens": 0, "output_tokens": 0, "thought_tokens": 0, "complete": True})
    monkeypatch.setattr(guard, "_counted_responses", [])
    return guard


def test_usage_summary_sums_billable_tokens_once_per_response(tmp_path, fresh_usage):
    guard = PaidCallGuard(ledger_path=tmp_path / "ledger.jsonl", max_calls=12)
    first, second = _response(8804, 281, 512), _response(8804, 269, None)
    guard.after_call({}, response=first)
    guard.after_call({}, response=first, error=ValueError("json"))  # parse failure of the same call
    guard.after_call({}, response=second)
    assert fresh_usage.usage_summary() == {
        "calls": 2, "input_tokens": 17608, "output_tokens": 550, "thought_tokens": 512, "complete": True,
    }
    records = [json.loads(line) for line in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert records[0]["thoughtsTokens"] == 512


def test_usage_summary_is_incomplete_when_a_call_has_no_usage(tmp_path, fresh_usage):
    guard = PaidCallGuard(ledger_path=tmp_path / "ledger.jsonl", max_calls=12)
    guard.after_call({}, response=_response(10, 2, 0))
    guard.after_call({}, error=TimeoutError("no response"))
    summary = fresh_usage.usage_summary()
    assert summary["calls"] == 2 and summary["complete"] is False


def test_face_cli_prints_usage_after_report_paths(monkeypatch, tmp_path, fresh_usage):
    from typer.testing import CliRunner

    import validator_studio.cli as cli

    def validated(*_args, **_kwargs):
        PaidCallGuard(ledger_path=tmp_path / "ledger.jsonl", max_calls=12).after_call({}, response=_response(8804, 281, 64))
        return {"md": tmp_path / "r.md", "json": tmp_path / "r.json"}

    monkeypatch.setattr(cli, "run_face_validation", validated)
    image = tmp_path / "x.png"
    image.write_bytes(b"x")
    result = CliRunner().invoke(cli.app, ["face", "--subject", "linh_an", "--image", str(image)])
    assert result.exit_code == 0
    lines = result.output.splitlines()
    # faceless-video's parser: the first line containing "JSON" and ":" is the report path.
    first_json = next(line for line in lines if "JSON" in line and ":" in line)
    assert first_json.split(":", 1)[1].strip() == str(tmp_path / "r.json")
    usage_line = next(line for line in lines if line.startswith(cli.USAGE_MARKER + " "))
    assert lines.index(usage_line) > lines.index(first_json)
    assert json.loads(usage_line[len(cli.USAGE_MARKER) + 1 :]) == {
        "calls": 1, "complete": True, "input_tokens": 8804, "output_tokens": 281, "thought_tokens": 64,
    }


def test_image_cli_prints_usage_and_reports_blocked_calls(monkeypatch, tmp_path, fresh_usage):
    from typer.testing import CliRunner

    import validator_studio.cli as cli

    image = tmp_path / "x.png"
    image.write_bytes(b"x")

    def validated(*_args, **_kwargs):
        PaidCallGuard(ledger_path=tmp_path / "ledger.jsonl", max_calls=12).after_call({}, response=_response(1500, 300, 0))
        return {"md": tmp_path / "r.md", "json": tmp_path / "r.json"}

    monkeypatch.setattr(cli, "run_image_validation", validated)
    args = ["image", "--subject", "westlake", "--image", str(image), "--scenario-profile-id", "linh_an_lakeside_video"]
    result = CliRunner().invoke(cli.app, args)
    assert result.exit_code == 0
    assert any(line.startswith(cli.USAGE_MARKER + " ") for line in result.output.splitlines())

    def blocked(*_args, **_kwargs):
        raise PaidCallBlocked("Validator paid-call budget exhausted: 1/1")

    monkeypatch.setattr(cli, "run_image_validation", blocked)
    refused = CliRunner().invoke(cli.app, args)
    assert refused.exit_code == cli.PAID_CALL_BLOCKED_EXIT_CODE


def test_linh_an_lakeside_overlay_forbids_pagodas_and_mountains_and_keeps_base_rules():
    import yaml

    overlay = yaml.safe_load(open("config/projects/venho_hotel/subjects/westlake.linh_an_lakeside_video.overrides.yaml"))
    rules = " | ".join(overlay["forbidden"])
    assert "pagodas" in rules and "mountains" in rules
    assert "no generic Asian city lake" in rules and "jade-teal" in rules  # base curated rules redeclared


def test_lakeside_scenario_overlay_is_actually_applied_to_the_westlake_dna():
    # _apply_scenario_overlay silently falls back when the file is missing; pin the real path.
    from validator_studio.image_validator import _apply_scenario_overlay

    dna = json.load(open("data/projects/venho_hotel/knowledge/VENHO_HOTEL_WESTLAKE_DNA.json"))
    merged = _apply_scenario_overlay("venho_hotel", "westlake", "linh_an_lakeside_video", dna)
    rules = [item["rule"] for item in merged["forbidden"]]
    assert any("pagodas" in rule for rule in rules)
    assert any("mountains" in rule for rule in rules)
    assert _apply_scenario_overlay("venho_hotel", "westlake", None, dna) == dna
