from __future__ import annotations

from growth_engine.application.errors import Conflict
from growth_engine.domain.content.candidate import CandidateState, ResearchCandidate
from growth_engine.domain.content.package import ContentPackage

from ._base import SqliteRepository, canonical_json, canonical_json_text, parse_json


class PackageRepository(SqliteRepository):
    def save(self, package: ContentPackage) -> None:
        self.connection.execute(
            """INSERT INTO content_packages
               (id, slot_id, topic_key, pillar, lane, candidate_id, source_snapshot_json,
                fact_snapshot_json, fact_snapshot_hash, generation_version, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                package.id,
                package.slot_id,
                package.topic_key,
                package.pillar,
                package.lane,
                package.candidate_id,
                canonical_json_text(package.source_snapshot_json),
                canonical_json_text(package.fact_snapshot_json),
                package.fact_snapshot_hash,
                package.generation_version,
                package.created_at_ms,
            ),
        )

    def get(self, package_id: str) -> ContentPackage | None:
        row = self.connection.execute(
            """SELECT id, slot_id, topic_key, pillar, lane, candidate_id, source_snapshot_json,
                      fact_snapshot_json, fact_snapshot_hash, generation_version, created_at
               FROM content_packages WHERE id=?""",
            (package_id,),
        ).fetchone()
        if row is None:
            return None
        return ContentPackage(
            id=row["id"],
            slot_id=row["slot_id"],
            topic_key=row["topic_key"],
            pillar=row["pillar"],
            lane=row["lane"],
            source_snapshot_json=row["source_snapshot_json"],
            fact_snapshot_json=row["fact_snapshot_json"],
            fact_snapshot_hash=row["fact_snapshot_hash"],
            generation_version=row["generation_version"],
            created_at_ms=row["created_at"],
            candidate_id=row["candidate_id"],
        )


class CandidateRepository(SqliteRepository):
    def save(
        self,
        candidate: ResearchCandidate,
        *,
        created_at_ms: int,
        payload_json: str | None = None,
    ) -> None:
        payload = (
            canonical_json(
                {
                    "id": candidate.id,
                    "project_id": candidate.project_id,
                    "source": candidate.source,
                    "external_key": candidate.external_key,
                    "source_revision": candidate.source_revision,
                    "event_key": candidate.event_key,
                    "topic_key": candidate.topic_key,
                    "event_start_at_ms": candidate.event_start_at_ms,
                    "event_end_at_ms": candidate.event_end_at_ms,
                    "expires_at_ms": candidate.expires_at_ms,
                    "source_hash": candidate.source_hash,
                    "state": candidate.state.value,
                }
            )
            if payload_json is None
            else canonical_json(parse_json(payload_json))
        )
        self.connection.execute(
            """INSERT INTO research_candidates
               (id, project_id, source, external_key, source_revision, event_key, topic_key,
                event_start_at, event_end_at, expires_at, payload_json, source_hash, state,
                created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate.id,
                candidate.project_id,
                candidate.source,
                candidate.external_key,
                candidate.source_revision,
                candidate.event_key,
                candidate.topic_key,
                candidate.event_start_at_ms,
                candidate.event_end_at_ms,
                candidate.expires_at_ms,
                payload,
                candidate.source_hash,
                candidate.state.value,
                created_at_ms,
            ),
        )

    def get(self, candidate_id: str) -> ResearchCandidate | None:
        row = self.connection.execute(
            """SELECT id, project_id, source, external_key, source_revision, event_key,
                      topic_key, event_start_at, event_end_at, expires_at, source_hash, state
               FROM research_candidates WHERE id=?""",
            (candidate_id,),
        ).fetchone()
        if row is None:
            return None
        return _candidate(row)

    def upsert_candidate(
        self,
        candidate: ResearchCandidate,
        *,
        payload_json: str,
        created_at_ms: int,
        actor: str,
        correlation_id: str,
    ) -> tuple[ResearchCandidate, bool]:
        existing = self.connection.execute(
            """SELECT id, project_id, source, external_key, source_revision, event_key,
                      topic_key, event_start_at, event_end_at, expires_at, source_hash, state
               FROM research_candidates
               WHERE project_id=? AND source=? AND external_key=? AND source_revision=?""",
            (candidate.project_id, candidate.source, candidate.external_key, candidate.source_revision),
        ).fetchone()
        if existing is not None:
            return _candidate(existing), False
        self.save(candidate, created_at_ms=created_at_ms, payload_json=payload_json)
        self.connection.execute(
            """INSERT INTO audit_events
               (id, aggregate_type, aggregate_id, actor, action, before_hash, after_hash,
                details_json, correlation_id, created_at)
               VALUES (?, 'research_candidate', ?, ?, 'candidate.ingested', NULL, ?, ?, ?, ?)""",
            (
                f"candidate-ingest:{candidate.id}",
                candidate.id,
                actor,
                candidate.source_hash,
                canonical_json(
                    {
                        "source": candidate.source,
                        "external_key": candidate.external_key,
                        "source_revision": candidate.source_revision,
                    }
                ),
                correlation_id,
                created_at_ms,
            ),
        )
        return candidate, True

    def apply_candidate_decision(
        self,
        candidate_id: str,
        *,
        expected_source_hash: str,
        decision_id: str,
        decision: object,
        next_state: CandidateState,
        actor: str,
        reason: str,
        created_at_ms: int,
        correlation_id: str,
    ) -> ResearchCandidate:
        row = self.connection.execute(
            """SELECT id, project_id, source, external_key, source_revision, event_key,
                      topic_key, event_start_at, event_end_at, expires_at, source_hash, state,
                      row_version
               FROM research_candidates WHERE id=?""",
            (candidate_id,),
        ).fetchone()
        if row is None:
            raise Conflict("Research candidate không còn tồn tại.")
        if row["source_hash"] != expected_source_hash or row["state"] != CandidateState.NEW.value:
            raise Conflict("Research candidate đã đổi hoặc đã được quyết định.")
        changed = self.connection.execute(
            """UPDATE research_candidates SET state=?, row_version=row_version+1
               WHERE id=? AND source_hash=? AND state='NEW' AND row_version=?""",
            (next_state.value, candidate_id, expected_source_hash, row["row_version"]),
        ).rowcount
        if changed != 1:
            raise Conflict("Research candidate đã đổi hoặc đã được quyết định.")
        decision_value = getattr(decision, "value", decision)
        if not isinstance(decision_value, str):
            raise ValueError("candidate decision must be text")
        self.connection.execute(
            """INSERT INTO candidate_decisions
               (id, candidate_id, source_hash, decision, actor_id, reason, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (decision_id, candidate_id, expected_source_hash, decision_value, actor, reason, created_at_ms),
        )
        self.connection.execute(
            """INSERT INTO audit_events
               (id, aggregate_type, aggregate_id, actor, action, before_hash, after_hash,
                details_json, correlation_id, created_at)
               VALUES (?, 'research_candidate', ?, ?, 'candidate.decided', ?, ?, ?, ?, ?)""",
            (
                f"candidate-decision:{decision_id}",
                candidate_id,
                actor,
                expected_source_hash,
                expected_source_hash,
                canonical_json({"decision": decision_value, "state": next_state.value, "reason": reason}),
                correlation_id,
                created_at_ms,
            ),
        )
        updated = self.get(candidate_id)
        if updated is None:
            raise RuntimeError("candidate disappeared within its write transaction")
        return updated

    def expire_due_candidates(
        self,
        now_ms: int,
        *,
        actor: str,
        correlation_id: str,
    ) -> tuple[str, ...]:
        rows = self.connection.execute(
            """SELECT id, source_hash, row_version FROM research_candidates
               WHERE state IN ('NEW','APPROVED')
                 AND (expires_at<=? OR (event_end_at IS NOT NULL AND event_end_at<=?))
               ORDER BY id""",
            (now_ms, now_ms),
        ).fetchall()
        expired: list[str] = []
        for row in rows:
            changed = self.connection.execute(
                """UPDATE research_candidates SET state='EXPIRED', row_version=row_version+1
                   WHERE id=? AND row_version=? AND state IN ('NEW','APPROVED')""",
                (row["id"], row["row_version"]),
            ).rowcount
            if changed != 1:
                continue
            event_id = f"candidate-expire:{row['id']}:{now_ms}"
            self.connection.execute(
                """INSERT INTO audit_events
                   (id, aggregate_type, aggregate_id, actor, action, before_hash, after_hash,
                    details_json, correlation_id, created_at)
                   VALUES (?, 'research_candidate', ?, ?, 'candidate.expired', ?, ?, ?, ?, ?)""",
                (
                    event_id,
                    row["id"],
                    actor,
                    row["source_hash"],
                    row["source_hash"],
                    canonical_json({"expired_at_ms": now_ms}),
                    correlation_id,
                    now_ms,
                ),
            )
            expired.append(row["id"])
        return tuple(expired)


def _candidate(row: object) -> ResearchCandidate:
    return ResearchCandidate(
        id=row["id"],
        project_id=row["project_id"],
        source=row["source"],
        external_key=row["external_key"],
        source_revision=row["source_revision"],
        event_key=row["event_key"],
        topic_key=row["topic_key"],
        event_start_at_ms=row["event_start_at"],
        event_end_at_ms=row["event_end_at"],
        expires_at_ms=row["expires_at"],
        source_hash=row["source_hash"],
        state=CandidateState(row["state"]),
    )
