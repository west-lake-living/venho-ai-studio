from __future__ import annotations

import sqlite3
from pathlib import Path


MIN_SQLITE_VERSION = (3, 51, 3)


class SQLiteVersionError(RuntimeError):
    pass


def check_sqlite_version(version: tuple[int, ...]) -> None:
    if tuple(version[:3]) < MIN_SQLITE_VERSION:
        actual = ".".join(str(part) for part in version[:3])
        required = ".".join(str(part) for part in MIN_SQLITE_VERSION)
        raise SQLiteVersionError(f"Python SQLite {actual} is below required {required}")


def connect(path: str | Path) -> sqlite3.Connection:
    check_sqlite_version(sqlite3.sqlite_version_info)
    connection = sqlite3.connect(str(path), timeout=5.0, isolation_level=None)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=5000")
        if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise RuntimeError("SQLite foreign_keys pragma is not enabled")
    except Exception:
        connection.close()
        raise
    return connection
