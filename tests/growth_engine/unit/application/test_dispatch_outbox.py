from __future__ import annotations

import base64
import json
from dataclasses import replace
from pathlib import Path
from typing import Mapping

import jsonschema
import pytest

from growth_engine.adapters.outbound.make.envelope import MakeEnvelopeBuilder
from growth_engine.adapters.outbound.make.http_transport import (
    HttpTransport,
    TransportDisposition,
)
from growth_engine.adapters.outbound.security.capability_tokens import (
    CapabilityTokenManager,
    CapabilityTokenInvalid,
    parse_key_ring,
)
from growth_engine.application.publishing.dispatch_outbox import (
    DispatchLease,
    DispatchOutbox,
    DispatchTransportResult,
)
from growth_engine.application.publishing.enqueue_due import EnqueueCommandClaims
from growth_engine.domain.publishing.command import CommandState, OutboxCommand
from growth_engine.domain.publishing.window import PublishingPolicy


SYNTHETIC_NOTE = "cần thay bằng fixture thật từ P0-T03/P0-T04"
SYNTHETIC_FIXTURE = {"_synthetic": True, "note": SYNTHETIC_NOTE}
OLD_KEY_FIXTURE = {
    **SYNTHETIC_FIXTURE,
    "keys": {"old": b"o" * 32},
}
ROTATED_KEY_FIXTURE = {
    **SYNTHETIC_FIXTURE,
    "keys": {"new": b"n" * 32, "old": b"o" * 32},
}
COMMAND_ID = "cmd-synthetic-001"
DELIVERY_ID = "delivery-synthetic-001"
REVISION_ID = "revision-synthetic-001"
CHANNEL_ID = "channel-synthetic-a"
REMOTE_PAGE_ID = "page-synthetic-a"
PAYLOAD_HASH = "a" * 64
MEDIA_SHA = "b" * 64
EPOCH = "epoch-synthetic-001"
NOW_MS = 1_800_000_000_000
DEADLINE_MS = NOW_MS + 3_600_000


class FakeClock:
    def now_ms(self) -> int:
        return NOW_MS


class FakeRng:
    def __call__(self, low: float, high: float) -> float:
        return min(3.0, high)


class FakeMediaURLs:
    def media_url(self, sha256: str, command_id: str, expires_at_ms: int) -> str:
        return f"https://growth.example.test/media/{sha256}?cmd={command_id}&exp={expires_at_ms}"


class FakeTransport:
    def __init__(self, outcomes: list[DispatchTransportResult]) -> None:
        self.outcomes = list(outcomes)
        self.sent: list[tuple[str, dict[str, object]]] = []

    def deliver(self, route_ref: str, envelope: dict[str, object]) -> DispatchTransportResult:
        self.sent.append((route_ref, envelope))
        return self.outcomes.pop(0)


class FakeDispatchStore:
    def __init__(self, command: OutboxCommand, *, state: CommandState = CommandState.PENDING) -> None:
        self.policy = PublishingPolicy(
            window_minutes=60,
            grant_ttl_seconds=60,
            receipt_grace_minutes=15,
            redeliver_after_ack_minutes=5,
            max_transport_attempts=8,
            verify_delay_minutes=5,
            unknown_escalation_minutes=30,
        )
        self.command = replace(command, state=state)
        self.context = {
            "environment": "test",
            "channel_id": CHANNEL_ID,
            "channel_key": "fb_hanoi",
            "platform": "facebook",
            "remote_page_id": REMOTE_PAGE_ID,
            "payload_hash": PAYLOAD_HASH,
            "dispatch_epoch": EPOCH,
            "route_ref": "route-synthetic-a",
            "media_sha256": MEDIA_SHA,
        }
        self.incidents: list[str] = []
        self.lease_counter = 0

    def claim_due(self, now_ms: int, limit: int, *, owner: str, lease_ms: int, policy: PublishingPolicy):
        command = self.command
        if command.state is CommandState.DELIVERING and command.lease_expires_at_ms is not None and now_ms >= command.lease_expires_at_ms:
            command = command.recover_expired_lease(now_ms=now_ms)
        if command.state is CommandState.ACKED:
            try:
                command = command.redeliver_after_ack(
                    now_ms=now_ms,
                    deadline_at_ms=command.expires_at_ms,
                    policy=policy,
                )
            except ValueError:
                return ()
        if command.state is not CommandState.PENDING or now_ms < command.next_attempt_at_ms:
            return ()
        if now_ms > command.expires_at_ms or command.attempts >= policy.max_transport_attempts:
            return ()
        self.lease_counter += 1
        lease_token = f"lease-synthetic-{self.lease_counter}"
        claimed = command.claim(
            now_ms=now_ms,
            lease_token=lease_token,
            lease_ttl_ms=lease_ms,
        )
        self.command = claimed
        return (DispatchLease(command=claimed, lease_token=lease_token, **self.context),)

    def complete_ack(self, lease: DispatchLease, *, at_ms: int) -> bool:
        if self.command.state is not CommandState.DELIVERING or self.command.lease_token != lease.lease_token:
            return False
        self.command = self.command.acknowledge(lease_token=lease.lease_token, at_ms=at_ms)
        return True

    def complete_retry(self, lease: DispatchLease, command: OutboxCommand, *, at_ms: int) -> bool:
        if self.command.state is not CommandState.DELIVERING or self.command.lease_token != lease.lease_token:
            return False
        self.command = command
        if self.command.attempts >= self.policy.max_transport_attempts:
            self.incidents.append("OUTBOX_RETRY_LIMIT")
        return True

    def complete_fatal(
        self,
        lease: DispatchLease,
        *,
        at_ms: int,
        status: int | None,
        next_attempt_at_ms: int,
    ) -> bool:
        if self.command.state is not CommandState.DELIVERING or self.command.lease_token != lease.lease_token:
            return False
        self.command = replace(
            self.command,
            state=CommandState.PENDING,
            next_attempt_at_ms=next_attempt_at_ms,
            lease_token=None,
            lease_expires_at_ms=None,
        )
        self.incidents.append(f"OUTBOX_FATAL:{status}")
        return True


def make_command(*, now_ms: int = NOW_MS, expires_at_ms: int = DEADLINE_MS) -> OutboxCommand:
    return OutboxCommand.new(
        command_id=COMMAND_ID,
        delivery_id=DELIVERY_ID,
        revision_id=REVISION_ID,
        sequence_no=1,
        expires_at_ms=expires_at_ms,
        now_ms=now_ms,
        envelope_token="v1.c3ludGhldGlj.c2ln",
    )


def make_dispatch(store: FakeDispatchStore, transport: FakeTransport) -> DispatchOutbox:
    return DispatchOutbox(
        store,
        transport,
        FakeMediaURLs(),
        MakeEnvelopeBuilder(),
        policy=store.policy,
        rng=FakeRng(),
        lease_ms=10_000,
        owner="publish-worker-synthetic",
    )


def test_capability_token_rejects_bad_signature_expiry_and_audience() -> None:
    old = CapabilityTokenManager(OLD_KEY_FIXTURE["keys"])
    claims = EnqueueCommandClaims(
        command_id=COMMAND_ID,
        delivery_id=DELIVERY_ID,
        revision_id=REVISION_ID,
        channel_id=CHANNEL_ID,
        remote_account_id=REMOTE_PAGE_ID,
        payload_hash=PAYLOAD_HASH,
        dispatch_epoch=EPOCH,
        audience=f"make-route:{CHANNEL_ID}",
        expires_at_ms=DEADLINE_MS,
    )
    token = old.issue(claims)

    with pytest.raises(CapabilityTokenInvalid):
        old.verify(token[:-1] + ("A" if token[-1] != "A" else "B"), claims.audience, NOW_MS)
    with pytest.raises(CapabilityTokenInvalid):
        old.verify(token, claims.audience, DEADLINE_MS + 1)
    with pytest.raises(CapabilityTokenInvalid):
        old.verify(token, "make-route:another-channel", NOW_MS)


def test_key_ring_parser_accepts_urlsafe_32_byte_key_and_rejects_short_key() -> None:
    encoded = base64.urlsafe_b64encode(b"k" * 32).decode("ascii").rstrip("=")
    short = base64.urlsafe_b64encode(b"short").decode("ascii").rstrip("=")

    assert parse_key_ring(f"kid1:{encoded}") == {"kid1": b"k" * 32}
    with pytest.raises(ValueError, match="32 bytes"):
        parse_key_ring(f"short:{short}")


def test_rotated_key_ring_verifies_a_token_signed_by_old_key() -> None:
    old = CapabilityTokenManager(OLD_KEY_FIXTURE["keys"])
    rotated = CapabilityTokenManager(ROTATED_KEY_FIXTURE["keys"])
    claims = EnqueueCommandClaims(
        command_id=COMMAND_ID,
        delivery_id=DELIVERY_ID,
        revision_id=REVISION_ID,
        channel_id=CHANNEL_ID,
        remote_account_id=REMOTE_PAGE_ID,
        payload_hash=PAYLOAD_HASH,
        dispatch_epoch=EPOCH,
        audience=f"make-route:{CHANNEL_ID}",
        expires_at_ms=DEADLINE_MS,
    )
    verified = rotated.verify(old.issue(claims), claims.audience, NOW_MS)

    assert verified.dispatch_epoch == EPOCH
    assert verified.command_id == COMMAND_ID


def test_command_envelope_matches_schema_without_extra_fields() -> None:
    schema = json.loads(Path("contracts/growth_engine/command_envelope.v2.schema.json").read_text())
    lease = DispatchLease(
        command=make_command(),
        lease_token="lease-synthetic",
        environment="test",
        channel_id=CHANNEL_ID,
        channel_key="fb_hanoi",
        platform="facebook",
        remote_page_id=REMOTE_PAGE_ID,
        payload_hash=PAYLOAD_HASH,
        dispatch_epoch=EPOCH,
        route_ref="route-synthetic-a",
        media_sha256=MEDIA_SHA,
    )
    envelope = MakeEnvelopeBuilder().build(
        lease,
        media_url=FakeMediaURLs().media_url(MEDIA_SHA, COMMAND_ID, DEADLINE_MS),
    )

    jsonschema.validate(envelope, schema)
    assert envelope["schema_version"] == "growth.command.v2"
    assert envelope["command_token"] == "v1.c3ludGhldGlj.c2ln"
    assert envelope["dispatch_epoch"] == EPOCH
    assert envelope["channel_key"] == "fb_hanoi"
    assert envelope["platform"] == "facebook"
    assert "_synthetic" not in envelope
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**envelope, "access_token": "never"}, schema)
    instagram_envelope = MakeEnvelopeBuilder().build(
        replace(lease, channel_key="ig_venho", platform="instagram"),
        media_url=FakeMediaURLs().media_url(MEDIA_SHA, COMMAND_ID, DEADLINE_MS),
    )
    jsonschema.validate(instagram_envelope, schema)
    assert instagram_envelope["channel_key"] == "ig_venho"
    assert instagram_envelope["platform"] == "instagram"


def test_media_url_lifetime_extends_thirty_minutes_past_execution_deadline() -> None:
    store = FakeDispatchStore(make_command())
    transport = FakeTransport([DispatchTransportResult(TransportDisposition.ACK, status=200)])

    make_dispatch(store, transport).execute(NOW_MS)

    assert transport.sent[0][1]["media_url"].endswith(
        f"exp={DEADLINE_MS + 30 * 60_000}"
    )


def test_retryable_transport_retries_same_envelope_after_backoff() -> None:
    store = FakeDispatchStore(make_command())
    transport = FakeTransport(
        [
            DispatchTransportResult(TransportDisposition.RETRYABLE, status=None),
            DispatchTransportResult(TransportDisposition.ACK, status=200),
        ]
    )
    use_case = make_dispatch(store, transport)

    first = use_case.execute(NOW_MS)
    assert first.retried_command_ids == (COMMAND_ID,)
    assert store.command.state is CommandState.PENDING
    assert store.command.next_attempt_at_ms == NOW_MS + 3_000

    second = use_case.execute(NOW_MS + 3_000)

    assert second.acked_command_ids == (COMMAND_ID,)
    assert store.command.state is CommandState.ACKED
    assert len(transport.sent) == 2
    assert transport.sent[0] == transport.sent[1]


def test_ack_without_authorize_after_five_minutes_redelivers_same_envelope() -> None:
    store = FakeDispatchStore(make_command())
    transport = FakeTransport(
        [
            DispatchTransportResult(TransportDisposition.ACK, status=200),
            DispatchTransportResult(TransportDisposition.ACK, status=200),
        ]
    )
    use_case = make_dispatch(store, transport)

    use_case.execute(NOW_MS)
    redelivery_time = NOW_MS + 5 * 60_000
    result = use_case.execute(redelivery_time)

    assert result.acked_command_ids == (COMMAND_ID,)
    assert len(transport.sent) == 2
    assert transport.sent[0] == transport.sent[1]
    assert store.command.attempts == 0


def test_authorized_command_is_never_redelivered() -> None:
    store = FakeDispatchStore(make_command(), state=CommandState.AUTHORIZED)
    transport = FakeTransport([DispatchTransportResult(TransportDisposition.ACK, status=200)])

    result = make_dispatch(store, transport).execute(NOW_MS)

    assert result.claimed_count == 0
    assert transport.sent == []
    assert store.command.state is CommandState.AUTHORIZED


def test_stale_lease_fencing_prevents_completion() -> None:
    store = FakeDispatchStore(make_command())
    old_lease = store.claim_due(NOW_MS, 1, owner="worker-a", lease_ms=1_000, policy=store.policy)[0]
    new_lease = store.claim_due(
        NOW_MS + 1_000,
        1,
        owner="worker-b",
        lease_ms=10_000,
        policy=store.policy,
    )[0]

    assert old_lease.lease_token != new_lease.lease_token
    assert not store.complete_ack(old_lease, at_ms=NOW_MS + 1_000)
    assert store.complete_ack(new_lease, at_ms=NOW_MS + 1_000)
    assert store.command.state is CommandState.ACKED


def test_http_transport_uses_separate_timeouts_and_classifies_without_network(caplog) -> None:
    calls: dict[str, object] = {}

    class FakeSocket:
        def settimeout(self, value: float) -> None:
            calls["read_timeout"] = value

    class FakeResponse:
        status = 503
        headers = {"Retry-After": "12"}

    class FakeConnection:
        sock = FakeSocket()

        def __init__(self, host: str, port: int, *, timeout: float) -> None:
            calls["host"] = host
            calls["port"] = port
            calls["connect_timeout"] = timeout

        def request(self, method: str, target: str, *, body: bytes, headers: Mapping[str, str]) -> None:
            calls["request"] = (method, target, json.loads(body), dict(headers))

        def getresponse(self) -> FakeResponse:
            return FakeResponse()

        def close(self) -> None:
            calls["closed"] = True

    result = HttpTransport(FakeClock(), connection_factory=FakeConnection).deliver(
        "https://make.example.test/hooks/private/path?opaque=secret",
        {"_synthetic": True, "note": SYNTHETIC_NOTE},
    )

    assert result.disposition is TransportDisposition.RETRYABLE
    assert result.status == 503
    assert result.retry_after_seconds == 12
    assert calls["connect_timeout"] == 5
    assert calls["read_timeout"] == 15
    assert calls["closed"] is True
    assert "opaque=secret" not in caplog.text


def test_http_transport_classifies_client_error_as_fatal_without_logging_url() -> None:
    class FakeConnection:
        sock = object()

        def __init__(self, host: str, port: int, *, timeout: float) -> None:
            pass

        def request(self, *args, **kwargs) -> None:
            pass

        def getresponse(self):
            return type("Response", (), {"status": 403, "headers": {}})()

        def close(self) -> None:
            pass

    result = HttpTransport(FakeClock(), connection_factory=FakeConnection).deliver(
        "https://make.example.test/hooks/private", {"_synthetic": True}
    )

    assert result.disposition is TransportDisposition.FATAL
    assert result.status == 403
