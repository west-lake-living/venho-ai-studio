from __future__ import annotations

import json
from pathlib import Path

import pytest

from image_studio_runtime.action_composite.regional_score_gateway import (
    RegionalScoreBlocked,
    RegionalScoreEvidence,
    RegionalScoreGateway,
)
from shared.vision.providers.gemini_vision import classify_gemini_failure
from shared.vision.structured import extract_json


ROOT = Path(__file__).parents[1]
REPORT = ROOT / "artifacts/identity-restoration/benchmarks/gw-p4-t2-provider-blocked-report.json"


def test_max_tokens_maps_to_provider_truncated_response() -> None:
    assert classify_gemini_failure(RuntimeError("FinishReason.MAX_TOKENS")) == "PROVIDER_TRUNCATED_RESPONSE"


def test_truncated_response_cannot_create_face_qc_scores() -> None:
    with pytest.raises(Exception):
        extract_json('{"gates": [], "weighted_scores": {')


def test_regional_cannot_pass_without_authoritative_face_qc_samples() -> None:
    with pytest.raises(RegionalScoreBlocked):
        RegionalScoreGateway().build(RegionalScoreEvidence())


def test_provider_blocked_is_not_pilot_fail_and_stops_continuation() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["status"] == "PROVIDER_BLOCKED"
    assert report["validatorBlocker"]["qualityConclusion"] == "UNKNOWN"
    assert report["validatorBlocker"]["providerBlockedIsNotPilotFail"] is True
    assert report["costAndContinuation"]["B04Validated"] is False
    assert report["costAndContinuation"]["C2C3Touched"] is False


def test_frozen_configuration_and_two_attempt_evidence_are_explicit() -> None:
    blocker = json.loads(REPORT.read_text(encoding="utf-8"))["validatorBlocker"]
    assert (blocker["provider"], blocker["model"], blocker["samples"]) == (
        "gemini", "gemini-3.5-flash", 3
    )
    assert blocker["mock"] is False
    assert blocker["fallback"] is False
    assert [item["maxOutputTokens"] for item in blocker["attempts"]] == [2048, 4096]
    assert all(item["validSamples"] == 0 for item in blocker["attempts"])
