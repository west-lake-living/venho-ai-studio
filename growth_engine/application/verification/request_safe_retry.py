from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.publishing.command import CommandState, OutboxCommand, business_key
from growth_engine.domain.publishing.execution import ExecutionState


@dataclass(frozen=True)
class SafeRetryCandidate:
    delivery: Delivery
    current_revision_id: str
    deadline_at_ms: int
    max_sequence_no: int
    execution_states: tuple[ExecutionState, ...]
    has_live_execution: bool
    approval_valid: bool
    approval_revoked: bool


class SafeRetryTransaction(Protocol):
    def get_candidate(self, delivery_id: str) -> SafeRetryCandidate | None: ...
    def commit_safe_retry(
        self,
        candidate: SafeRetryCandidate,
        *,
        updated_delivery: Delivery,
        command: OutboxCommand,
        expected_row_version: int,
        actor_id: str,
        reason: str,
        audit_id: str,
        at_ms: int,
    ) -> bool: ...


class SafeRetryStore(Protocol):
    def begin_immediate(self) -> object: ...


class SafeRetryCommandFactory(Protocol):
    def create(self, candidate: SafeRetryCandidate, sequence_no: int, now_ms: int) -> OutboxCommand: ...


@dataclass(frozen=True)
class RequestSafeRetryResult:
    delivery_id: str
    command_id: str
    sequence_no: int
    business_key: str


class RequestSafeRetry:
    def __init__(
        self,
        store: SafeRetryStore,
        commands: SafeRetryCommandFactory,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._store = store
        self._commands = commands
        self._clock = clock
        self._ids = ids

    def execute(
        self,
        delivery_id: str,
        *,
        expected_row_version: int,
        actor_id: str,
        reason: str,
    ) -> RequestSafeRetryResult:
        if expected_row_version < 1 or not actor_id.strip() or not reason.strip():
            raise ValueError("expected row version, actor and reason are required")
        now_ms = self._clock.now_ms()
        with self._store.begin_immediate() as tx:
            candidate = tx.get_candidate(delivery_id)
            if candidate is None or candidate.delivery.state is not DeliveryState.BLOCKED:
                raise ValueError("safe retry is available only for a BLOCKED delivery")
            if candidate.delivery.row_version != expected_row_version:
                raise ValueError("delivery changed; reload before retrying")
            no_live_execution = not candidate.has_live_execution
            all_prior_no_side_effect = all(
                state is ExecutionState.NO_SIDE_EFFECT for state in candidate.execution_states
            )
            if candidate.has_live_execution or not all_prior_no_side_effect:
                raise ValueError("retry requires no live execution and only NO_SIDE_EFFECT history")
            if candidate.approval_revoked or not candidate.approval_valid:
                raise ValueError("current revision approval is missing or revoked")
            window_open = now_ms < candidate.deadline_at_ms - 2 * 60_000
            if not window_open:
                raise ValueError("safe retry window has closed")

            sequence_no = candidate.max_sequence_no + 1
            updated_delivery, _events = candidate.delivery.apply(
                DeliveryEvent.SAFE_RETRY,
                {
                    "now_ms": now_ms,
                    "no_execution_live": no_live_execution,
                    "all_prior_executions_no_side_effect": all_prior_no_side_effect,
                    "window_open": window_open,
                    "approval_valid": candidate.approval_valid and not candidate.approval_revoked,
                },
            )
            command = self._commands.create(candidate, sequence_no, now_ms)
            expected_key = business_key(delivery_id, candidate.current_revision_id, sequence_no)
            if (
                command.delivery_id != delivery_id
                or command.revision_id != candidate.current_revision_id
                or command.sequence_no != sequence_no
                or command.business_key != expected_key
                or command.state is not CommandState.PENDING
            ):
                raise ValueError("safe retry command factory returned an invalid command")
            if not tx.commit_safe_retry(
                candidate,
                updated_delivery=updated_delivery,
                command=command,
                expected_row_version=expected_row_version,
                actor_id=actor_id,
                reason=reason,
                audit_id=self._ids.new_id(),
                at_ms=now_ms,
            ):
                raise ValueError("safe retry lost a concurrent state change")
            return RequestSafeRetryResult(delivery_id, command.id, sequence_no, command.business_key)
