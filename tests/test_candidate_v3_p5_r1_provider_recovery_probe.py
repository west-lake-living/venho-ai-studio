from __future__ import annotations

from pathlib import Path

from shared.vision.providers.gemini_vision import configured_transport_attempts


SCRIPT = Path(__file__).parents[1] / "scripts/run_candidate_v3_r1_p5_r1_provider_recovery_probe.py"


def test_probe_is_locked_to_one_fixture_and_one_transport_attempt() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"FACE_LOCAL", "B01", 1' in source
    assert '"VALIDATOR_MAX_NEW_CALLS"] = "1"' in source
    assert '"GEMINI_MAX_TRANSPORT_ATTEMPTS"] = "1"' in source
    assert "runner.run()" not in source
    assert "providerCalls" in source


def test_transport_attempt_cap_can_be_lowered_without_changing_default(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_MAX_TRANSPORT_ATTEMPTS", raising=False)
    assert configured_transport_attempts() == 2
    monkeypatch.setenv("GEMINI_MAX_TRANSPORT_ATTEMPTS", "1")
    assert configured_transport_attempts() == 1
