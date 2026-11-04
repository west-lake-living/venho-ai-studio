from __future__ import annotations

from growth_engine.domain.ops.incident import Incident, IncidentSeverity, IncidentState
from growth_engine.domain.publishing.runtime_mode import PublishMode, RuntimeControls

from ._base import SqliteRepository, canonical_json, parse_json


class IncidentRepository(SqliteRepository):
    def save(self, incident: Incident, *, details_json: str = "{}") -> None:
        details = parse_json(details_json)
        if not isinstance(details, dict):
            raise ValueError("incident details_json must contain an object")
        details.setdefault("ref", incident.ref)
        details.setdefault("channel_id", incident.channel_id)
        self.connection.execute(
            """INSERT INTO incidents
               (id, fingerprint, type, severity, state, first_seen_at, last_seen_at,
                occurrence_count, details_json, resolved_at, resolved_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                incident.id,
                incident.fingerprint,
                incident.type,
                incident.severity.value,
                incident.state.value,
                incident.first_seen_at_ms,
                incident.last_seen_at_ms,
                incident.occurrence_count,
                canonical_json(details),
                incident.last_seen_at_ms if incident.state is IncidentState.RESOLVED else None,
                None,
            ),
        )

    def get(self, incident_id: str) -> Incident | None:
        row = self.connection.execute(
            """SELECT id, type, fingerprint, severity, state, first_seen_at, last_seen_at,
                      occurrence_count, details_json
               FROM incidents WHERE id=?""",
            (incident_id,),
        ).fetchone()
        if row is None:
            return None
        details = parse_json(row["details_json"])
        return Incident(
            id=row["id"],
            type=row["type"],
            fingerprint=row["fingerprint"],
            channel_id=details["channel_id"],
            ref=details["ref"],
            severity=IncidentSeverity(row["severity"]),
            state=IncidentState(row["state"]),
            first_seen_at_ms=row["first_seen_at"],
            last_seen_at_ms=row["last_seen_at"],
            occurrence_count=row["occurrence_count"],
        )
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
        row = self.connection.execute(
            """SELECT publish_mode, dispatch_epoch, global_pause
               FROM runtime_controls WHERE environment=?""",
            (environment,),
        ).fetchone()
        if row is None:
            return None
        return RuntimeControls(
            mode=PublishMode(row["publish_mode"]),
            dispatch_epoch=row["dispatch_epoch"],
            global_pause=bool(row["global_pause"]),
        )
