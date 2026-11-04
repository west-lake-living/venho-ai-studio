from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from growth_engine.adapters.inbound.cli.main import app
from growth_engine.adapters.outbound.persistence.sqlite.connection import (
    SQLiteVersionError,
    check_sqlite_version,
    connect,
)
from growth_engine.adapters.outbound.persistence.sqlite.migrator import (
    MigrationChecksumMismatch,
    MigrationRunner,
    PendingMigrations,
)


def test_connect_sets_required_pragmas_on_every_connection(tmp_path: Path) -> None:
    path = tmp_path / "growth.db"
    connection = connect(path)
    try:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert connection.execute("PRAGMA synchronous").fetchone()[0] == 2
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    finally:
        connection.close()
    with connect(path) as reopened:
        assert reopened.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_new_database_migrates_and_repeat_is_noop(tmp_path: Path) -> None:
    database = tmp_path / "growth.db"
    migrations = Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")
    runner = MigrationRunner(migrations)
    with connect(database) as connection:
        assert runner.apply(connection, application_version="synthetic-test") == 8
        assert runner.check(connection) == (1, 2, 3, 4, 5, 6, 7, 9)
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='runtime_controls'"
        ).fetchone()[0] == "runtime_controls"
        assert runner.apply(connection, application_version="synthetic-test") == 0
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_applied_migration_checksum_mismatch_stops(tmp_path: Path) -> None:
    # Temporary migration is a synthetic fixture; replace with verified migration evidence from P0-T03/P0-T04.
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    migration = migrations / "0001_core.sql"
    migration.write_text("-- _synthetic: true\nCREATE TABLE sample(value TEXT);\n", encoding="utf-8")
    runner = MigrationRunner(migrations)
    with connect(tmp_path / "growth.db") as connection:
        runner.apply(connection, application_version="synthetic-test")
        migration.write_text("-- _synthetic: true\nCREATE TABLE sample(value INTEGER);\n", encoding="utf-8")
        with pytest.raises(MigrationChecksumMismatch):
            runner.apply(connection, application_version="synthetic-test")


def test_migration_check_does_not_apply_pending_schema(tmp_path: Path) -> None:
    migrations = Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")
    runner = MigrationRunner(migrations)
    with connect(tmp_path / "growth.db") as connection:
        with pytest.raises(PendingMigrations):
            runner.check(connection)
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_controls'"
        ).fetchone() is None


def test_migrations_apply_by_numeric_version(tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "10_tenth.sql").write_text(
        "INSERT INTO migration_order(version) VALUES (10);", encoding="utf-8"
    )
    (migrations / "2_second.sql").write_text(
        "INSERT INTO migration_order(version) VALUES (2);", encoding="utf-8"
    )
    (migrations / "1_first.sql").write_text(
        "CREATE TABLE migration_order(version INTEGER);"
        "INSERT INTO migration_order(version) VALUES (1);",
        encoding="utf-8",
    )
    runner = MigrationRunner(migrations)
    with connect(tmp_path / "ordered.db") as connection:
        assert runner.apply(connection, application_version="synthetic-test") == 3
        versions = connection.execute("SELECT version FROM migration_order ORDER BY rowid").fetchall()
        assert [row[0] for row in versions] == [1, 2, 10]


def test_sqlite_version_gate_uses_runtime_link_version() -> None:
    check_sqlite_version(sqlite3.sqlite_version_info)
    with pytest.raises(SQLiteVersionError):
        check_sqlite_version((3, 51, 2))


def test_cli_migrate_and_check_use_configured_database_and_service(tmp_path: Path) -> None:
    database = tmp_path / "cli.db"

    class FakeMigrationService:
        calls: list[tuple[Path, bool]]

        def __init__(self) -> None:
            self.calls = []

        def run(self, db_path: Path, check: bool) -> str:
            self.calls.append((db_path, check))
            return "migration check complete" if check else "migration applied"

    service = FakeMigrationService()
    runner = CliRunner()
    env = {"GE_ENV": "test", "GE_DB_PATH": str(database)}
    applied = runner.invoke(app, ["migrate"], env=env, obj={"migration_service": service})
    assert applied.exit_code == 0, applied.output
    assert "migration applied" in applied.output
    checked = runner.invoke(
        app,
        ["migrate", "--check"],
        env=env,
        obj={"migration_service": service},
    )
    assert checked.exit_code == 0, checked.output
    assert "migration check complete" in checked.output
    assert service.calls == [(database, False), (database, True)]
