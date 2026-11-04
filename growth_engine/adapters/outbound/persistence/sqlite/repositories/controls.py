from __future__ import annotations

from collections.abc import Mapping

from growth_engine.domain.publishing.runtime_mode import PublishMode, RuntimeControls

from ._base import SqliteRepository


class ControlsRepository(SqliteRepository):
    def save(
        self,
        controls: RuntimeControls,
        *,
        environment: str,
        policy_version: str,
        updated_at_ms: int,
    ) -> None:
        self.connection.execute(
            """INSERT INTO runtime_controls
               (environment, publish_mode, dispatch_epoch, global_pause, policy_version,
                updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                environment,
                controls.mode.value,
                controls.dispatch_epoch,
                int(controls.global_pause),
                policy_version,
                updated_at_ms,
            ),
        )

    def get(self, environment: str) -> RuntimeControls | None:
        snapshot = self.get_with_version(environment)
        return None if snapshot is None else snapshot[0]

    def get_with_version(self, environment: str) -> tuple[RuntimeControls, int] | None:
        row = self.connection.execute(
            """SELECT publish_mode, dispatch_epoch, global_pause, row_version
               FROM runtime_controls WHERE environment=?""",
            (environment,),
        ).fetchone()
        if row is None:
            return None
        return (
            RuntimeControls(
                mode=PublishMode(row["publish_mode"]),
                dispatch_epoch=row["dispatch_epoch"],
                global_pause=bool(row["global_pause"]),
            ),
            row["row_version"],
        )

    def compare_and_set(
        self,
        environment: str,
        expected_row_version: int,
        *,
        fields: Mapping[str, object],
        updated_at_ms: int,
    ) -> bool:
        allowed = {"publish_mode", "dispatch_epoch", "global_pause", "policy_version"}
        if not fields or any(field not in allowed for field in fields):
            raise ValueError("runtime control update fields are not allowed")
        columns = tuple(fields)
        assignments = ", ".join(f"{column}=?" for column in columns)
        values = tuple(_db_value(fields[column]) for column in columns)
        cursor = self.connection.execute(
            f"UPDATE runtime_controls SET {assignments}, updated_at=?, row_version=row_version+1 "
            "WHERE environment=? AND row_version=?",
            (*values, updated_at_ms, environment, expected_row_version),
        )
        return cursor.rowcount == 1

    def set_channel_paused(self, channel_id: str, paused: bool) -> bool:
        if type(paused) is not bool:
            raise ValueError("paused must be boolean")
        cursor = self.connection.execute(
            "UPDATE channels SET paused=? WHERE id=? AND paused!=?",
            (int(paused), channel_id, int(paused)),
        )
        return cursor.rowcount == 1


def _db_value(value: object) -> object:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    if isinstance(value, bool):
        return int(value)
    return value
