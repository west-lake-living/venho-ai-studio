from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import math

from growth_engine.domain.publishing.backoff import RandomUniform, full_jitter
from growth_engine.domain.publishing.window import PublishingPolicy


class CommandState(str, Enum):
    PENDING = "PENDING"
    DELIVERING = "DELIVERING"
    ACKED = "ACKED"
    AUTHORIZED = "AUTHORIZED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


def business_key(delivery_id: str, revision_id: str, seq: int) -> str:
    if not delivery_id.strip() or not revision_id.strip():
        raise ValueError("delivery_id and revision_id are required")
    if type(seq) is not int or seq < 1:
        raise ValueError("seq must be a positive integer")
    return f"publish:{delivery_id}:{revision_id}:{seq}"


@dataclass(frozen=True)
class OutboxCommand:
    id: str
    delivery_id: str
    revision_id: str
    sequence_no: int
    business_key: str
    expires_at_ms: int
    next_attempt_at_ms: int
    envelope_token: str
    state: CommandState = CommandState.PENDING
    attempts: int = 0
    lease_token: str | None = None
    lease_expires_at_ms: int | None = None
    acked_at_ms: int | None = None

    @classmethod
    def new(
        cls,
        *,
        command_id: str,
        delivery_id: str,
        revision_id: str,
        sequence_no: int,
        expires_at_ms: int,
        now_ms: int,
        envelope_token: str,
    ) -> OutboxCommand:
        key = business_key(delivery_id, revision_id, sequence_no)
        if not command_id.strip() or not envelope_token.strip():
            raise ValueError("command_id and envelope_token are required")
        if type(expires_at_ms) is not int or type(now_ms) is not int or now_ms > expires_at_ms:
            raise ValueError("command timestamps are invalid")
        return cls(
            id=command_id,
            delivery_id=delivery_id,
            revision_id=revision_id,
            sequence_no=sequence_no,
            business_key=key,
            expires_at_ms=expires_at_ms,
            next_attempt_at_ms=now_ms,
            envelope_token=envelope_token,
        )

    def claim(
        self,
        *,
        now_ms: int,
        lease_token: str,
        lease_ttl_ms: int,
        max_attempts: int = 8,
    ) -> OutboxCommand:
        if (
            self.state is not CommandState.PENDING
            or type(now_ms) is not int
            or now_ms < self.next_attempt_at_ms
            or now_ms > self.expires_at_ms
            or self.attempts >= max_attempts
            or not lease_token.strip()
            or type(lease_ttl_ms) is not int
            or lease_ttl_ms <= 0
        ):
            raise ValueError("command is not claimable")
        return replace(
            self,
            state=CommandState.DELIVERING,
            lease_token=lease_token,
            lease_expires_at_ms=now_ms + lease_ttl_ms,
        )

    def acknowledge(self, *, lease_token: str, at_ms: int) -> OutboxCommand:
        if (
            self.state is not CommandState.DELIVERING
            or not lease_token.strip()
            or lease_token != self.lease_token
            or type(at_ms) is not int
        ):
            raise ValueError("lease token does not own this command")
        return replace(self, state=CommandState.ACKED, acked_at_ms=at_ms)

    def transport_failed(
        self,
        *,
        at_ms: int,
        rng: RandomUniform,
        retry_after_seconds: float = 0.0,
    ) -> OutboxCommand:
        if self.state is not CommandState.DELIVERING or type(at_ms) is not int:
            raise ValueError("only a delivering command can be retried")
        if not isinstance(retry_after_seconds, (int, float)) or not math.isfinite(retry_after_seconds) or retry_after_seconds < 0:
            raise ValueError("retry_after_seconds must be a non-negative finite number")
        delay_seconds = max(full_jitter(self.attempts, rng), float(retry_after_seconds))
        return replace(
            self,
            state=CommandState.PENDING,
            attempts=self.attempts + 1,
            next_attempt_at_ms=at_ms + math.ceil(delay_seconds * 1_000),
            lease_token=None,
            lease_expires_at_ms=None,
        )

    def recover_expired_lease(self, *, now_ms: int) -> OutboxCommand:
        if (
            self.state is not CommandState.DELIVERING
            or self.lease_expires_at_ms is None
            or type(now_ms) is not int
            or now_ms < self.lease_expires_at_ms
        ):
            raise ValueError("delivery lease has not expired")
        return replace(
            self,
            state=CommandState.PENDING,
            next_attempt_at_ms=now_ms,
            lease_token=None,
            lease_expires_at_ms=None,
        )

    def redeliver_after_ack(
        self,
        *,
        now_ms: int,
        deadline_at_ms: int,
        policy: PublishingPolicy,
    ) -> OutboxCommand:
        wait_until = (
            None
            if self.acked_at_ms is None
            else self.acked_at_ms + policy.redeliver_after_ack_minutes * 60_000
        )
        if (
            self.state is not CommandState.ACKED
            or wait_until is None
            or type(now_ms) is not int
            or type(deadline_at_ms) is not int
            or now_ms < wait_until
            or now_ms >= deadline_at_ms - 2 * 60_000
            or self.attempts >= policy.max_transport_attempts
        ):
            raise ValueError("ACKed command is not eligible for redelivery")
        return replace(
            self,
            state=CommandState.PENDING,
            next_attempt_at_ms=now_ms,
            lease_token=None,
            lease_expires_at_ms=None,
            acked_at_ms=None,
        )

    def authorize(self) -> OutboxCommand:
        if self.state not in {CommandState.PENDING, CommandState.DELIVERING, CommandState.ACKED}:
            raise ValueError("command cannot be authorized from its current state")
        return replace(
            self,
            state=CommandState.AUTHORIZED,
            lease_token=None,
            lease_expires_at_ms=None,
        )

    def cancel(self) -> OutboxCommand:
        if self.state not in {CommandState.PENDING, CommandState.DELIVERING, CommandState.ACKED}:
            raise ValueError("command cannot be cancelled from its current state")
        return replace(
            self,
            state=CommandState.CANCELLED,
            lease_token=None,
            lease_expires_at_ms=None,
        )

    def expire(self, *, now_ms: int) -> OutboxCommand:
        if (
            self.state not in {CommandState.PENDING, CommandState.DELIVERING, CommandState.ACKED}
            or type(now_ms) is not int
            or now_ms <= self.expires_at_ms
        ):
            raise ValueError("command is not expired")
        return replace(
            self,
            state=CommandState.EXPIRED,
            lease_token=None,
            lease_expires_at_ms=None,
        )
