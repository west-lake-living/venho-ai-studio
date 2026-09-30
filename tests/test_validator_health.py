from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from validator_studio.cli import app
from validator_studio.health import validator_health

PIN = "gemini-2.5-flash"


class _NoCallClient:
    """Stands in for google.genai.Client: constructing is fine, any model call fails the test."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    @property
    def models(self) -> object:
        raise AssertionError("health must never call Gemini")


@pytest.fixture(autouse=True)
def _offline_genai(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    from google import genai

    import validator_studio.health as health

    dna = tmp_path / "VENHO_HOTEL_LINH_AN_DNA.json"
    dna.write_text(json.dumps({"dna_version": "test"}), encoding="utf-8")

    def find(project: str, subject: str):  # type: ignore[no-untyped-def]
        if subject != "linh_an":
            raise FileNotFoundError(subject)
        return dna

    monkeypatch.setattr(health, "find_dna_path", find)

    monkeypatch.setattr(genai, "Client", _NoCallClient)
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_VISION_MODEL",
                 "GEMINI_MAX_TRANSPORT_ATTEMPTS", "VALIDATOR_MAX_NEW_CALLS"):
        monkeypatch.delenv(name, raising=False)


def _ready_env(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory | None = None) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    monkeypatch.setenv("GEMINI_VISION_MODEL", PIN)
    monkeypatch.setenv("GEMINI_MAX_TRANSPORT_ATTEMPTS", "1")
    monkeypatch.setenv("VALIDATOR_MAX_NEW_CALLS", "1")


def test_ready_when_key_pin_limits_config_and_runtime_are_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    _ready_env(monkeypatch)
    result = validator_health("venho_hotel", "linh_an", PIN)
    assert result["status"] == "READY", result
    assert result["gemini_calls"] == 0
    assert "test-key-not-real" not in json.dumps(result)


@pytest.mark.parametrize(
    ("env", "failing"),
    [
        ({"GEMINI_API_KEY": None}, "credential"),
        ({"GEMINI_VISION_MODEL": "gemini-flash-latest"}, "model"),
        ({"GEMINI_VISION_MODEL": "gemini-2.0-flash"}, "model"),
        ({"GEMINI_MAX_TRANSPORT_ATTEMPTS": "5"}, "policy"),
        ({"VALIDATOR_MAX_NEW_CALLS": "0"}, "policy"),
    ],
)
def test_blocked_on_each_missing_precondition(
    monkeypatch: pytest.MonkeyPatch, env: dict[str, str | None], failing: str
) -> None:
    _ready_env(monkeypatch)
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    result = validator_health("venho_hotel", "linh_an", PIN)
    assert result["status"] == "BLOCKED"
    assert result["checks"][failing]["ok"] is False


def test_unknown_subject_config_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    _ready_env(monkeypatch)
    result = validator_health("venho_hotel", "no_such_subject", PIN)
    assert result["status"] == "BLOCKED"
    assert result["checks"]["config"]["ok"] is False


def test_cli_prints_one_json_line_and_exit_code_reflects_status(monkeypatch: pytest.MonkeyPatch) -> None:
    _ready_env(monkeypatch)
    ok = CliRunner().invoke(app, ["health", "--expected-model", PIN])
    assert ok.exit_code == 0
    assert json.loads(ok.stdout.strip().splitlines()[0])["status"] == "READY"
    monkeypatch.delenv("GEMINI_API_KEY")
    blocked = CliRunner().invoke(app, ["health", "--expected-model", PIN])
    assert blocked.exit_code == 2
