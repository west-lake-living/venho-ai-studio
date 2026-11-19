#!/usr/bin/env python3
"""Inventory frozen legacy publishing state and retain a private rollback copy."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import tempfile
from collections import Counter
from contextlib import closing
from pathlib import Path


SAFE_TERMINAL = {"CANCELLED", "REJECTED", "STALE_APPROVAL", "FAILED"}
PROJECT = Path("data/projects/venho_hotel")


def blockers(registry: dict, first: str) -> dict[str, int]:
    rows = registry["publications"]
    if not isinstance(rows, list):
        raise ValueError("publication_registry_invalid")
    outstanding: Counter[str] = Counter()
    for row in rows:
        match = re.match(r"^slot-(\d{4}-\d{2}-\d{2})(?:-|$)", row.get("slot_id") or "")
        status = row.get("status")
        if status == "DISPATCHING":
            outstanding["dispatching"] += 1
        elif match and match[1] >= first and status not in SAFE_TERMINAL:
            reason = {
                "APPROVED_SCHEDULED": "approved_scheduled",
                "PENDING_APPROVAL": "pending_approval",
                "PUBLISHED": "already_published",
                "GATEWAY_ERROR": "gateway_error",
            }.get(status, "other_unresolved")
            outstanding[reason] += 1
        elif not match and status not in SAFE_TERMINAL | {"PUBLISHED"}:
            outstanding["undated_unresolved"] += 1
    return dict(outstanding)


def sqlite_snapshot(source_path: Path, target: Path) -> None:
    with closing(sqlite3.connect(source_path.resolve().as_uri() + "?mode=ro", uri=True)) as source:
        with closing(sqlite3.connect(target)) as destination:
            source.backup(destination)
            if destination.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ValueError("legacy_sqlite_snapshot_invalid")


def snapshot(legacy: Path, evidence: Path, *, check: bool, insights: Path | None) -> bool:
    registry = legacy / PROJECT / "publishing/publication_registry.json"
    data = registry.read_bytes()
    pending = blockers(json.loads(data), "2026-11-25")
    if pending:
        print(json.dumps({"result": "BLOCKED", "legacy_blockers": pending}, sort_keys=True))
        return False
    if check:
        print('{"result":"PASS","legacy_blockers":{}}')
        return True

    if insights is None or not insights.is_file():
        raise ValueError("legacy_insights_database_missing")
    target = evidence / "legacy-snapshot"
    if target.exists():
        manifest = json.loads((target / "manifest.json").read_text())
        if manifest["publication_registry.json"] != hashlib.sha256(data).hexdigest():
            raise ValueError("legacy_registry_changed_after_snapshot")
        for name in ("publication_registry.json", "slots_snapshot.json", "growth.db", "insights.db"):
            if hashlib.sha256((target / "source" / name).read_bytes()).hexdigest() != manifest[name]:
                raise ValueError("legacy_snapshot_checksum_mismatch")
        print('{"result":"PASS","legacy_snapshot":"existing_verified"}')
        return True
    with tempfile.TemporaryDirectory(dir=evidence, prefix=".legacy-") as temporary:
        directory = Path(temporary) / "snapshot"
        directory.mkdir(mode=0o700)
        source_directory = directory / "source"
        source_directory.mkdir(mode=0o700)
        (source_directory / "publication_registry.json").write_bytes(data)
        shutil.copyfile(legacy / PROJECT / "growth/slots_snapshot.json", source_directory / "slots_snapshot.json")
        sqlite_snapshot(legacy / PROJECT / "growth/growth.db", source_directory / "growth.db")
        sqlite_snapshot(insights, source_directory / "insights.db")
        if registry.read_bytes() != data:
            raise ValueError("legacy_registry_changed_during_snapshot")
        manifest = {}
        for path in source_directory.iterdir():
            manifest[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            path.chmod(0o400)
        (directory / "manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n")
        (directory / "manifest.json").chmod(0o400)
        directory.rename(target)
    print('{"result":"PASS","legacy_snapshot":"created","checksums":4}')
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy", type=Path)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--insights", type=Path)
    args = parser.parse_args()
    try:
        return 0 if snapshot(args.legacy, args.evidence, check=args.check, insights=args.insights) else 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError, sqlite3.Error):
        print('{"result":"BLOCKED","reason":"legacy_snapshot_or_registry_invalid"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
