from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from growth_orchestrator.domain.publishing_slot import PublishingSlot


class SlotStore:
    """SQLite persistence for PublishingSlot rows (plan v3.1 §4.4).

    Adapted for the ephemeral GitHub Actions cron model (see
    growth-daily-cycle.yml) rather than the plan's original Mac-Mini-24/7
    worker daemon design: there is no background process polling this
    table, so every method here is called synchronously from within a
    single `weekly-cycle` run. Its job is visibility and idempotency --
    "which cadence slot got filled, which got missed, which is stuck
    mid-approval" -- not job scheduling.
    """

    def __init__(self, db_path: Path = Path("data/projects/venho_hotel/growth/growth.db")) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path)
        db.execute("PRAGMA busy_timeout = 5000")
        return db

    def _init(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS publishing_slots (
                  slot_id TEXT PRIMARY KEY,
                  slot_date TEXT NOT NULL,
                  slot_type TEXT NOT NULL,
                  lane TEXT NOT NULL,
                  status TEXT NOT NULL,
                  content_package_id TEXT,
                  filled_from TEXT,
                  updated_at TEXT NOT NULL
                )
                """
            )

    def ensure_slots(self, slots: Iterable[PublishingSlot]) -> int:
        """Idempotently insert OPEN slots (INSERT OR IGNORE on slot_id).

        Takes already-built PublishingSlot objects (from
        growth_orchestrator.application.manage_slots.generate_slots) rather
        than a cadence policy, so callers control the horizon/start_date and
        this stays a pure persistence layer.
        """
        now = datetime.now(timezone.utc).isoformat()
        inserted = 0
        with self._connect() as db:
            for slot in slots:
                cursor = db.execute(
                    """
                    INSERT OR IGNORE INTO publishing_slots
                      (slot_id, slot_date, slot_type, lane, status, content_package_id, filled_from, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (slot.slot_id, slot.slot_date, slot.slot_type, slot.lane, slot.status, slot.content_package_id, slot.filled_from, now),
                )
                inserted += cursor.rowcount
        return inserted

    def get(self, slot_id: str) -> Optional[PublishingSlot]:
        with self._connect() as db:
            row = db.execute(
                "SELECT slot_id, slot_date, slot_type, lane, status, content_package_id, filled_from FROM publishing_slots WHERE slot_id=?",
                (slot_id,),
            ).fetchone()
        if not row:
            return None
        return PublishingSlot(
            slot_id=row[0], slot_date=row[1], slot_type=row[2], lane=row[3], status=row[4],
            content_package_id=row[5], filled_from=row[6],
        )

    def transition(self, slot_id: str, target: str, **updates: Any) -> PublishingSlot:
        """Validate + apply a PublishingSlot transition, persisted atomically.

        Raises ValueError (via PublishingSlot.transition) if the target
        isn't reachable from the slot's current on-disk status, and KeyError
        if the slot_id doesn't exist -- callers in daily_cycle/
        approve_and_dispatch wrap this in try/except since slot bookkeeping
        must never block the real content generation or dispatch it's
        tracking (see call sites for the "best-effort" comment).
        """
        current = self.get(slot_id)
        if current is None:
            raise KeyError(f"Unknown slot_id: {slot_id}")
        updated = current.transition(target, **updates)
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute(
                """
                UPDATE publishing_slots
                SET status=?, content_package_id=?, filled_from=?, updated_at=?
                WHERE slot_id=?
                """,
                (updated.status, updated.content_package_id, updated.filled_from, now, slot_id),
            )
        return updated

    def list_all(self, *, status: Optional[str] = None) -> list[PublishingSlot]:
        """All slots ever created, optionally filtered by status.

        Added for Phase 8's real scorecard (`controlled_rollout.collect_real_scorecard_metrics`):
        `unplanned_empty_days` (Part 13.4/DoD #9) needs a real count of
        `MISSED` slots across the whole pilot window, not just the current
        week `list_for_week` was built for.
        """
        query = "SELECT slot_id, slot_date, slot_type, lane, status, content_package_id, filled_from FROM publishing_slots"
        params: tuple[Any, ...] = ()
        if status is not None:
            query += " WHERE status=?"
            params = (status,)
        query += " ORDER BY slot_date"
        with self._connect() as db:
            rows = db.execute(query, params).fetchall()
        return [
            PublishingSlot(slot_id=r[0], slot_date=r[1], slot_type=r[2], lane=r[3], status=r[4], content_package_id=r[5], filled_from=r[6])
            for r in rows
        ]

    def list_for_week(self, slot_dates: Iterable[str]) -> list[PublishingSlot]:
        dates = list(slot_dates)
        if not dates:
            return []
        placeholders = ",".join("?" for _ in dates)
        with self._connect() as db:
            rows = db.execute(
                f"SELECT slot_id, slot_date, slot_type, lane, status, content_package_id, filled_from "
                f"FROM publishing_slots WHERE slot_date IN ({placeholders}) ORDER BY slot_date",
                dates,
            ).fetchall()
        return [
            PublishingSlot(slot_id=r[0], slot_date=r[1], slot_type=r[2], lane=r[3], status=r[4], content_package_id=r[5], filled_from=r[6])
            for r in rows
        ]
