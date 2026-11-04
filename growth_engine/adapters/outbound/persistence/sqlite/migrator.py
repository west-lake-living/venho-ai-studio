from __future__ import annotations

import hashlib
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


class MigrationError(RuntimeError):
    pass


class MigrationChecksumMismatch(MigrationError):
    pass


class PendingMigrations(MigrationError):
    pass


class UnknownMigration(MigrationError):
    pass


@dataclass(frozen=True)
class MigrationFile:
    version: int
    name: str
    sql: str
    checksum: str


class MigrationRunner:
    def __init__(self, migrations_dir: str | Path) -> None:
        self.migrations_dir = Path(migrations_dir)

    def apply(self, connection: sqlite3.Connection, *, application_version: str) -> int:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                   version INTEGER PRIMARY KEY,
                   name TEXT NOT NULL,
                   checksum TEXT NOT NULL,
                   applied_at INTEGER NOT NULL,
                   application_version TEXT NOT NULL
               )"""
        )
        migrations = self._migration_files()
        applied = self._applied_migrations(connection)
        files_by_version = {migration.version: migration for migration in migrations}
        for version, (name, checksum) in applied.items():
            migration = files_by_version.get(version)
            if migration is None:
                raise UnknownMigration(f"database contains migration {version:04d} absent from source")
            if name != migration.name or checksum != migration.checksum:
                raise MigrationChecksumMismatch(f"applied migration {version:04d} differs from source")

        count = 0
        for migration in migrations:
            if migration.version in applied:
                continue
            escaped_name = _sql_text(migration.name)
            escaped_checksum = _sql_text(migration.checksum)
            escaped_app_version = _sql_text(application_version)
            applied_at = time.time_ns() // 1_000_000
            script = (
                "BEGIN IMMEDIATE;\n"
                + migration.sql
                + "\nINSERT INTO schema_migrations "
                "(version, name, checksum, applied_at, application_version) VALUES "
                f"({migration.version}, '{escaped_name}', '{escaped_checksum}', "
                f"{applied_at}, '{escaped_app_version}');\nCOMMIT;"
            )
            try:
                connection.executescript(script)
            except Exception:
                if connection.in_transaction:
                    connection.rollback()
                raise
            count += 1
        return count

    def check(self, connection: sqlite3.Connection) -> tuple[int, ...]:
        migrations = self._migration_files()
        applied = self._applied_migrations(connection)
        files_by_version = {migration.version: migration for migration in migrations}
        for version, (name, checksum) in applied.items():
            migration = files_by_version.get(version)
            if migration is None:
                raise UnknownMigration(f"database contains migration {version:04d} absent from source")
            if name != migration.name or checksum != migration.checksum:
                raise MigrationChecksumMismatch(f"applied migration {version:04d} differs from source")
        pending = tuple(migration.version for migration in migrations if migration.version not in applied)
        if pending:
            rendered = ", ".join(f"{version:04d}" for version in pending)
            raise PendingMigrations(f"pending migrations: {rendered}")
        return tuple(sorted(applied))

    def _migration_files(self) -> list[MigrationFile]:
        if not self.migrations_dir.is_dir():
            raise MigrationError(f"migration directory does not exist: {self.migrations_dir}")
        files = list(self.migrations_dir.glob("*.sql"))
        migrations: list[MigrationFile] = []
        seen_versions: set[int] = set()
        numbered_files: list[tuple[int, Path]] = []
        for path in files:
            match = re.match(r"^(\d+)_.*\.sql$", path.name)
            if match is None:
                raise MigrationError(f"invalid migration filename: {path.name}")
            version = int(match.group(1))
            if version in seen_versions:
                raise MigrationError(f"duplicate migration version: {version:04d}")
            seen_versions.add(version)
            numbered_files.append((version, path))
        for version, path in sorted(numbered_files, key=lambda item: item[0]):
            contents = path.read_bytes()
            migrations.append(
                MigrationFile(
                    version=version,
                    name=path.name,
                    sql=contents.decode("utf-8"),
                    checksum=hashlib.sha256(contents).hexdigest(),
                )
            )
        return migrations

    @staticmethod
    def _applied_migrations(connection: sqlite3.Connection) -> dict[int, tuple[str, str]]:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        if table is None:
            return {}
        return {
            int(row[0]): (str(row[1]), str(row[2]))
            for row in connection.execute("SELECT version, name, checksum FROM schema_migrations")
        }


def _sql_text(value: str) -> str:
    return value.replace("'", "''")
