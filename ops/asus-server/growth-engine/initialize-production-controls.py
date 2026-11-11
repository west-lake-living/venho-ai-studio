#!/usr/bin/env python3
"""Create the first production runtime-control row fail-closed and with audit."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from uuid import uuid4


def initialize(db_path: str | Path, *, now_ms: int | None = None) -> str:
    path = Path(db_path).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError("production database must be an existing regular file")
    timestamp = time.time_ns() // 1_000_000 if now_ms is None else now_ms
    connection = sqlite3.connect(path, timeout=30, isolation_level=None)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("BEGIN IMMEDIATE")
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if not {"schema_migrations", "runtime_controls", "audit_events"}.issubset(tables):
            raise ValueError("production schema is not migrated")
        version = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        if not isinstance(version, int) or version < 9:
            raise ValueError("production schema is behind the reviewed version")
        existing = connection.execute(
            "SELECT publish_mode, global_pause FROM runtime_controls WHERE environment='production'"
        ).fetchone()
        if existing is not None:
            if existing["publish_mode"] == "DISABLED" and int(existing["global_pause"]) == 1:
                connection.execute("COMMIT")
                return "already_initialized"
            raise ValueError("existing production controls are not fail-closed; no change made")

        epoch = "bootstrap-" + uuid4().hex
        snapshot = {"mode": "DISABLED", "dispatch_epoch": epoch, "global_pause": True}
        after_hash = hashlib.sha256(
            json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        connection.execute(
            """INSERT INTO runtime_controls
               (environment, publish_mode, dispatch_epoch, global_pause, policy_version, updated_at)
               VALUES ('production', 'DISABLED', ?, 1, 'gc2-production-bootstrap-v1', ?)""",
            (epoch, timestamp),
        )
        connection.execute(
            """INSERT INTO audit_events
               (id, aggregate_type, aggregate_id, actor, action, before_hash, after_hash,
                details_json, correlation_id, created_at)
               VALUES (?, 'runtime_controls', 'production', 'gc2-production-bootstrap',
                       'initialize_disabled', NULL, ?, ?, ?, ?)""",
            (
                str(uuid4()),
                after_hash,
                '{"global_pause":true,"publish_mode":"DISABLED"}',
                str(uuid4()),
                timestamp,
            ),
        )
        connection.execute("COMMIT")
        return "initialized"
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def main() -> int:
    if os.environ.get("GE_ENV", "").strip() != "production":
        print("FAIL: GE_ENV must be production", file=sys.stderr)
        return 2
    raw_db = os.environ.get("GE_DB_PATH", "").strip()
    if not raw_db:
        print("FAIL: GE_DB_PATH is missing", file=sys.stderr)
        return 2
    expected_root = (Path.home() / "venho/state/growth-engine").resolve()
    try:
        resolved = Path(raw_db).expanduser().resolve(strict=True)
        resolved.relative_to(expected_root)
        result = initialize(resolved)
    except (OSError, ValueError, sqlite3.Error):
        print("FAIL: production controls not initialized; verify production state path/schema", file=sys.stderr)
        return 1
    print(f"production_controls={result} mode=DISABLED global_pause=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
