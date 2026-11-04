from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.domain.channels.channel import ChannelConfig
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.publishing.execution import Execution, ExecutionState
from growth_engine.domain.publishing.receipt import Receipt, ReceiptOutcome


@dataclass(frozen=True)
class UnknownEvidence:
    kind: str
    actor_id: str
    reason: str
    platform_post_id: str | None = None
    permalink: str | None = None
    make_execution_ref: str | None = None


@dataclass(frozen=True)
class UnknownCandidate:
    delivery: Delivery
    execution: Execution
    channel_id: str
    remote_page_id: str
    revision_id: str
    payload_hash: str
    expected_caption: str
    channel_config: ChannelConfig


class UnknownEvidenceReader(Protocol):
    def read_post(self, **kwargs: object) -> object: ...
    def read_permalink(self, permalink: str, **kwargs: object) -> tuple[str, object]: ...


class ResolveUnknownTransaction(Protocol):
    def get_candidate(self, delivery_id: str) -> UnknownCandidate | None: ...
    def commit_resolution(self, candidate: UnknownCandidate, **values: object) -> bool: ...


class ResolveUnknownStore(Protocol):
    def begin_immediate(self) -> object: ...


@dataclass(frozen=True)
class ResolveUnknownResult:
    outcome: str
    delivery_state: DeliveryState


class ResolveUnknown:
    def __init__(self, store: ResolveUnknownStore, reader: UnknownEvidenceReader, clock: Clock, ids: IdGenerator) -> None:
        self._store = store
        self._reader = reader
        self._clock = clock
        self._ids = ids

    def execute(self, delivery_id: str, evidence: UnknownEvidence) -> ResolveUnknownResult:
        if not evidence.actor_id.strip() or not evidence.reason.strip():
            raise ValueError("actor and reason are required")
        now_ms = self._clock.now_ms()
        with self._store.begin_immediate() as tx:
            candidate = tx.get_candidate(delivery_id)
            if candidate is None or candidate.delivery.state is not DeliveryState.UNKNOWN:
                raise ValueError("only an UNKNOWN delivery can be resolved")
            if candidate.execution.state is not ExecutionState.UNKNOWN:
                raise ValueError("execution is not UNKNOWN")

            if evidence.kind == "POST_FOUND":
                post_id = evidence.platform_post_id
                if not post_id and evidence.permalink:
                    resolve_link = getattr(self._reader, "read_permalink", None)
                    if not callable(resolve_link):
                        raise ValueError("reader cannot verify a permalink; provide the Page post ID")
                    post_id, result = resolve_link(
                        evidence.permalink,
                        channel_config=candidate.channel_config,
                        remote_page_id=candidate.remote_page_id,
                        expected_caption=candidate.expected_caption,
                    )
                elif post_id:
                    result = self._reader.read_post(
                        channel_config=candidate.channel_config,
                        remote_page_id=candidate.remote_page_id,
                        platform_post_id=post_id,
                        expected_caption=candidate.expected_caption,
                    )
                else:
                    raise ValueError("POST_FOUND requires a post ID or permalink")
                if getattr(result, "existence", None) != "EXISTS" or getattr(result, "ownership", None) != "MATCH":
                    raise ValueError("candidate post does not verify on the delivery Page")
                receipt = Receipt(
                    issuer="operator-resolution",
                    event_id=f"resolve:{candidate.execution.id}",
                    execution_id=candidate.execution.id,
                    grant_id=candidate.execution.grant_id,
                    command_id=candidate.execution.command_id,
                    delivery_id=candidate.delivery.id,
                    revision_id=candidate.revision_id,
                    channel_id=candidate.channel_id,
                    remote_account_id=candidate.remote_page_id,
                    payload_hash=candidate.payload_hash,
                    outcome=ReceiptOutcome.POST_CREATED,
                    platform_post_id=post_id,
                )
                updated_execution = candidate.execution.accept_receipt(receipt)
                updated_delivery, _events = candidate.delivery.apply(
                    DeliveryEvent.RESOLVE_PUBLISHED,
                    {"now_ms": now_ms, "post_id_matches_page": True},
                )
                values = {
                    "updated_delivery": updated_delivery,
                    "updated_execution": updated_execution,
                    "post_id": post_id,
                    "permalink": evidence.permalink,
                    "actor_id": evidence.actor_id,
                    "reason": evidence.reason,
                    "evidence_kind": evidence.kind,
                    "audit_id": self._ids.new_id(),
                    "at_ms": now_ms,
                }
                outcome = "RESOLVED_PUBLISHED"
            elif evidence.kind == "NO_SIDE_EFFECT":
                if not evidence.make_execution_ref:
                    raise ValueError("NO_SIDE_EFFECT requires a Make execution reference")
                updated_execution = candidate.execution.resolve_no_side_effect(
                    actor_id=evidence.actor_id,
                    evidence=f"{evidence.make_execution_ref}: {evidence.reason}",
                )
                updated_delivery, _events = candidate.delivery.apply(
                    DeliveryEvent.RESOLVE_NO_SIDE_EFFECT,
                    {
                        "now_ms": now_ms,
                        "actor_id": evidence.actor_id,
                        "reason": evidence.reason,
                        "evidence": evidence.make_execution_ref,
                    },
                )
                values = {
                    "updated_delivery": updated_delivery,
                    "updated_execution": updated_execution,
                    "post_id": None,
                    "permalink": None,
                    "actor_id": evidence.actor_id,
                    "reason": evidence.reason,
                    "evidence_kind": evidence.kind,
                    "audit_id": self._ids.new_id(),
                    "at_ms": now_ms,
                }
                outcome = "RESOLVED_NO_SIDE_EFFECT"
            else:
                raise ValueError("unsupported UNKNOWN evidence kind")

            if not tx.commit_resolution(candidate, **values):
                return ResolveUnknownResult("STALE", candidate.delivery.state)
            return ResolveUnknownResult(outcome, updated_delivery.state)
