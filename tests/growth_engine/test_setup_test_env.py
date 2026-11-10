from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from pathlib import Path

from growth_engine.adapters.outbound.security.capability_tokens import parse_key_ring
from growth_engine.settings import Settings

SCRIPT = Path(__file__).resolve().parents[2] / "ops/asus-server/growth-engine/setup-test-env.sh"


def _run_setup(home: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["HOME"] = str(home)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_setup_creates_isolated_private_test_environment_and_make_bearer_handoff(
    tmp_path: Path,
) -> None:
    home = tmp_path / "fake-home"
    production_env = home / "venho/secrets/growth-engine.env"
    production_env.parent.mkdir(parents=True)
    production_env.parent.chmod(0o700)
    production_env.write_text("GE_ENV=production\nPRESERVE=synthetic\n", encoding="utf-8")
    production_env.chmod(0o600)
    production_before = production_env.read_bytes()
    production_mode_before = _mode(production_env)

    result = _run_setup(home)

    assert result.returncode == 0, "TEST env setup should succeed with a fake HOME"
    env_path = home / "venho/secrets/growth-engine-test.env"
    handoff_path = home / "venho/secrets/growth-engine-test.make-bearers.tmp"
    env_text = env_path.read_text(encoding="utf-8")
    handoff_text = handoff_path.read_text(encoding="utf-8")
    values = dict(line.split("=", 1) for line in env_text.splitlines())
    bearer_values = dict(line.split("=", 1) for line in handoff_text.splitlines() if not line.startswith("#"))
    service_tokens = dict(
        entry.split(":", 1) for entry in values["GE_SERVICE_TOKENS"].split(",")
    )

    assert values["GE_ENV"] == "test"
    assert values["GE_DB_PATH"] == str(home / "venho/state/growth-engine-test/growth_engine.db")
    assert values["GE_MEDIA_ROOT"] == str(home / "venho/state/growth-engine-test/media")
    assert values["GE_PUBLIC_BASE_URL"] == "https://ge-test.venhohotel.com"
    assert values["GE_CAPABILITY_KEYS"].startswith("test-")
    settings = Settings.from_env(values)
    assert settings.env == "test"
    assert len(parse_key_ring(settings.capability_keys)[values["GE_CAPABILITY_KEYS"].split(":", 1)[0]]) == 32
    assert set(service_tokens) == {"make-fb-hanoi", "make-fb-venho", "make-ig"}
    expected_handoff = {
        "GE_TEST_BEARER_FB_HANOI": "make-fb-hanoi",
        "GE_TEST_BEARER_FB_VENHO": "make-fb-venho",
        "GE_TEST_BEARER_IG": "make-ig",
    }
    for variable, principal in expected_handoff.items():
        bearer = bearer_values[variable]
        assert service_tokens[principal] == hashlib.sha256(bearer.encode("utf-8")).hexdigest()
    assert not any(bearer in env_text for bearer in bearer_values.values()), "raw bearer leaked into env"
    assert _mode(env_path) == 0o600
    assert _mode(handoff_path) == 0o600
    assert _mode(env_path.parent) == 0o700
    assert result.stdout and not any(bearer in result.stdout for bearer in bearer_values.values())
    assert production_env.read_bytes() == production_before
    assert _mode(production_env) == production_mode_before


def test_setup_is_idempotent_and_does_not_recreate_deleted_bearers(tmp_path: Path) -> None:
    home = tmp_path / "fake-home"
    first = _run_setup(home)
    assert first.returncode == 0, "initial fake setup should succeed"
    env_path = home / "venho/secrets/growth-engine-test.env"
    handoff_path = home / "venho/secrets/growth-engine-test.make-bearers.tmp"
    env_before = env_path.read_bytes()
    handoff_before = handoff_path.read_bytes()

    second = _run_setup(home)
    assert second.returncode == 0, "rerun should be a no-op"
    if env_path.read_bytes() != env_before or handoff_path.read_bytes() != handoff_before:
        raise AssertionError("rerun rotated TEST secrets")

    handoff_path.unlink()
    third = _run_setup(home)
    assert third.returncode == 0, "rerun after handoff deletion should remain safe"
    if env_path.read_bytes() != env_before:
        raise AssertionError("rerun changed the established TEST env")
    assert not handoff_path.exists(), "rerun must not recreate deleted plaintext bearers"


def test_test_service_uses_loopback_port_8023_and_only_test_state() -> None:
    unit = SCRIPT.with_name("growth-engine-api-test.service").read_text(encoding="utf-8")

    assert "EnvironmentFile=%h/venho/secrets/growth-engine-test.env" in unit
    assert "Environment=GE_ENV=test" in unit
    assert "--host 127.0.0.1 --port 8023" in unit
    assert "ReadWritePaths=%h/venho/state/growth-engine-test" in unit
    assert "growth-engine.env\n" not in unit
    assert "--port 8022" not in unit
