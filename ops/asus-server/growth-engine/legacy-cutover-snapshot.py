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
from datetime import date
from pathlib import Path


SAFE_TERMINAL = {"CANCELLED", "REJECTED", "STALE_APPROVAL", "FAILED", "SUPERSEDED", "DISABLED"}
PROJECT = Path("data/projects/venho_hotel")


def inventory(registry: dict, first: str) -> tuple[dict[str, int], list[dict[str, str]]]:
    rows = registry["publications"]
    if not isinstance(rows, list):
        raise ValueError("publication_registry_invalid")
    outstanding: Counter[str] = Counter()
    frozen: dict[str, dict[str, str]] = {}
    for row in rows:
        match = re.match(r"^slot-(\d{4}-\d{2}-\d{2})(?:-|$)", row.get("slot_id") or "")
        status = row.get("status")
        if status == "DISPATCHING":
            outstanding["dispatching"] += 1
        elif match and match[1] >= first and status == "PENDING_APPROVAL":
            publication_id, platform = row["publication_id"], row["platform"]
            if not all(isinstance(value, str) and value for value in (publication_id, platform)):
                raise ValueError("invalid_frozen_pending_row")
            if publication_id in frozen:
                raise ValueError("duplicate_frozen_pending_row")
            frozen[publication_id] = {
                "publication_id": publication_id, "slot_date": match[1], "platform": platform, "status": status,
            }
        elif match and match[1] >= first and status not in SAFE_TERMINAL:
            reason = {
                "APPROVED_SCHEDULED": "approved_scheduled",
                "GATEWAY_ACCEPTED": "gateway_accepted",
                "PUBLISHED": "already_published",
                "GATEWAY_ERROR": "gateway_error",
            }.get(status, "other_unresolved")
            outstanding[reason] += 1
        elif not match and status not in SAFE_TERMINAL | {"PUBLISHED"}:
            outstanding["undated_unresolved"] += 1
    return dict(outstanding), [frozen[key] for key in sorted(frozen)]


def sqlite_snapshot(source_path: Path, target: Path) -> None:
    with closing(sqlite3.connect(source_path.resolve().as_uri() + "?mode=ro", uri=True)) as source:
        with closing(sqlite3.connect(target)) as destination:
            source.backup(destination)
            if destination.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ValueError("legacy_sqlite_snapshot_invalid")


INSIGHTS_ABSENT = {"status": "ABSENT", "reason": "t0_06_never_deployed"}


def insights_present(path: Path | None) -> bool:
    if path is None:
        return False
    try:
        path.stat()
    except FileNotFoundError:
        if path.is_symlink():
            raise ValueError("legacy_insights_invalid")
        return False
    if not path.is_file():
        raise ValueError("legacy_insights_invalid")
    return True


def snapshot(legacy: Path, evidence: Path, *, check: bool, insights: Path | None, first_slot: str,
             record_frozen: bool = False, require_frozen: bool = False) -> bool:
    registry = legacy / PROJECT / "publishing/publication_registry.json"
    data = registry.read_bytes()
    pending, frozen = inventory(json.loads(data), first_slot)
    frozen_path = evidence / "legacy-frozen-pending.json"
    if frozen_path.is_file():
        if json.loads(frozen_path.read_text()) != frozen:
            raise ValueError("legacy_frozen_pending_changed")
    elif require_frozen:
        raise ValueError("legacy_frozen_pending_missing")

    if pending:
        print(json.dumps({"result": "BLOCKED", "legacy_blockers": pending}, sort_keys=True))
        return False
    print(f"LEGACY_FROZEN_PENDING={len(frozen)}")
    if record_frozen:
        if not frozen_path.is_file():
            with tempfile.TemporaryDirectory(dir=evidence, prefix=".frozen-") as directory:
                staged = Path(directory) / frozen_path.name
                staged.write_text(json.dumps(frozen, indent=2) + "\n")
                staged.chmod(0o600)
                frozen_path.hardlink_to(staged)
        print('{"result":"PASS","legacy_frozen_pending":"recorded"}')
        return True
    present = insights_present(insights)
    target = evidence / "legacy-snapshot"
    if target.exists():
        manifest = json.loads((target / "manifest.json").read_text())
        if manifest["publication_registry.json"] != hashlib.sha256(data).hexdigest():
            raise ValueError("legacy_registry_changed_after_snapshot")
        recorded_absent = manifest["insights.db"] == INSIGHTS_ABSENT
        if present == recorded_absent:
            raise ValueError("legacy_insights_presence_changed_after_snapshot")
        for name in ("publication_registry.json", "slots_snapshot.json", "growth.db", "insights.db"):
            copied = target / "source" / name
            if name == "insights.db" and recorded_absent:
                if copied.exists() or copied.is_symlink():
                    raise ValueError("legacy_snapshot_checksum_mismatch")
                continue
            if hashlib.sha256(copied.read_bytes()).hexdigest() != manifest[name]:
                raise ValueError("legacy_snapshot_checksum_mismatch")
        if recorded_absent:
            print("INSIGHTS=ABSENT (D2 deferred)")
        print('{"result":"PASS","legacy_snapshot":"existing_verified"}')
        return True
    if check:
        print('{"result":"PASS","legacy_blockers":{}}')
        return True
    with tempfile.TemporaryDirectory(dir=evidence, prefix=".legacy-") as temporary:
        directory = Path(temporary) / "snapshot"
        directory.mkdir(mode=0o700)
        source_directory = directory / "source"
        source_directory.mkdir(mode=0o700)
        (source_directory / "publication_registry.json").write_bytes(data)
        shutil.copyfile(legacy / PROJECT / "growth/slots_snapshot.json", source_directory / "slots_snapshot.json")
        sqlite_snapshot(legacy / PROJECT / "growth/growth.db", source_directory / "growth.db")
        if present:
            assert insights is not None
            sqlite_snapshot(insights, source_directory / "insights.db")
        if insights_present(insights) != present:
            raise ValueError("legacy_insights_presence_changed_during_snapshot")
        if registry.read_bytes() != data:
            raise ValueError("legacy_registry_changed_during_snapshot")
        manifest = {}
        for path in source_directory.iterdir():
            manifest[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            path.chmod(0o400)
        checksums = len(manifest)
        if not present:
            manifest["insights.db"] = INSIGHTS_ABSENT
        (directory / "manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n")
        (directory / "manifest.json").chmod(0o400)
        directory.rename(target)
    if not present:
        print("INSIGHTS=ABSENT (D2 deferred)")
    print(json.dumps({"result": "PASS", "legacy_snapshot": "created", "checksums": checksums}))
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy", type=Path)
    parser.add_argument("evidence", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--record-frozen", action="store_true")
    parser.add_argument("--require-frozen", action="store_true")
    parser.add_argument("--insights", type=Path)
    parser.add_argument("--first-slot", required=True, type=date.fromisoformat)
    args = parser.parse_args()
    try:
        return 0 if snapshot(args.legacy, args.evidence, check=args.check, insights=args.insights,
                             first_slot=args.first_slot.isoformat(), record_frozen=args.record_frozen,
                             require_frozen=args.require_frozen) else 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError, sqlite3.Error) as error:
        reason = str(error) if isinstance(error, ValueError) and str(error) in {
            "legacy_frozen_pending_changed", "legacy_frozen_pending_missing",
        } else "legacy_snapshot_or_registry_invalid"
        print(json.dumps({"result": "BLOCKED", "reason": reason}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
