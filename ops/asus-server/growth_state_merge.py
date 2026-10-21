#!/usr/bin/env python3
"""Merge this runner's Growth publication state onto a newer origin/main.

Used by growth-dispatch.sh when its state commit cannot fast-forward because
someone else (weekly cycle on GitHub, Dashboard approve/reject) pushed first.
Never re-dispatches anything: it only reconciles files.

  registry  <ours.json> <target.json>   rows by publication_id, newest updated_at wins
  db        <ours.db>   <target.db>     publishing_slots by slot_id (newest updated_at),
                                        jobs / budget rows missing from target are added
  trends    <ours.json> <target.json>   trend candidates: target (Dashboard approvals)
                                        wins per id; ours adds new ids + new sources
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime


def _ts(value: object) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return datetime.min
    return parsed.replace(tzinfo=None) if parsed.tzinfo is None else parsed.astimezone().replace(tzinfo=None)


def merge_registry(ours_path: str, target_path: str) -> int:
    with open(ours_path, encoding="utf-8") as fh:
        ours = json.load(fh)
    with open(target_path, encoding="utf-8") as fh:
        target = json.load(fh)
    rows = target.setdefault("publications", [])
    index = {row.get("publication_id"): i for i, row in enumerate(rows)}
    changed = 0
    for row in ours.get("publications", []):
        pid = row.get("publication_id")
        if pid not in index:
            rows.append(row)
            changed += 1
        elif _ts(row.get("updated_at")) > _ts(rows[index[pid]].get("updated_at")):
            rows[index[pid]] = row
            changed += 1
    with open(target_path, "w", encoding="utf-8") as fh:
        json.dump(target, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return changed


def merge_db(ours_path: str, target_path: str) -> int:
    db = sqlite3.connect(target_path)
    db.execute("ATTACH DATABASE ? AS ours", (ours_path,))
    before = db.total_changes
    db.execute(
        """
        INSERT OR REPLACE INTO main.publishing_slots
        SELECT o.* FROM ours.publishing_slots o
        LEFT JOIN main.publishing_slots m ON m.slot_id = o.slot_id
        WHERE m.slot_id IS NULL OR o.updated_at > m.updated_at
        """
    )
    db.execute("INSERT OR IGNORE INTO main.jobs SELECT * FROM ours.jobs")
    for table, cols in (
        ("budget_events", "reservation_id, action, amount_minor, currency, created_at"),
        ("budget_overrides", "reservation_id, amount_minor, currency, reason, approved_by, created_at"),
    ):
        db.execute(
            f"""
            INSERT INTO main.{table} ({cols})
            SELECT {cols} FROM ours.{table} o
            WHERE NOT EXISTS (
              SELECT 1 FROM main.{table} m
              WHERE m.reservation_id = o.reservation_id AND m.created_at = o.created_at
                AND m.amount_minor = o.amount_minor
            )
            """
        )
    db.commit()
    changed = db.total_changes - before
    db.execute("DETACH DATABASE ours")
    db.close()
    return changed


def merge_trends(ours_path: str, target_path: str) -> int:
    """The runner only ever inserts candidates and appends sources; approve/
    reject happen on the Dashboard. So the target row always keeps its
    decision fields and only gains source refs it lacks."""
    with open(ours_path, encoding="utf-8") as fh:
        ours = json.load(fh)
    with open(target_path, encoding="utf-8") as fh:
        target = json.load(fh)
    index = {row.get("id"): row for row in target}
    changed = 0
    for row in ours:
        existing = index.get(row.get("id"))
        if existing is None:
            target.append(row)
            index[row.get("id")] = row
            changed += 1
            continue
        known = {ref.get("title") for ref in existing.get("sources", [])}
        extra = [ref for ref in row.get("sources", []) if ref.get("title") not in known]
        if extra:
            existing.setdefault("sources", []).extend(extra)
            existing["source_count"] = len(existing["sources"])
            changed += 1
    with open(target_path, "w", encoding="utf-8") as fh:
        json.dump(target, fh, ensure_ascii=False, indent=2)
    return changed


if __name__ == "__main__":
    kind, ours, target = sys.argv[1:4]
    count = {"registry": merge_registry, "db": merge_db, "trends": merge_trends}[kind](ours, target)
    print(f"{kind}: merged {count} change(s)")
