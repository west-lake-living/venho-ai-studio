from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from growth_engine.domain.content.candidate import CandidateState, ResearchCandidate
from growth_engine.domain.analytics.metric import MetricObservation


class ChannelRepo(Protocol): ...
class SlotRepo(Protocol): ...
class PackageRepo(Protocol): ...
class MediaRepo(Protocol): ...
class QcRepo(Protocol):
    def find_matching(
        self,
        variant_id: str,
        caption_hash: str,
        fact_snapshot_hash: str,
        ruleset_hash: str,
    ) -> object | None: ...
class DeliveryRepo(Protocol): ...
class CommandRepo(Protocol):
    def close_open_for_delivery(self, delivery_id: str, at_ms: int) -> int: ...
class ExecutionRepo(Protocol): ...
class ReceiptRepo(Protocol): ...
class VerificationRepo(Protocol): ...
class JobRepo(Protocol):
    def save(self, job: object) -> None: ...

    def claim_with_lease(
        self,
        where: dict[str, object],
        *,
        owner: str,
        lease_ms: int,
        now_ms: int,
    ) -> tuple[object, str] | None: ...

    def complete(
        self,
        job_id: str,
        lease_token: str,
        *,
        updated_at_ms: int,
        state: str = "SUCCEEDED",
        last_error: str | None = None,
    ) -> bool: ...

    def defer(
        self,
        job_id: str,
        lease_token: str,
        *,
        run_at_ms: int,
        updated_at_ms: int,
        last_error: str,
    ) -> bool: ...
class AuditRepo(Protocol): ...
class IncidentRepo(Protocol): ...
class ControlsRepo(Protocol): ...
class IdempotencyRepo(Protocol): ...
class BudgetRepo(Protocol): ...
class CandidateRepo(Protocol):
    def get(self, candidate_id: str) -> ResearchCandidate | None: ...

    def upsert_candidate(
        self,
        candidate: ResearchCandidate,
        *,
        payload_json: str,
        created_at_ms: int,
        actor: str,
        correlation_id: str,
    ) -> tuple[ResearchCandidate, bool]: ...

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
    ) -> ResearchCandidate: ...

    def expire_due_candidates(
        self,
        now_ms: int,
        *,
        actor: str,
        correlation_id: str,
    ) -> tuple[str, ...]: ...
class MetricRepo(Protocol):
    def claim_collection(
        self, *, job_id: str, business_key: str, now_ms: int, lease_ms: int
    ) -> tuple[str, str] | None: ...

    def append(self, observations: Sequence[MetricObservation]) -> int: ...

    def load_weekly_samples(
        self, *, start_ms: int, until_ms: int, checkpoint: str
    ) -> list[dict[str, object]]: ...

    def complete_collection(
        self,
        job_id: str,
        lease_token: str,
        *,
        now_ms: int,
        failed: bool,
        retry_delay_ms: int,
    ) -> bool: ...
class LegacyImportRepo(Protocol): ...
