from __future__ import annotations

from datetime import date

from growth_engine.domain.scheduling.slot import Slot, SlotTarget

from ._base import SqliteRepository


class SlotRepository(SqliteRepository):
    def save_slot(
        self,
        slot: Slot,
        *,
        created_at_ms: int,
        cancel_reason: str | None = None,
    ) -> None:
        self.connection.execute(
            """INSERT INTO slots
               (id, project_id, local_date, local_time, timezone, lane, cadence_version,
                scheduled_at, deadline_at, cancelled_at, cancel_reason, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                slot.id,
                slot.project_id,
                slot.local_date.isoformat(),
                slot.local_time,
                slot.timezone,
                slot.lane,
                slot.cadence_version,
                slot.scheduled_at_ms,
                slot.deadline_at_ms,
                slot.cancelled_at_ms,
                cancel_reason,
                created_at_ms,
            ),
        )

    def get_slot(self, slot_id: str) -> Slot | None:
        row = self.connection.execute(
            """SELECT id, project_id, local_date, local_time, timezone, lane, cadence_version,
                      scheduled_at, deadline_at, cancelled_at
               FROM slots WHERE id=?""",
            (slot_id,),
        ).fetchone()
        if row is None:
            return None
        return Slot(
            id=row["id"],
            project_id=row["project_id"],
            local_date=date.fromisoformat(row["local_date"]),
            local_time=row["local_time"],
            timezone=row["timezone"],
            lane=row["lane"],
            cadence_version=row["cadence_version"],
            scheduled_at_ms=row["scheduled_at"],
            deadline_at_ms=row["deadline_at"],
            cancelled_at_ms=row["cancelled_at"],
        )

    def save_target(self, target: SlotTarget) -> None:
        self.connection.execute(
            "INSERT INTO slot_targets(id, slot_id, channel_id, required) VALUES (?, ?, ?, ?)",
            (target.id, target.slot_id, target.channel_id, int(target.required)),
        )

    def get_target(self, target_id: str) -> SlotTarget | None:
        row = self.connection.execute(
            "SELECT id, slot_id, channel_id, required FROM slot_targets WHERE id=?",
            (target_id,),
        ).fetchone()
        if row is None:
            return None
        return SlotTarget(
            id=row["id"],
            slot_id=row["slot_id"],
            channel_id=row["channel_id"],
            required=bool(row["required"]),
        )
