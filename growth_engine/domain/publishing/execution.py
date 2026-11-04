from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from growth_engine.domain.publishing.receipt import Receipt, ReceiptOutcome, is_placeholder_post_id
from growth_engine.domain.publishing.window import PublishingPolicy, grant_window


class ExecutionState(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    REPORTED = "REPORTED"
    NO_SIDE_EFFECT = "NO_SIDE_EFFECT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Execution:
    id: str
    delivery_id: str
    command_id: str
    grant_id: str
    state: ExecutionState
    grant_expires_at_ms: int
    receipt_due_at_ms: int
    platform_post_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("id", "delivery_id", "command_id", "grant_id"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if type(self.grant_expires_at_ms) is not int or type(self.receipt_due_at_ms) is not int:
            raise ValueError("execution timestamps must be integer epoch milliseconds")
        if self.state is ExecutionState.REPORTED and is_placeholder_post_id(self.platform_post_id):
            raise ValueError("REPORTED execution requires a real platform post id")

    @classmethod
    def authorize(
        cls,
        *,
        execution_id: str,
        delivery_id: str,
        command_id: str,
        grant_id: str,
        now_ms: int,
        deadline_at_ms: int,
        policy: PublishingPolicy,
    ) -> Execution:
        if any(not value.strip() for value in (execution_id, delivery_id, command_id, grant_id)):
            raise ValueError("execution identifiers are required")
        window = grant_window(
            now_ms=now_ms,
            deadline_at_ms=deadline_at_ms,
            ttl_seconds=policy.grant_ttl_seconds,
            receipt_grace_minutes=policy.receipt_grace_minutes,
        )
        return cls(
            id=execution_id,
            delivery_id=delivery_id,
            command_id=command_id,
            grant_id=grant_id,
            state=ExecutionState.AUTHORIZED,
            grant_expires_at_ms=window.grant_expires_at_ms,
            receipt_due_at_ms=window.receipt_due_at_ms,
        )

    def accept_receipt(
        self,
        receipt: Receipt,
        *,
        error_class_verified: bool = False,
    ) -> Execution:
        if type(error_class_verified) is not bool:
            raise ValueError("error_class_verified must be boolean")
        if (
            receipt.execution_id != self.id
            or receipt.grant_id != self.grant_id
            or receipt.command_id != self.command_id
            or receipt.delivery_id != self.delivery_id
        ):
            raise ValueError("receipt does not match execution grant")
        if self.state is ExecutionState.REPORTED:
            return self
        if self.state not in {ExecutionState.AUTHORIZED, ExecutionState.UNKNOWN}:
            raise ValueError("execution cannot accept a receipt from its current state")
        if receipt.outcome is ReceiptOutcome.POST_CREATED:
            return replace(
                self,
                state=ExecutionState.REPORTED,
                platform_post_id=receipt.platform_post_id,
            )
        if self.state is ExecutionState.UNKNOWN:
            return self
        if receipt.outcome is ReceiptOutcome.REJECTED_NO_SIDE_EFFECT:
            return replace(
                self,
                state=(ExecutionState.NO_SIDE_EFFECT if error_class_verified else ExecutionState.UNKNOWN),
            )
        return replace(self, state=ExecutionState.UNKNOWN)

    def timeout(self, *, now_ms: int) -> Execution:
        if (
            self.state is not ExecutionState.AUTHORIZED
            or type(now_ms) is not int
            or now_ms <= self.receipt_due_at_ms
        ):
            raise ValueError("receipt deadline has not passed")
        return replace(self, state=ExecutionState.UNKNOWN)

    def resolve_no_side_effect(self, *, actor_id: str, evidence: str) -> Execution:
        if (
            self.state is not ExecutionState.UNKNOWN
            or not actor_id.strip()
            or not evidence.strip()
        ):
            raise ValueError("UNKNOWN resolution requires actor and evidence")
        return replace(self, state=ExecutionState.NO_SIDE_EFFECT)

    def verify_mismatch(self) -> Execution:
        if self.state is not ExecutionState.REPORTED:
            raise ValueError("only a reported execution can become UNKNOWN after verification")
        return replace(self, state=ExecutionState.UNKNOWN)
