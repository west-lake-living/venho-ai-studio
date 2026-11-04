from __future__ import annotations

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
