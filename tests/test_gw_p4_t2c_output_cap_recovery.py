from __future__ import annotations

import json
from pathlib import Path

from shared.vision.providers.gemini_vision import GeminiVisionProvider


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/run_gw_p4_t2c_output_cap_recovery.py"


def test_t2c_changes_only_the_output_cap_and_targets_b03_sample_one() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"after": 8192' in source
    assert 'validate_face(' in source
    assert 'find_candidate("B04")' not in source
    assert '"B04": "NOT CALLED"' in source
    assert '"C2"' in source and '"C3"' in source
    assert 'sampleIndex": 1' in source


def test_gemini_request_uses_8192_and_preserves_structured_contract() -> None:
    provider = object.__new__(GeminiVisionProvider)
    provider.temperature = 0.0
    config = provider._generate_config("prompt", {"type": "object"})
    assert config == {
        "system_instruction": "prompt",
        "temperature": 0.0,
        "max_output_tokens": 8192,
        "thinking_config": {"thinking_budget": 0, "include_thoughts": False},
        "response_mime_type": "application/json",
        "response_schema": {"type": "object"},
    }


def test_t2c_evidence_if_present_is_single_call_and_fail_closed() -> None:
    path = ROOT / "artifacts/identity-restoration/benchmarks/gw-p4-t2c-output-cap-8192-recovery.json"
    if not path.is_file():
        return
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["transport_change"] == {"before": 4096, "after": 8192}
    assert report["live_call_count"] == 1
    assert report["valid_sample_count"] in {0, 1}
    assert report["scope_guard"] == {"B04": "NOT CALLED", "C2": "UNTOUCHED", "C3": "UNTOUCHED", "gpuJobs": 0, "nanoCalls": 0}
