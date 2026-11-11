from __future__ import annotations

import importlib.util
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


_SCRIPT = Path("ops/asus-server/growth-engine/configure-production-cloudflared-ingress.py")
_SPEC = importlib.util.spec_from_file_location("configure_production_cloudflared_ingress", _SCRIPT)
assert _SPEC and _SPEC.loader
ingress = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = ingress
_SPEC.loader.exec_module(ingress)


CONFIG = """tunnel: synthetic-id
credentials-file: /tmp/synthetic-creds.json
ingress:
  - hostname: existing.venhohotel.com
    service: http://127.0.0.1:8000
  - service: http_status:404
"""


class FakeCommands:
    def __init__(self, *, fail_restart: bool = False, fail_validate: bool = False):
        self.calls: list[list[str]] = []
        self.fail_restart = fail_restart
        self.fail_validate = fail_validate
        self.restart_count = 0

    def __call__(self, command, **kwargs):
        values = list(command)
        self.calls.append(values)
        if values[:2] == ["systemctl", "restart"]:
            self.restart_count += 1
        failed = (
            self.fail_restart and values[:2] == ["systemctl", "restart"] and self.restart_count == 1
        ) or (
            self.fail_validate and values[-2:] == ["ingress", "validate"]
        )
        return subprocess.CompletedProcess(values, 1 if failed else 0)


def test_adds_rule_before_catchall_and_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "config.yml"
    path.write_text(CONFIG, encoding="utf-8")
    commands = FakeCommands()
    now = datetime(2026, 11, 11, tzinfo=timezone.utc)

    result = ingress.configure(path, runner=commands, find_executable=lambda _: "/fake/bin", now=now)
    content = path.read_text(encoding="utf-8")

    assert result.startswith("configured backup=")
    assert content.index("hostname: growth-api.venhohotel.com") < content.index("service: http_status:404")
    assert "path: ^/(internal|media/publish)/" in content
    assert "service: http://127.0.0.1:8021" in content
    assert (tmp_path / "config.yml.bak-production-20261111T000000Z").read_text() == CONFIG
    assert ["systemctl", "restart", "cloudflared.service"] in commands.calls
    assert ["systemctl", "is-active", "--quiet", "cloudflared.service"] in commands.calls

    commands.calls.clear()
    assert ingress.configure(path, runner=commands, find_executable=lambda _: "/fake/bin", now=now) == "already_configured"
    assert not any(call[:2] == ["systemctl", "restart"] for call in commands.calls)


def test_invalid_candidate_does_not_change_config_or_make_backup(tmp_path: Path) -> None:
    path = tmp_path / "config.yml"
    path.write_text(CONFIG, encoding="utf-8")
    commands = FakeCommands(fail_validate=True)

    try:
        ingress.configure(path, runner=commands, find_executable=lambda _: "/fake/bin")
    except ingress.ConfigError as error:
        assert "did not validate" in str(error)
    else:
        raise AssertionError("invalid fake ingress should fail")

    assert path.read_text(encoding="utf-8") == CONFIG
    assert not list(tmp_path.glob("*.bak-production-*"))
    assert not list(tmp_path.glob("*.candidate-*"))


def test_restart_failure_restores_backup_and_restarts_old_config(tmp_path: Path) -> None:
    path = tmp_path / "config.yml"
    path.write_text(CONFIG, encoding="utf-8")
    commands = FakeCommands(fail_restart=True)

    try:
        ingress.configure(path, runner=commands, find_executable=lambda _: "/fake/bin")
    except ingress.ConfigError as error:
        assert "failed after restart" in str(error)
    else:
        raise AssertionError("failed service restart should fail")

    assert path.read_text(encoding="utf-8") == CONFIG
    assert len([call for call in commands.calls if call[:2] == ["systemctl", "restart"]]) == 2


def test_refuses_wrong_existing_destination_or_missing_final_catchall() -> None:
    wrong = CONFIG.replace("http_status:404", "http://127.0.0.1:8022")
    for text in (
        wrong.replace("hostname: existing.venhohotel.com", "hostname: growth-api.venhohotel.com\n    path: ^/(internal|media/publish)/"),
        CONFIG.replace("  - service: http_status:404\n", ""),
    ):
        try:
            ingress.add_rule(text)
        except ingress.ConfigError:
            pass
        else:
            raise AssertionError("unsafe ingress should be rejected")
