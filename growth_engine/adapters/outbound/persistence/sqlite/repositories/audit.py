from __future__ import annotations

from ._base import SqliteRepository, canonical_json, parse_json


class AuditRepository(SqliteRepository):
    def append(
        self,
        *,
        event_id: str,
        aggregate_type: str,
        aggregate_id: str,
        actor: str,
        action: str,
        before_hash: str | None,
        after_hash: str | None,
        details_json: str,
        correlation_id: str,
        created_at_ms: int,
    ) -> None:
        canonical_details = canonical_json(parse_json(details_json))
        self.connection.execute(
            """INSERT INTO audit_events
               (id, aggregate_type, aggregate_id, actor, action, before_hash, after_hash,
                details_json, correlation_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event_id,
                aggregate_type,
                aggregate_id,
                actor,
                action,
                before_hash,
                after_hash,
                canonical_details,
                correlation_id,
                created_at_ms,
            ),
        )
