from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest


_SCRIPT = Path(__file__).resolve().parents[2] / "ops/asus-server/venho-os/growth-backend-switch.sh"
_ENV = b'OTHER="line one\nGROWTH_BACKEND=literal\nline three"\nexport GROWTH_BACKEND=legacy\nGROWTH_BACKEND=legacy\nTAIL=value\n'


@pytest.fixture
def setup(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    app = tmp_path / "venho/venho-os"
    app.mkdir(parents=True)
    dotenv = app / ".env.local"
    dotenv.write_bytes(_ENV)
    registry = tmp_path / "venho/growth-runtime/venho-ai-studio/data/projects/venho_hotel/publishing/publication_registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"publications": [
        {"publication_id": "one", "slot_id": "slot-2026-11-19-fb", "status": "PENDING_APPROVAL"},
    ]}))
    stubs = tmp_path / "bin"
    stubs.mkdir()
    scripts = {
        "date": '''case "$*" in
          +%H%M) echo "$TEST_CLOCK";;
          +%F) echo 2026-11-19;;
          *) echo 20261119T060000Z;;
        esac''',
        "flock": "exit 0",
        "systemctl": '''if [[ "$2" == restart ]]; then
          mode="$(awk -F= '$1 == "GROWTH_BACKEND" {mode=$2} END {print mode}' "$HOME/venho/venho-os/.env.local")"
          [[ "$mode" != v2 || "${TEST_RESTART_FAIL:-}" != yes ]] || exit 1
          printf '%s' "$mode" > "$HOME/runtime"
        fi''',
        "curl": '''if [[ "${!#}" == */login ]]; then printf '200'; else
          printf 'X-Venho-Growth-Backend: %s\\r\\n' "$(cat "$HOME/runtime")"
        fi''',
    }
    for name, body in scripts.items():
        path = stubs / name
        path.write_text(f"#!/usr/bin/env bash\nset -e\n{body}\n")
        path.chmod(0o700)
    (tmp_path / "runtime").write_text("legacy")
    return dotenv, {**os.environ, "HOME": str(tmp_path), "PATH": f"{stubs}:{os.environ['PATH']}", "TEST_CLOCK": "1500"}


def _run(mode: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(_SCRIPT), mode], env=env, capture_output=True, text=True, timeout=10)


def test_switch_updates_only_backend_and_verifies_both_modes(setup) -> None:
    dotenv, env = setup
    result = _run("v2", env)
    assert result.returncode == 0, result.stderr
    assert "GROWTH_BACKEND=v2" in result.stdout
    assert "WARN LEGACY_PENDING_APPROVAL_TODAY=1" in result.stdout
    assert dotenv.read_bytes() == _ENV.replace(
        b"export GROWTH_BACKEND=legacy\nGROWTH_BACKEND=legacy\n", b"GROWTH_BACKEND=v2\n"
    )
    (backup,) = dotenv.parent.glob(".env.local.bak-*")
    assert backup.read_bytes() == _ENV
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600
    returned = _run("legacy", env)
    assert returned.returncode == 0 and "GROWTH_BACKEND=legacy" in returned.stdout


@pytest.mark.parametrize("clock", ["0830", "0900", "0930"])
def test_switch_blocks_publish_window_before_mutation(setup, clock) -> None:
    dotenv, env = setup
    result = _run("v2", {**env, "TEST_CLOCK": clock})
    assert result.returncode != 0 and "08:30" in result.stderr
    assert dotenv.read_bytes() == _ENV
    assert not list(dotenv.parent.glob(".env.local.bak-*"))


def test_switch_rolls_back_to_verified_legacy_if_restart_fails(setup) -> None:
    dotenv, env = setup
    result = _run("v2", {**env, "TEST_RESTART_FAIL": "yes"})
    assert result.returncode != 0 and "GROWTH_BACKEND_ROLLBACK=PASS" in result.stderr
    assert dotenv.read_bytes() == _ENV.replace(b"export GROWTH_BACKEND=legacy\n", b"")
    assert (Path(env["HOME"]) / "runtime").read_text() == "legacy"
