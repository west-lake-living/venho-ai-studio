from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner


_SCRIPT = Path("ops/asus-server/growth-engine/initialize-production-controls.py")
_SPEC = importlib.util.spec_from_file_location("initialize_production_controls", _SCRIPT)
assert _SPEC and _SPEC.loader
bootstrap = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = bootstrap
_SPEC.loader.exec_module(bootstrap)

MIGRATIONS = Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")


def _database(path: Path) -> None:
    connection = connect(path)
    try:
        MigrationRunner(MIGRATIONS).apply(connection, application_version="pytest")
    finally:
        connection.close()


def test_initializes_disabled_and_globally_paused_with_audit_once(tmp_path: Path) -> None:
    path = tmp_path / "growth_engine.db"
    _database(path)

    assert bootstrap.initialize(path, now_ms=1_798_790_400_000) == "initialized"
    assert bootstrap.initialize(path, now_ms=1_798_790_400_001) == "already_initialized"

    connection = sqlite3.connect(path)
    try:
        control = connection.execute(
            "SELECT publish_mode, global_pause FROM runtime_controls WHERE environment='production'"
        ).fetchone()
        audit = connection.execute(
            "SELECT action, aggregate_id, after_hash FROM audit_events WHERE aggregate_type='runtime_controls'"
        ).fetchall()
    finally:
        connection.close()
    assert control == ("DISABLED", 1)
    assert len(audit) == 1
    assert audit[0][0:2] == ("initialize_disabled", "production")
    assert len(audit[0][2]) == 64


def test_refuses_to_overwrite_non_disabled_production_mode(tmp_path: Path) -> None:
    path = tmp_path / "growth_engine.db"
    _database(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """INSERT INTO runtime_controls
               (environment, publish_mode, dispatch_epoch, global_pause, policy_version, updated_at)
               VALUES ('production','LIVE_MANUAL','synthetic-epoch',0,'test',1)"""
        )
        connection.commit()
    finally:
        connection.close()

    try:
        bootstrap.initialize(path, now_ms=2)
    except ValueError as error:
        assert "not fail-closed" in str(error)
    else:
        raise AssertionError("bootstrap must not overwrite an existing runtime mode")

    connection = sqlite3.connect(path)
    try:
        assert connection.execute(
            "SELECT publish_mode, global_pause FROM runtime_controls WHERE environment='production'"
        ).fetchone() == ("LIVE_MANUAL", 0)
    finally:
        connection.close()
