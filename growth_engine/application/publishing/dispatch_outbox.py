from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
import math
import re
from typing import Protocol

from growth_engine.domain.publishing.command import CommandState, OutboxCommand
from growth_engine.domain.publishing.backoff import RandomUniform
from growth_engine.domain.publishing.window import PublishingPolicy


class TransportDisposition(str, Enum):
    ACK = "ACK"
    RETRYABLE = "RETRYABLE"
    FATAL = "FATAL"


@dataclass(frozen=True)
class DispatchTransportResult:
    disposition: TransportDisposition
    status: int | None
    retry_after_seconds: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, TransportDisposition):
            raise ValueError("disposition is invalid")
        if self.status is not None and (type(self.status) is not int or not 100 <= self.status <= 599):
            raise ValueError("status must be an HTTP status or None")
        if self.retry_after_seconds is not None and (
            isinstance(self.retry_after_seconds, bool)
            or not isinstance(self.retry_after_seconds, (int, float))
            or not math.isfinite(self.retry_after_seconds)
            or self.retry_after_seconds < 0
        ):
            raise ValueError("retry_after_seconds must be non-negative")


@dataclass(frozen=True)
class DispatchLease:
    command: OutboxCommand
    lease_token: str
    environment: str
    channel_id: str
    channel_key: str
    platform: str
    remote_page_id: str
    payload_hash: str
    dispatch_epoch: str
    route_ref: str
    media_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "lease_token", "environment", "channel_id", "channel_key", "platform", "remote_page_id",
            "payload_hash", "dispatch_epoch", "route_ref", "media_sha256",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if self.environment not in {"test", "production"}:
            raise ValueError("environment is invalid")
        if self.platform not in {"facebook", "instagram"}:
            raise ValueError("platform is unsupported")
        if not re.fullmatch(r"[0-9a-f]{64}", self.payload_hash) or not re.fullmatch(
            r"[0-9a-f]{64}", self.media_sha256
        ):
            raise ValueError("payload and media hashes must be SHA-256 hex digests")


class DispatchStore(Protocol):
    def claim_due(
        self,
        now_ms: int,
        limit: int,
        *,
        owner: str,
        lease_ms: int,
        policy: PublishingPolicy,
    ) -> Sequence[DispatchLease]: ...

    def complete_ack(self, lease: DispatchLease, *, at_ms: int) -> bool: ...
    def complete_retry(self, lease: DispatchLease, command: OutboxCommand, *, at_ms: int) -> bool: ...
    def complete_fatal(
        self,
        lease: DispatchLease,
        *,
        at_ms: int,
        status: int | None,
        next_attempt_at_ms: int,
    ) -> bool: ...


class DispatchTransport(Protocol):
    def deliver(self, route_ref: str, envelope: dict[str, object]) -> DispatchTransportResult: ...


class MediaURLIssuer(Protocol):
    def media_url(self, sha256: str, command_id: str, expires_at_ms: int) -> str: ...


class EnvelopeBuilder(Protocol):
    def build(self, lease: DispatchLease, *, media_url: str) -> dict[str, object]: ...


@dataclass(frozen=True)
class DispatchOutboxResult:
    claimed_count: int = 0
    acked_command_ids: tuple[str, ...] = ()
    retried_command_ids: tuple[str, ...] = ()
    fatal_command_ids: tuple[str, ...] = ()
    stale_lease_command_ids: tuple[str, ...] = ()


class DispatchOutbox:
    """Lease, send and complete outbox commands with fencing at every write."""

    def __init__(
        self,
        store: DispatchStore,
        transport: DispatchTransport,
        media_urls: MediaURLIssuer,
        envelope_builder: EnvelopeBuilder,
        *,
        policy: PublishingPolicy,
        rng: RandomUniform,
        lease_ms: int = 30_000,
        owner: str = "publish-worker",
    ) -> None:
        if type(lease_ms) is not int or lease_ms <= 0 or not owner.strip():
            raise ValueError("lease_ms and owner are required")
        self._store = store
        self._transport = transport
        self._media_urls = media_urls
        self._envelopes = envelope_builder
        self._policy = policy
        self._rng = rng
        self._lease_ms = lease_ms
        self._owner = owner

    def execute(self, now_ms: int, limit: int = 20) -> DispatchOutboxResult:
        if type(now_ms) is not int or now_ms < 0 or type(limit) is not int or limit < 1:
            raise ValueError("now_ms and limit are invalid")
        leases = tuple(
            self._store.claim_due(
                now_ms,
                limit,
                owner=self._owner,
                lease_ms=self._lease_ms,
                policy=self._policy,
            )
        )
        acked: list[str] = []
        retried: list[str] = []
        fatal: list[str] = []
        stale: list[str] = []
        for lease in leases:
            command = lease.command
            if (
                command.state is not CommandState.DELIVERING
                or command.lease_token != lease.lease_token
                or now_ms > command.expires_at_ms
            ):
                stale.append(command.id)
                continue
            media_url = self._media_urls.media_url(
                lease.media_sha256,
                command.id,
                command.expires_at_ms + 30 * 60_000,
            )
            envelope = self._envelopes.build(lease, media_url=media_url)
            try:
                outcome = self._transport.deliver(lease.route_ref, envelope)
            except Exception:
                # A transport exception is ambiguous; keep the exact command for safe retry.
                outcome = DispatchTransportResult(TransportDisposition.RETRYABLE, status=None)
            completed = False
            if outcome.disposition is TransportDisposition.ACK:
                completed = self._store.complete_ack(lease, at_ms=now_ms)
                (acked if completed else stale).append(command.id)
            elif outcome.disposition is TransportDisposition.RETRYABLE:
                updated = command.transport_failed(
                    at_ms=now_ms,
                    rng=self._rng,
                    retry_after_seconds=outcome.retry_after_seconds or 0.0,
                )
                completed = self._store.complete_retry(lease, updated, at_ms=now_ms)
                (retried if completed else stale).append(command.id)
            elif outcome.disposition is TransportDisposition.FATAL:
                completed = self._store.complete_fatal(
                    lease,
                    at_ms=now_ms,
                    status=outcome.status,
                    next_attempt_at_ms=command.expires_at_ms + 1,
                )
                (fatal if completed else stale).append(command.id)
            else:
                raise ValueError("transport returned an unsupported disposition")
        return DispatchOutboxResult(
            claimed_count=len(leases),
            acked_command_ids=tuple(acked),
            retried_command_ids=tuple(retried),
            fatal_command_ids=tuple(fatal),
            stale_lease_command_ids=tuple(stale),
        )
