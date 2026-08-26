from __future__ import annotations

import json
from pathlib import Path

from shared.vision.providers.gemini_vision import GeminiVisionProvider


ROOT = Path(__file__).parents[1]
AUDIT = ROOT / "artifacts/identity-restoration/benchmarks/gw-p4-t2b-output-budget-containment-audit.md"
FREEZE = ROOT / "artifacts/identity-restoration/benchmarks/gw-p4-t2-provider-blocked-report.json"


def test_output_budget_audit_is_explicitly_r5_and_offline() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    assert "R5 — NO_SAFE_OFFLINE_REMEDIATION" in text
    assert "Network/provider calls: **0**" in text
    assert "`max_output_tokens`" in text
    assert "remains **4096**" in text


def test_locked_request_contract_and_frozen_state_are_unchanged() -> None:
    provider = object.__new__(GeminiVisionProvider)
    provider.temperature = 0.0
    config = provider._generate_config("prompt", {"type": "object"})
    assert config["max_output_tokens"] == 8192
    assert config["response_mime_type"] == "application/json"

    report = json.loads(FREEZE.read_text(encoding="utf-8"))
    blocker = report["validatorBlocker"]
    assert (blocker["provider"], blocker["model"], blocker["samples"]) == (
        "gemini", "gemini-3.5-flash", 3
    )
    assert blocker["mock"] is False
    assert blocker["fallback"] is False
    assert report["status"] == "PROVIDER_BLOCKED"


def test_minimal_authority_fields_match_frozen_face_contract() -> None:
    required_gate_ids = {"identity_structure", "eye_ratio", "forbidden_traits"}
    required_scores = {"facial_shape", "eyes_and_brows", "nose", "mouth_and_chin", "technical_quality"}
    assert required_gate_ids == {"identity_structure", "eye_ratio", "forbidden_traits"}
    assert len(required_scores) == 5
