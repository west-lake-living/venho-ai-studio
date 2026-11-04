from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from growth_engine.application.errors import Conflict
from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.application.dto import CandidateInput
from growth_engine.domain.content.candidate import CandidateState, ResearchCandidate
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.kernel.hashing import canonical_json_bytes, sha256_hex


@dataclass(frozen=True)
class CandidateIngestCommand:
    project_id: str
    candidate: CandidateInput
    actor: str = "research-ingest"
    correlation_id: str = "research-ingest"


@dataclass(frozen=True)
class CandidateIngestResult:
    candidate: ResearchCandidate
    created: bool


class CandidateIngestStore(Protocol):
    def upsert_candidate(
        self,
        candidate: ResearchCandidate,
        *,
        payload_json: str,
        created_at_ms: int,
        actor: str,
        correlation_id: str,
    ) -> tuple[ResearchCandidate, bool]:
        """Atomically insert by the natural key or return the exact replay."""


class IngestCandidate:
    """Persist an untrusted research payload as data; it cannot grant approval."""

    def __init__(self, store: CandidateIngestStore, clock: Clock, ids: IdGenerator) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids

    def execute(self, command: CandidateIngestCommand) -> CandidateIngestResult:
        candidate_input = command.candidate
        if not command.project_id.strip() or not command.actor.strip() or not command.correlation_id.strip():
            raise ValueError("project_id, actor and correlation_id are required")
        try:
            payload_json = canonical_json_bytes(dict(candidate_input.payload)).decode("utf-8")
        except (TypeError, ValueError) as error:
            raise DomainError(ErrorCode.VALIDATION, "Research payload không phải JSON hợp lệ.") from error
        source_hash = sha256_hex(payload_json.encode("utf-8"))
        if candidate_input.source_hash and candidate_input.source_hash != source_hash:
            raise DomainError(ErrorCode.VALIDATION, "Hash của research payload không khớp.")

        proposed = ResearchCandidate(
            id=self._ids.new_id(),
            project_id=command.project_id,
            source=candidate_input.source,
            external_key=candidate_input.external_key,
            source_revision=candidate_input.source_revision,
            event_key=candidate_input.event_key,
            topic_key=candidate_input.topic_key,
            event_start_at_ms=candidate_input.event_start_at_ms,
            event_end_at_ms=candidate_input.event_end_at_ms,
            expires_at_ms=candidate_input.expires_at_ms,
            source_hash=source_hash,
            state=CandidateState.NEW,
        )
        created_at_ms = self._clock.now_ms()
        stored, created = self._store.upsert_candidate(
            proposed,
            payload_json=payload_json,
            created_at_ms=created_at_ms,
            actor=command.actor,
            correlation_id=command.correlation_id,
        )
        if (
            stored.project_id,
            stored.source,
            stored.external_key,
            stored.source_revision,
        ) != (
            proposed.project_id,
            proposed.source,
            proposed.external_key,
            proposed.source_revision,
        ):
            raise RuntimeError("candidate upsert returned a different natural key")
        if stored.source_hash != source_hash:
            raise Conflict("Nguồn thay đổi nhưng source_revision không đổi.")
        return CandidateIngestResult(stored, created)
