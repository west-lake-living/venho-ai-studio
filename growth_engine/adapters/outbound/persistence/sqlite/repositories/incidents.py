from __future__ import annotations

from growth_engine.domain.ops.incident import Incident, IncidentSeverity, IncidentState

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
        return None if row is None else _incident_from_row(row)

    def get_open_by_fingerprint(self, fingerprint: str) -> Incident | None:
        row = self.connection.execute(
            """SELECT id, type, fingerprint, severity, state, first_seen_at, last_seen_at,
                      occurrence_count, details_json
               FROM incidents WHERE fingerprint=? AND state='OPEN'""",
            (fingerprint,),
        ).fetchone()
        return None if row is None else _incident_from_row(row)

    def open_or_touch(self, incident: Incident, *, details_json: str = "{}") -> Incident:
        if not self.connection.in_transaction:
            raise RuntimeError("open_or_touch requires an active transaction")
        details = parse_json(details_json)
        if not isinstance(details, dict):
            raise ValueError("incident details_json must contain an object")
        details.setdefault("ref", incident.ref)
        details.setdefault("channel_id", incident.channel_id)
        row = self.connection.execute(
            """INSERT INTO incidents
               (id, fingerprint, type, severity, state, first_seen_at, last_seen_at,
                occurrence_count, details_json)
               VALUES (?, ?, ?, ?, 'OPEN', ?, ?, 1, ?)
               ON CONFLICT(fingerprint) WHERE state='OPEN'
               DO UPDATE SET last_seen_at=excluded.last_seen_at,
                             occurrence_count=incidents.occurrence_count+1,
                             severity=excluded.severity,
                             details_json=excluded.details_json
               RETURNING id""",
            (
                incident.id,
                incident.fingerprint,
                incident.type,
                incident.severity.value,
                incident.first_seen_at_ms,
                incident.last_seen_at_ms,
                canonical_json(details),
            ),
        ).fetchone()
        saved = self.get(str(row["id"]))
        if saved is None:
            raise RuntimeError("incident upsert did not return a stored row")
        return saved

    def resolve(
        self,
        incident_id: str,
        *,
        actor: str,
        reason: str,
        now_ms: int,
    ) -> bool:
        if not actor.strip() or not reason.strip():
            raise ValueError("incident resolution requires actor and reason")
        row = self.connection.execute(
            "SELECT details_json FROM incidents WHERE id=? AND state='OPEN'", (incident_id,)
        ).fetchone()
        if row is None:
            return False
        details = parse_json(row["details_json"])
        details["resolution_reason"] = reason
        cursor = self.connection.execute(
            """UPDATE incidents SET state='RESOLVED', resolved_at=?, resolved_by=?, details_json=?
               WHERE id=? AND state='OPEN'""",
            (now_ms, actor, canonical_json(details), incident_id),
        )
        return cursor.rowcount == 1


def _incident_from_row(row) -> Incident:
    details = parse_json(row["details_json"])
    return Incident(
        id=row["id"],
        type=row["type"],
        fingerprint=row["fingerprint"],
        channel_id=details.get("channel_id"),
        ref=details["ref"],
        severity=IncidentSeverity(row["severity"]),
        state=IncidentState(row["state"]),
        first_seen_at_ms=row["first_seen_at"],
        last_seen_at_ms=row["last_seen_at"],
        occurrence_count=row["occurrence_count"],
    )
