from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
from pathlib import Path


_SCRIPT = Path("ops/asus-server/growth-engine/setup-production-make-bearers.py")
_SPEC = importlib.util.spec_from_file_location("setup_production_make_bearers", _SCRIPT)
assert _SPEC and _SPEC.loader
provisioner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = provisioner
_SPEC.loader.exec_module(provisioner)


def test_creates_hashed_server_tokens_and_private_handoff(tmp_path: Path) -> None:
    env = tmp_path / "growth-engine.env"
    handoff = tmp_path / "growth-engine.make-bearers.tmp"
    env.write_text("GE_ENV=production\nKEEP=value\nGE_SERVICE_TOKENS=REQUIRED_FROM_P0\n", encoding="utf-8")
    os.chmod(env, 0o600)
    made = iter(("FAKE_BEARER_HANOI", "FAKE_BEARER_VENHO", "FAKE_BEARER_IG"))

    assert provisioner.provision(env, handoff, token_factory=lambda: next(made)) == "created"
    env_text = env.read_text(encoding="utf-8")
    handoff_text = handoff.read_text(encoding="utf-8")
    _, values = provisioner._assignments(handoff_text)

    assert "KEEP=value\n" in env_text
    assert "FAKE_BEARER" not in env_text
    assert "GE_CAPABILITY_KEYS=prod-" in env_text
    assert "REQUIRED_FROM_P0" not in env_text
    assert env.stat().st_mode & 0o777 == 0o600
    assert handoff.stat().st_mode & 0o777 == 0o600
    for (principal, variable), bearer in zip(provisioner.PRINCIPALS, values.values()):
        digest = hashlib.sha256(bearer.encode()).hexdigest()
        assert f"{principal}:{digest}" in env_text
    assert all(value.startswith("FAKE_BEARER_") for value in values.values())

    assert provisioner.provision(env, handoff, token_factory=lambda: "SHOULD_NOT_ROTATE") == "already_configured"
    assert "SHOULD_NOT_ROTATE" not in handoff.read_text(encoding="utf-8")


def test_refuses_silent_rotation_when_hashes_exist_without_handoff(tmp_path: Path) -> None:
    env = tmp_path / "growth-engine.env"
    handoff = tmp_path / "growth-engine.make-bearers.tmp"
    env.write_text("GE_ENV=production\nGE_SERVICE_TOKENS=make-fb-hanoi:" + "a" * 64 + "\n", encoding="utf-8")
    os.chmod(env, 0o600)

    try:
        provisioner.provision(env, handoff, token_factory=lambda: "SYNTHETIC")
    except provisioner.ProvisionError as error:
        assert "refusing rotation" in str(error)
    else:
        raise AssertionError("existing hashes without their handoff must not be rotated")

    assert not handoff.exists()
    assert "SYNTHETIC" not in env.read_text(encoding="utf-8")


def test_explicit_rotation_replaces_unknown_hashes_and_writes_mode_600_handoff(tmp_path: Path) -> None:
    env = tmp_path / "growth-engine.env"
    handoff = tmp_path / "growth-engine.make-bearers.tmp"
    env.write_text(
        "GE_ENV=production\nGE_SERVICE_TOKENS=make-fb-hanoi:" + "a" * 64 + "\n",
        encoding="utf-8",
    )
    os.chmod(env, 0o600)
    made = iter((
        "new_hanoi_bearer_0123456789_abcdefghijklmnopqrstuvwxyz",
        "new_venho_bearer_0123456789_abcdefghijklmnopqrstuvwxyz",
        "new_ig_bearer_0123456789_abcdefghijklmnopqrstuvwxyz",
    ))

    assert provisioner.provision(
        env,
        handoff,
        rotate_existing=True,
        token_factory=lambda: next(made),
    ) == "rotated"

    env_text = env.read_text(encoding="utf-8")
    handoff_text = handoff.read_text(encoding="utf-8")
    _, values = provisioner._assignments(handoff_text)
    assert env.stat().st_mode & 0o777 == 0o600
    assert handoff.stat().st_mode & 0o777 == 0o600
    assert "new_hanoi_bearer" not in env_text
    assert "make-fb-hanoi:" + "a" * 64 not in env_text
    for principal, variable in provisioner.PRINCIPALS:
        digest = hashlib.sha256(values[variable].encode("utf-8")).hexdigest()
        assert f"{principal}:{digest}" in env_text


def test_invalid_capability_key_aborts_without_writing_handoff(tmp_path: Path) -> None:
    env = tmp_path / "growth-engine.env"
    handoff = tmp_path / "growth-engine.make-bearers.tmp"
    original = "GE_ENV=production\nGE_SERVICE_TOKENS=REQUIRED_FROM_P0\nGE_CAPABILITY_KEYS=REQUIRED_FROM_P0\n"
    env.write_text(original, encoding="utf-8")
    os.chmod(env, 0o600)

    try:
        provisioner.provision(
            env,
            handoff,
            token_factory=lambda: "SYNTHETIC_TOKEN",
            capability_factory=lambda: "bad:not-base64",
        )
    except provisioner.ProvisionError:
        pass
    else:
        raise AssertionError("invalid capability key must fail closed")

    assert env.read_text(encoding="utf-8") == original
    assert not handoff.exists()


def test_refuses_test_environment_and_wrong_permissions(tmp_path: Path) -> None:
    env = tmp_path / "growth-engine.env"
    handoff = tmp_path / "growth-engine.make-bearers.tmp"
    env.write_text("GE_ENV=test\nGE_SERVICE_TOKENS=REQUIRED_FROM_P0\n", encoding="utf-8")
    os.chmod(env, 0o600)
    try:
        provisioner.provision(env, handoff)
    except provisioner.ProvisionError:
        pass
    else:
        raise AssertionError("TEST env must be refused")
    env.write_text("GE_ENV=production\nGE_SERVICE_TOKENS=REQUIRED_FROM_P0\n", encoding="utf-8")
    os.chmod(env, 0o644)
    try:
        provisioner.provision(env, handoff)
    except provisioner.ProvisionError:
        pass
    else:
        raise AssertionError("non-private env must be refused")
