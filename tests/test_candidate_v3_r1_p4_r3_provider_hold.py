from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/run_candidate_v3_r1_p4_r1_provider_remediation.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("candidate_v3_r1_p4_runner", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_active_provider_hold_blocks_without_explicit_recovery(monkeypatch, tmp_path):
    runner = load_runner()
    gate = tmp_path / "provider-hold.json"
    gate.write_text(
        json.dumps({"provider_hold": {"active": True, "provider": "Gemini", "model": "gemini-flash-latest"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "R1_P4_R3_HOLD_GATE", gate)
    monkeypatch.delenv("R1_P4_R3_RECOVERY_RECHECK_AUTHORIZED", raising=False)

    try:
        runner.enforce_provider_hold_gate()
    except RuntimeError as exc:
        assert str(exc).startswith("PROVIDER_HOLD_ACTIVE:")
    else:
        raise AssertionError("active provider hold must block an unauthorized invocation")


def test_explicit_recovery_authorization_opens_only_the_next_gate(monkeypatch, tmp_path):
    runner = load_runner()
    gate = tmp_path / "provider-hold.json"
    gate.write_text(json.dumps({"provider_hold": {"active": True}}), encoding="utf-8")
    monkeypatch.setattr(runner, "R1_P4_R3_HOLD_GATE", gate)
    monkeypatch.setenv("R1_P4_R3_RECOVERY_RECHECK_AUTHORIZED", "1")

    runner.enforce_provider_hold_gate()
