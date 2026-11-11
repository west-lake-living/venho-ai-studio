from __future__ import annotations

import fcntl
import os
from pathlib import Path
from types import SimpleNamespace

from growth_engine import bootstrap


def _service(db_path: Path) -> bootstrap.DoctorService:
    return bootstrap.DoctorService(
        SimpleNamespace(db_path=str(db_path)),
        connect=lambda _path: None,
        migration_runner=lambda _path: None,
        sqlite_version_check=lambda _version: None,
        sqlite_version_error=ValueError,
    )


def _simulate_held_lock(monkeypatch) -> None:
    def flock(_descriptor: int, operation: int) -> None:
        if operation & fcntl.LOCK_EX and operation & fcntl.LOCK_NB:
            raise BlockingIOError

    monkeypatch.setattr(fcntl, "flock", flock)


def test_doctor_passes_when_the_active_systemd_publish_unit_owns_lock(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "growth_engine.db"
    db_path.touch()
    (tmp_path / "publish.lock").touch()
    _simulate_held_lock(monkeypatch)
    owner_pid = os.getpid()
    monkeypatch.setattr(bootstrap, "_publish_lock_owner_pids", lambda _path: (owner_pid,))
    monkeypatch.setattr(bootstrap, "_systemd_publish_unit", lambda: ("active", owner_pid))

    check = _service(db_path)._publish_lock_check()

    assert check.status == "PASS"
    assert "đúng thiết kế" in check.detail


def test_doctor_fails_when_a_second_process_owns_publish_lock(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "growth_engine.db"
    db_path.touch()
    (tmp_path / "publish.lock").touch()
    _simulate_held_lock(monkeypatch)
    monkeypatch.setattr(bootstrap, "_publish_lock_owner_pids", lambda _path: (os.getpid() + 1000,))
    monkeypatch.setattr(bootstrap, "_systemd_publish_unit", lambda: ("active", os.getpid()))

    check = _service(db_path)._publish_lock_check()

    assert check.status == "FAIL"
    assert "không thuộc instance systemd" in check.detail


def test_api_and_worker_units_are_installable_and_runbook_checks_linger() -> None:
    root = Path("ops/asus-server/growth-engine")
    for filename in ("growth-engine-api.service", "growth-engine-worker@.service"):
        text = (root / filename).read_text(encoding="utf-8")
        assert "[Install]" in text
        assert "WantedBy=default.target" in text

    runbook = Path("docs/growth_engine/runbooks/production_cutover.md").read_text(encoding="utf-8")
    assert "loginctl show-user" in runbook
    assert "loginctl enable-linger" in runbook
