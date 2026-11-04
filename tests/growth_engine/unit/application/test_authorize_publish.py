from __future__ import annotations

import hashlib
import json
import threading
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator

import jsonschema
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from growth_engine.adapters.inbound.api.app import create_app
from growth_engine.adapters.inbound.api.routers.internal_executions import router
from growth_engine.adapters.outbound.security.capability_tokens import CapabilityTokenManager
from growth_engine.application.publishing.authorize_publish import (
    AuthorizeCandidate,
    AuthorizePublish,
    AuthorizePublishCommand,
)
from growth_engine.application.publishing.enqueue_due import EnqueueCommandClaims
from growth_engine.domain.channels.channel import Channel, ChannelConfig, ChannelPlatform, config_hash
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.media.asset import MediaVariant, VariantQcStatus
from growth_engine.domain.media.qc import QcDecision, QcReport
from growth_engine.domain.publishing.command import CommandState, OutboxCommand
from growth_engine.domain.publishing.runtime_mode import PublishMode, RuntimeControls
from growth_engine.domain.publishing.window import PublishingPolicy
from growth_engine.domain.kernel.errors import DomainError


SYNTHETIC_NOTE = "cần thay bằng fixture thật từ P0-T03/P0-T04"
SYNTHETIC_FIXTURE = {"_synthetic": True, "note": SYNTHETIC_NOTE}
CHANNEL_ID = "channel-synthetic-hanoi"
CHANNEL_KEY = "fb_hanoi"
REMOTE_PAGE_ID = "remote-page-synthetic-hanoi"
DELIVERY_ID = "delivery-synthetic-001"
REVISION_ID = "revision-synthetic-001"
COMMAND_ID = "command-synthetic-001"
CAPTION = "Synthetic approved caption"
NOW_MS = 1_800_000_000_000
DEADLINE_MS = NOW_MS + 600_000
PAYLOAD_HASH = "a" * 64
FACTS_HASH = "b" * 64
RULESET_HASH = "c" * 64
MEDIA_SHA = "d" * 64


class FakeClock:
    def __init__(self, now_ms: int) -> None:
        self.value = now_ms

    def now_ms(self) -> int:
        return self.value


class FakeIds:
    def __init__(self) -> None:
        self.counter = 0

    def new_id(self) -> str:
        self.counter += 1
        return f"synthetic-id-{self.counter}"


class FakeMediaStore:
    def __init__(self, valid: bool = True) -> None:
        self.valid = valid
        self.calls: list[tuple[str, str]] = []

    def verify(self, object_key: str, sha256: str) -> bool:
        self.calls.append((object_key, sha256))
        return self.valid


class FakeAuthorizeStore:
    def __init__(self, channel: Channel, candidate: AuthorizeCandidate, controls: RuntimeControls) -> None:
        self.channels = {channel.channel_key: channel}
        self.candidate = candidate
        self.controls = controls
        self.executions = []
        self.audit: list[str] = []
        self.incidents: list[str] = []
        self.blocked_reason: str | None = None
        self.hook_before_transaction = None
        self._lock = threading.RLock()

    def resolve_channel_by_key(self, channel_key: str) -> Channel | None:
        return self.channels.get(channel_key)

    def read_candidate(self, command_id: str) -> AuthorizeCandidate | None:
        return self.candidate if self.candidate.command.id == command_id else None

    @contextmanager
    def begin_immediate(self) -> Iterator["FakeAuthorizeStore"]:
        with self._lock:
            if self.hook_before_transaction is not None:
                hook = self.hook_before_transaction
                self.hook_before_transaction = None
                hook(self)
            yield self

    def current_controls(self) -> RuntimeControls:
        return self.controls

    def get_candidate(self, command_id: str) -> AuthorizeCandidate | None:
        return self.candidate if self.candidate.command.id == command_id else None

    def commit_authorized(
        self,
        candidate: AuthorizeCandidate,
        command: OutboxCommand,
        delivery: Delivery,
        execution,
        *,
        principal_id: str,
        expected_row_version: int,
        audit_event_id: str,
        correlation_id: str,
        at_ms: int,
    ) -> bool:
        if self.candidate.delivery.row_version != expected_row_version:
            return False
        self.candidate = replace(
            self.candidate,
            command=command,
            delivery=delivery,
            has_live_execution=True,
        )
        self.executions.append(execution)
        self.audit.append(audit_event_id)
        return True

    def commit_blocked(
        self,
        candidate: AuthorizeCandidate,
        command: OutboxCommand,
        delivery: Delivery,
        *,
        expected_row_version: int,
        blocked_reason: str,
        audit_event_id: str,
        incident_id: str,
        correlation_id: str,
        at_ms: int,
    ) -> bool:
        if self.candidate.delivery.row_version != expected_row_version:
            return False
        self.candidate = replace(self.candidate, command=command, delivery=delivery)
        self.blocked_reason = blocked_reason
        self.audit.append(audit_event_id)
        self.incidents.append(incident_id)
        return True

    def commit_expired(
        self,
        candidate: AuthorizeCandidate,
        command: OutboxCommand,
        delivery: Delivery,
        *,
        expected_row_version: int,
        audit_event_id: str,
        correlation_id: str,
        at_ms: int,
    ) -> bool:
        if self.candidate.delivery.row_version != expected_row_version:
            return False
        self.candidate = replace(self.candidate, command=command, delivery=delivery)
        self.audit.append(audit_event_id)
        return True


def make_world(
    *,
    now_ms: int = NOW_MS,
    deadline_at_ms: int = DEADLINE_MS,
    token_exp_ms: int | None = None,
    mode: PublishMode = PublishMode.LIVE_MANUAL,
    global_pause: bool = False,
    channel_paused: bool = False,
    media_valid: bool = True,
) -> dict[str, object]:
    channel = Channel(
        id=CHANNEL_ID,
        project_id="venho_hotel",
        environment="test",
        channel_key=CHANNEL_KEY,
        platform=ChannelPlatform.FACEBOOK,
        remote_account_id=REMOTE_PAGE_ID,
        name="Hanoi synthetic",
        enabled=True,
        paused=channel_paused,
    )
    config = ChannelConfig(
        id="config-synthetic-hanoi",
        channel_id=channel.id,
        version=1,
        make_route_ref="route-synthetic-hanoi",
        graph_api_version="REQUIRED_FROM_P0",
        capability={**SYNTHETIC_FIXTURE},
    )
    variant = MediaVariant(
        id="variant-synthetic-001",
        asset_id="asset-synthetic-001",
        transform_version="synthetic-v1",
        sha256=MEDIA_SHA,
        object_key="variants/synthetic.jpg",
        width=1080,
        height=1350,
        mime="image/jpeg",
        byte_size=100_000,
        qc_status=VariantQcStatus.PASS,
        created_at_ms=NOW_MS - 60_000,
    )
    report = QcReport(
        id="qc-synthetic-001",
        variant_id=variant.id,
        caption_hash=hashlib.sha256(CAPTION.encode("utf-8")).hexdigest(),
        ruleset_hash=RULESET_HASH,
        fact_snapshot_hash=FACTS_HASH,
        decision=QcDecision.PASS,
        coverage_gaps=(),
        result_json="{}",
        created_at_ms=NOW_MS - 50_000,
    )
    revision = DeliveryRevision.create(
        {
            "delivery_id": DELIVERY_ID,
            "revision_id": REVISION_ID,
            "channel_id": channel.id,
            "remote_account_id": channel.remote_account_id,
            "channel_config_hash": config_hash(config),
            "caption": CAPTION,
            "media": [{"sha256": MEDIA_SHA, "mime": "image/jpeg", "width": 1080, "height": 1350}],
            "scheduled_at_ms": NOW_MS - 60_000,
            "deadline_at_ms": deadline_at_ms,
            "qc_report_id": report.id,
            "ruleset_hash": report.ruleset_hash,
            "fact_snapshot_hash": report.fact_snapshot_hash,
        }
    )
    approval = ApprovalDecision(
        id="approval-synthetic-001",
        revision_id=REVISION_ID,
        payload_hash=revision.payload_hash,
        decision=ApprovalType.APPROVE,
        actor_id="synthetic-editor",
        created_at_ms=NOW_MS - 30_000,
    )
    command = OutboxCommand.new(
        command_id=COMMAND_ID,
        delivery_id=DELIVERY_ID,
        revision_id=REVISION_ID,
        sequence_no=1,
        expires_at_ms=deadline_at_ms,
        now_ms=NOW_MS - 10_000,
        envelope_token="synthetic-command-token",
    )
    candidate = AuthorizeCandidate(
        command=command,
        command_payload_hash=revision.payload_hash,
        command_dispatch_epoch="epoch-synthetic-001",
        delivery=Delivery(DELIVERY_ID, DeliveryState.QUEUED, row_version=4),
        current_revision_id=REVISION_ID,
        active_approval_id=approval.id,
        revision=revision,
        approval=approval,
        approval_revoked=False,
        channel=channel,
        channel_config=config,
        variant=variant,
        qc_report=report,
        facts_valid=True,
        has_live_execution=False,
    )
    controls = RuntimeControls(mode, "epoch-synthetic-001", global_pause=global_pause)
    store = FakeAuthorizeStore(channel, candidate, controls)
    tokens = CapabilityTokenManager({"synthetic-kid": b"k" * 32})
    claims = EnqueueCommandClaims(
        command_id=COMMAND_ID,
        delivery_id=DELIVERY_ID,
        revision_id=REVISION_ID,
        channel_id=CHANNEL_ID,
        remote_account_id=REMOTE_PAGE_ID,
        payload_hash=revision.payload_hash,
        dispatch_epoch="epoch-synthetic-001",
        audience=f"make-route:{CHANNEL_ID}",
        expires_at_ms=token_exp_ms if token_exp_ms is not None else deadline_at_ms,
    )
    token = tokens.issue(claims)
    media = FakeMediaStore(media_valid)
    clock = FakeClock(now_ms)
    use_case = AuthorizePublish(
        store,
        tokens,
        media,
        clock,
        FakeIds(),
        PublishingPolicy(
            window_minutes=20,
            grant_ttl_seconds=60,
            receipt_grace_minutes=15,
            redeliver_after_ack_minutes=5,
            max_transport_attempts=8,
            verify_delay_minutes=5,
            unknown_escalation_minutes=30,
        ),
    )
    return {
        "channel": channel,
        "store": store,
        "tokens": tokens,
        "token": token,
        "media": media,
        "clock": clock,
        "use_case": use_case,
        "revision": revision,
        "variant": variant,
        "candidate": candidate,
    }


def request_for(
    world: dict[str, object],
    *,
    channel_key: str = CHANNEL_KEY,
    token: str | None = None,
    payload_hash: str | None = None,
):
    return AuthorizePublishCommand(
        command_token=token if token is not None else world["token"],
        payload_hash=payload_hash if payload_hash is not None else world["revision"].payload_hash,
        media_report_http_status=200,
        media_report_content_type="image/jpeg",
        principal_id="make-fb-hanoi",
        principal_channel_key=channel_key,
        correlation_id="corr-synthetic-001",
    )


def test_first_authorization_executes_and_replay_returns_already_authorized() -> None:
    world = make_world()
    result = world["use_case"].execute(request_for(world))

    assert result.execute is True
    assert result.reason is None
    assert result.remote_page_id == REMOTE_PAGE_ID
    assert result.caption == CAPTION
    assert world["store"].candidate.delivery.state is DeliveryState.EXECUTING
    assert world["store"].candidate.command.state is CommandState.AUTHORIZED
    assert len(world["store"].executions) == 1

    replay = world["use_case"].execute(request_for(world))

    assert replay.execute is False
    assert replay.reason == "ALREADY_AUTHORIZED"
    assert len(world["store"].executions) == 1


@pytest.mark.parametrize("race", ["approval_revoked", "image_changed"])
def test_revoke_or_image_change_between_preflight_and_transaction_never_authorizes(race: str) -> None:
    world = make_world()
    store = world["store"]

    def win_race(fake_store: FakeAuthorizeStore) -> None:
        if race == "approval_revoked":
            fake_store.candidate = replace(
                fake_store.candidate,
                delivery=Delivery(DELIVERY_ID, DeliveryState.IN_REVIEW, row_version=5),
                active_approval_id=None,
                approval_revoked=True,
                command=fake_store.candidate.command.cancel(),
            )
        else:
            changed_variant = replace(fake_store.candidate.variant, sha256="e" * 64)
            fake_store.candidate = replace(
                fake_store.candidate,
                variant=changed_variant,
            )

    store.hook_before_transaction = win_race
    result = world["use_case"].execute(request_for(world))

    assert result.execute is False
    assert result.reason == "PREFLIGHT_BLOCKED"
    assert store.executions == []


def test_pause_keeps_delivery_queued() -> None:
    world = make_world(global_pause=True)

    result = world["use_case"].execute(request_for(world))

    assert result.execute is False
    assert result.reason == "PAUSED"
    assert world["store"].candidate.delivery.state is DeliveryState.QUEUED
    assert world["store"].candidate.command.state is CommandState.PENDING


def test_old_epoch_blocks_and_cancels_command() -> None:
    world = make_world()
    store = world["store"]
    store.controls = RuntimeControls(PublishMode.LIVE_MANUAL, "epoch-current")

    result = world["use_case"].execute(request_for(world))

    assert result.execute is False
    assert result.reason == "EPOCH_MISMATCH"
    assert store.candidate.delivery.state is DeliveryState.BLOCKED
    assert store.candidate.command.state is CommandState.CANCELLED
    assert store.blocked_reason == "PF_EPOCH_MISMATCH"


def test_deadline_expires_delivery_and_command() -> None:
    world = make_world(
        now_ms=DEADLINE_MS + 1,
        deadline_at_ms=DEADLINE_MS,
        token_exp_ms=DEADLINE_MS + 60_000,
    )

    result = world["use_case"].execute(request_for(world))

    assert result.execute is False
    assert result.reason == "WINDOW_CLOSED"
    assert world["store"].candidate.delivery.state is DeliveryState.EXPIRED
    assert world["store"].candidate.command.state is CommandState.EXPIRED


def test_local_media_hash_mismatch_blocks_delivery() -> None:
    world = make_world(media_valid=False)

    result = world["use_case"].execute(request_for(world))

    assert result.execute is False
    assert result.reason == "PREFLIGHT_BLOCKED"
    assert world["store"].candidate.delivery.state is DeliveryState.BLOCKED
    assert world["store"].candidate.command.state is CommandState.CANCELLED
    assert world["store"].blocked_reason == "PF_MEDIA_HASH_MISMATCH"


def test_page_a_principal_cannot_authorize_page_b_token() -> None:
    world = make_world()
    page_b = Channel(
        id="channel-synthetic-page-b",
        project_id="venho_hotel",
        environment="test",
        channel_key="fb_venho",
        platform=ChannelPlatform.FACEBOOK,
        remote_account_id="remote-page-synthetic-b",
        name="Page B synthetic",
        enabled=True,
    )
    world["store"].channels[page_b.channel_key] = page_b
    claims_b = EnqueueCommandClaims(
        command_id=COMMAND_ID,
        delivery_id=DELIVERY_ID,
        revision_id=REVISION_ID,
        channel_id=page_b.id,
        remote_account_id=page_b.remote_account_id,
        payload_hash=PAYLOAD_HASH,
        dispatch_epoch="epoch-synthetic-001",
        audience=f"make-route:{page_b.id}",
        expires_at_ms=DEADLINE_MS,
    )
    token_b = world["tokens"].issue(claims_b)

    with pytest.raises(DomainError) as error:
        world["use_case"].execute(request_for(world, token=token_b))

    assert error.value.code in {"ERR_GC2_CAPABILITY_INVALID", "ERR_GC2_FORBIDDEN"}
    assert world["store"].executions == []


def test_media_fetch_failure_is_retryable_without_state_change() -> None:
    world = make_world()
    command = request_for(world)
    command = replace(command, media_report_http_status=404)

    result = world["use_case"].execute(command)

    assert result.execute is False
    assert result.reason == "MEDIA_FETCH_FAILED"
    assert world["store"].candidate.delivery.state is DeliveryState.QUEUED
    assert world["store"].candidate.command.state is CommandState.PENDING


def test_authorize_contract_covers_request_and_response_shapes() -> None:
    schema = json.loads(Path("contracts/growth_engine/authorize.v2.schema.json").read_text())
    request_fixture = {
        "_synthetic": True,
        "note": SYNTHETIC_NOTE,
        "payload": {
            "schema_version": "growth.authorize.v2",
            "command_token": "synthetic-token",
            "payload_hash": PAYLOAD_HASH,
            "media_report": {"http_status": 200, "content_type": "image/jpeg"},
        },
    }
    response_fixture = {
        "schema_version": "growth.authorize.v2",
        "execute": False,
        "reason": "PAUSED",
        "execution_id": None,
        "grant_id": None,
        "grant_expires_at_ms": None,
        "remote_page_id": None,
        "caption": None,
    }

    jsonschema.validate(request_fixture["payload"], schema)
    jsonschema.validate(response_fixture, schema)


def test_internal_authorize_route_requires_execution_scope_and_uses_contract() -> None:
    world = make_world()
    bearer = "synthetic-service-token"
    service_hash = hashlib.sha256(bearer.encode("utf-8")).hexdigest()
    container = SimpleNamespace(
        settings=SimpleNamespace(service_tokens=f"make-fb-hanoi:{service_hash}"),
        authorize_publish=world["use_case"],
    )
    app: FastAPI = create_app(container)
    app.include_router(router)

    with TestClient(app) as client:
        response = client.post(
            "/internal/growth/v2/executions/authorize",
            headers={"Authorization": f"Bearer {bearer}"},
            json={
                "schema_version": "growth.authorize.v2",
                "command_token": world["token"],
                "payload_hash": world["revision"].payload_hash,
                "media_report": {"http_status": 200, "content_type": "image/jpeg"},
            },
        )

    assert response.status_code == 200
    assert response.json()["execute"] is True


def test_internal_authorize_route_rejects_page_a_principal_with_page_b_token() -> None:
    world = make_world()
    bearer = "synthetic-service-token"
    service_hash = hashlib.sha256(bearer.encode("utf-8")).hexdigest()
    container = SimpleNamespace(
        settings=SimpleNamespace(service_tokens=f"make-fb-hanoi:{service_hash}"),
        authorize_publish=world["use_case"],
    )
    app: FastAPI = create_app(container)
    app.include_router(router)
    page_b_claims = EnqueueCommandClaims(
        command_id=COMMAND_ID,
        delivery_id=DELIVERY_ID,
        revision_id=REVISION_ID,
        channel_id="channel-synthetic-page-b",
        remote_account_id="remote-page-synthetic-b",
        payload_hash=world["revision"].payload_hash,
        dispatch_epoch="epoch-synthetic-001",
        audience="make-route:channel-synthetic-page-b",
        expires_at_ms=DEADLINE_MS,
    )
    token_b = world["tokens"].issue(page_b_claims)

    with TestClient(app) as client:
        response = client.post(
            "/internal/growth/v2/executions/authorize",
            headers={"Authorization": f"Bearer {bearer}"},
            json={
                "schema_version": "growth.authorize.v2",
                "command_token": token_b,
                "payload_hash": world["revision"].payload_hash,
                "media_report": {"http_status": 200, "content_type": "image/jpeg"},
            },
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ERR_GC2_CAPABILITY_INVALID"
