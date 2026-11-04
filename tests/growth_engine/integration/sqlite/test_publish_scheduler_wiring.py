from __future__ import annotations

import base64
import hashlib
import multiprocessing
import time
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from growth_engine.adapters.inbound.api.app import create_app
from growth_engine.adapters.inbound.workers.publish_lane import PublishLane
from growth_engine.adapters.outbound.security.capability_tokens import (
    CapabilityTokenManager,
    parse_key_ring,
)
from growth_engine.bootstrap import build_container
from growth_engine.domain.channels.channel import Channel, ChannelConfig, ChannelPlatform, config_hash
from growth_engine.domain.content.package import ContentPackage
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.media.asset import MediaAsset, MediaVariant, VariantQcStatus
from growth_engine.domain.media.qc import QcDecision, QcReport
from growth_engine.domain.publishing.runtime_mode import PublishMode, RuntimeControls
from growth_engine.domain.scheduling.slot import Slot, SlotTarget
from growth_engine.settings import Settings


def test_publish_scheduler_enqueues_and_expires_atomically_in_sqlite(tmp_path: Path) -> None:
    settings = Settings(
        env="test",
        db_path=str(tmp_path / "growth.db"),
        media_root=str(tmp_path / "media"),
        public_base_url="https://growth.example.test",
        capability_keys="synthetic:" + base64.urlsafe_b64encode(b"x" * 32).decode().rstrip("="),
    )
    container = build_container(settings)
    container.migration_service.run(Path(settings.db_path), check=False)
    _seed_approved_delivery(container.uow_factory)

    enqueued = container.enqueue_due.execute(2_000)
    replay = container.enqueue_due.execute(2_000)
    expired = container.expire_overdue.execute(10_001)
    expired_replay = container.expire_overdue.execute(10_001)

    assert enqueued.enqueued_delivery_ids == ("delivery-sqlite",)
    assert replay.enqueued_delivery_ids == ()
    assert expired.expired_delivery_ids == ("delivery-sqlite",)
    assert expired_replay.expired_delivery_ids == ()
    assert isinstance(container.publish_lane, PublishLane)
    with container.uow_factory().read_only() as tx:
        delivery = tx.connection.execute(
            "SELECT state, row_version FROM deliveries WHERE id='delivery-sqlite'"
        ).fetchone()
        command = tx.connection.execute(
            "SELECT state, payload_hash, dispatch_epoch, lease_token FROM outbox_commands "
            "WHERE delivery_id='delivery-sqlite'"
        ).fetchone()
        audit_count = tx.connection.execute(
            "SELECT count(*) FROM audit_events WHERE aggregate_id='delivery-sqlite'"
        ).fetchone()[0]
    assert delivery["state"] == "EXPIRED"
    assert delivery["row_version"] == 3
    assert command["state"] == "EXPIRED"
    assert len(command["payload_hash"]) == 64
    assert command["dispatch_epoch"] == "epoch-test"
    assert command["lease_token"] is None
    assert audit_count == 2


def test_dispatch_store_reissues_same_token_across_rotation_and_ack_redelivery(tmp_path: Path) -> None:
    old_key = base64.urlsafe_b64encode(b"o" * 32).decode().rstrip("=")
    new_key = base64.urlsafe_b64encode(b"n" * 32).decode().rstrip("=")
    settings = Settings(
        env="test",
        db_path=str(tmp_path / "dispatch.db"),
        media_root=str(tmp_path / "media"),
        public_base_url="https://growth.example.test",
        capability_keys=f"old:{old_key}",
        make_webhook_urls={"PAGE_A": "https://hooks.example.test/route"},
    )
    container = build_container(settings)
    container.migration_service.run(Path(settings.db_path), check=False)
    _seed_approved_delivery(container.uow_factory, deadline_at_ms=1_000_000)
    container.enqueue_due.execute(2_000)

    with container.uow_factory().read_only() as tx:
        row = tx.connection.execute(
            "SELECT id, revision_id, payload_hash, dispatch_epoch, expires_at, signing_key_id "
            "FROM outbox_commands WHERE delivery_id='delivery-sqlite'"
        ).fetchone()
    assert row["signing_key_id"] == "old"
    rotated = build_container(
        Settings(
            env="test",
            db_path=settings.db_path,
            media_root=settings.media_root,
            public_base_url=settings.public_base_url,
            capability_keys=f"new:{new_key},old:{old_key}",
            make_webhook_urls={"PAGE_A": "https://hooks.example.test/route"},
        )
    )
    token_manager = CapabilityTokenManager(parse_key_ring(f"new:{new_key},old:{old_key}"))
    claims = _TokenClaims(
        command_id=row["id"],
        revision_id=row["revision_id"],
        channel_id="channel-test-fb",
        payload_hash=row["payload_hash"],
        dispatch_epoch=row["dispatch_epoch"],
        audience="make-route:channel-test-fb",
        expires_at_ms=row["expires_at"],
    )
    stable_token = token_manager.issue(claims, key_id="old")
    policy = rotated.publishing_policy
    first = rotated.dispatch_store.claim_due(
        2_000, 10, owner="synthetic-worker-1", lease_ms=30_000, policy=policy
    )
    assert len(first) == 1
    assert first[0].route_ref == "https://hooks.example.test/route"
    assert first[0].command.envelope_token == stable_token
    retry_command = first[0].command.transport_failed(at_ms=2_000, rng=lambda low, high: 0.5)
    assert rotated.dispatch_store.complete_retry(first[0], retry_command, at_ms=2_000)
    assert rotated.dispatch_store.claim_due(
        2_000, 10, owner="synthetic-worker-1", lease_ms=30_000, policy=policy
    ) == ()
    second = rotated.dispatch_store.claim_due(
        retry_command.next_attempt_at_ms,
        10,
        owner="synthetic-worker-2",
        lease_ms=30_000,
        policy=policy,
    )
    assert len(second) == 1
    assert second[0].command.envelope_token == stable_token
    assert rotated.dispatch_store.complete_ack(second[0], at_ms=retry_command.next_attempt_at_ms)
    ack_at = retry_command.next_attempt_at_ms
    policy = rotated.publishing_policy
    assert rotated.dispatch_store.claim_due(
        ack_at + policy.redeliver_after_ack_minutes * 60_000 - 1,
        10,
        owner="synthetic-worker-3",
        lease_ms=30_000,
        policy=policy,
    ) == ()
    third = rotated.dispatch_store.claim_due(
        ack_at + policy.redeliver_after_ack_minutes * 60_000,
        10,
        owner="synthetic-worker-3",
        lease_ms=30_000,
        policy=policy,
    )
    assert len(third) == 1
    assert third[0].command.envelope_token == stable_token


def test_dispatch_store_reclaims_expired_lease_and_fences_stale_ack(tmp_path: Path) -> None:
    encoded = base64.urlsafe_b64encode(b"l" * 32).decode().rstrip("=")
    settings = Settings(
        env="test",
        db_path=str(tmp_path / "lease.db"),
        media_root=str(tmp_path / "media"),
        public_base_url="https://growth.example.test",
        capability_keys=f"lease:{encoded}",
        make_webhook_urls={"PAGE_A": "https://hooks.example.test/route"},
    )
    container = build_container(settings)
    container.migration_service.run(Path(settings.db_path), check=False)
    _seed_approved_delivery(container.uow_factory, deadline_at_ms=1_000_000)
    container.enqueue_due.execute(2_000)

    first = container.dispatch_store.claim_due(
        2_000, 1, owner="lease-worker-a", lease_ms=100, policy=container.publishing_policy
    )[0]
    second = container.dispatch_store.claim_due(
        2_100, 1, owner="lease-worker-b", lease_ms=100, policy=container.publishing_policy
    )[0]
    assert first.lease_token != second.lease_token
    assert not container.dispatch_store.complete_ack(first, at_ms=2_101)
    assert container.dispatch_store.complete_ack(second, at_ms=2_101)
    with container.uow_factory().read_only() as tx:
        row = tx.connection.execute(
            "SELECT state, lease_token, acked_at, next_attempt_at FROM outbox_commands "
            "WHERE delivery_id='delivery-sqlite'"
        ).fetchone()
    assert row["state"] == "ACKED"
    assert row["lease_token"] is None
    assert row["acked_at"] == 2_101
    assert row["next_attempt_at"] == 2_101 + 5 * 60_000


def test_authorize_router_commits_real_sqlite_execution_and_audit(tmp_path: Path) -> None:
    bearer = "synthetic-authorize-bearer"
    now_ms = time.time_ns() // 1_000_000
    key_config = "authorize:" + base64.urlsafe_b64encode(b"a" * 32).decode().rstrip("=")
    settings = Settings(
        env="test",
        db_path=str(tmp_path / "authorize.db"),
        media_root=str(tmp_path / "media"),
        public_base_url="https://growth.example.test",
        capability_keys=key_config,
        service_tokens=f"make-fb-hanoi:{hashlib.sha256(bearer.encode()).hexdigest()}",
        make_webhook_urls={"PAGE_A": "https://hooks.example.test/route"},
    )
    container = build_container(settings)
    container.migration_service.run(Path(settings.db_path), check=False)
    _seed_approved_delivery(
        container.uow_factory,
        deadline_at_ms=now_ms + 600_000,
        media_root=Path(settings.media_root),
    )
    container.enqueue_due.execute(now_ms)
    lease = container.dispatch_store.claim_due(
        now_ms,
        1,
        owner="authorize-integration",
        lease_ms=30_000,
        policy=container.publishing_policy,
    )[0]

    response = TestClient(create_app(container)).post(
        "/internal/growth/v2/executions/authorize",
        headers={"Authorization": f"Bearer {bearer}"},
        json={
            "schema_version": "growth.authorize.v2",
            "command_token": lease.command.envelope_token,
            "payload_hash": lease.payload_hash,
            "media_report": {"http_status": 200, "content_type": "image/jpeg"},
        },
    )
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["execute"] is True
    assert body["remote_page_id"] == "synthetic-page"
    assert body["caption"] == "Synthetic approved caption"
    with container.uow_factory().read_only() as tx:
        delivery = tx.connection.execute(
            "SELECT state FROM deliveries WHERE id='delivery-sqlite'"
        ).fetchone()
        command = tx.connection.execute(
            "SELECT state, lease_token FROM outbox_commands WHERE delivery_id='delivery-sqlite'"
        ).fetchone()
        executions = tx.connection.execute(
            "SELECT state, grant_id FROM executions WHERE delivery_id='delivery-sqlite'"
        ).fetchall()
        audit = tx.connection.execute(
            "SELECT action FROM audit_events WHERE aggregate_id='delivery-sqlite'"
        ).fetchall()
    assert delivery["state"] == "EXECUTING"
    assert command["state"] == "AUTHORIZED" and command["lease_token"] is None
    assert len(executions) == 1 and executions[0]["state"] == "AUTHORIZED"
    assert [row["action"] for row in audit].count("publish.command_authorized") == 1


def _authorize_process_worker(
    database_path,
    media_root,
    key_config,
    service_tokens,
    command_token,
    payload_hash,
    barrier,
    results,
) -> None:
    from growth_engine.application.publishing.authorize_publish import AuthorizePublishCommand

    try:
        container = build_container(
            Settings(
                env="test",
                db_path=database_path,
                media_root=media_root,
                public_base_url="https://growth.example.test",
                capability_keys=key_config,
                service_tokens=service_tokens,
            )
        )
        barrier.wait(timeout=20)
        result = container.authorize_publish.execute(
            AuthorizePublishCommand(
                command_token=command_token,
                payload_hash=payload_hash,
                media_report_http_status=200,
                media_report_content_type="image/jpeg",
                principal_id="make-fb-hanoi",
                principal_channel_key="fb_hanoi",
                correlation_id="authorize-race-synthetic",
            )
        )
        results.put((result.execute, result.reason))
    except BaseException as error:
        results.put(("ERROR", type(error).__name__))
        raise


def test_two_processes_authorize_one_delivery_once(tmp_path: Path) -> None:
    bearer = "synthetic-race-bearer"
    service_tokens = f"make-fb-hanoi:{hashlib.sha256(bearer.encode()).hexdigest()}"
    key_config = "race:" + base64.urlsafe_b64encode(b"r" * 32).decode().rstrip("=")
    now_ms = time.time_ns() // 1_000_000
    settings = Settings(
        env="test",
        db_path=str(tmp_path / "authorize-race.db"),
        media_root=str(tmp_path / "race-media"),
        public_base_url="https://growth.example.test",
        capability_keys=key_config,
        service_tokens=service_tokens,
        make_webhook_urls={"PAGE_A": "https://hooks.example.test/route"},
    )
    container = build_container(settings)
    container.migration_service.run(Path(settings.db_path), check=False)
    _seed_approved_delivery(
        container.uow_factory,
        deadline_at_ms=now_ms + 600_000,
        media_root=Path(settings.media_root),
    )
    container.enqueue_due.execute(now_ms)
    lease = container.dispatch_store.claim_due(
        now_ms,
        1,
        owner="authorize-race-setup",
        lease_ms=30_000,
        policy=container.publishing_policy,
    )[0]

    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    results = context.Queue()
    processes = [
        context.Process(
            target=_authorize_process_worker,
            args=(
                settings.db_path,
                settings.media_root,
                key_config,
                service_tokens,
                lease.command.envelope_token,
                lease.payload_hash,
                barrier,
                results,
            ),
        )
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    outcomes = [results.get(timeout=30) for _ in processes]
    for process in processes:
        process.join(timeout=30)
        assert process.exitcode == 0
    results.close()
    results.join_thread()
    assert outcomes.count((True, None)) == 1
    assert outcomes.count((False, "ALREADY_AUTHORIZED")) == 1
    with container.uow_factory().read_only() as tx:
        count = tx.connection.execute(
            "SELECT count(*) FROM executions WHERE delivery_id='delivery-sqlite'"
        ).fetchone()[0]
    assert count == 1


def test_receipt_api_persists_full_sanitized_body_and_applies_from_sqlite(tmp_path: Path) -> None:
    container, settings, lease, grant, bearer, now_ms = _make_authorized_container(tmp_path)
    body = _make_receipt_body(lease, grant, now_ms)
    response = TestClient(create_app(container)).post(
        "/internal/growth/v2/receipts",
        headers={"Authorization": f"Bearer {bearer}"},
        json=body,
    )
    assert response.status_code == 200, response.json()
    receipt_id = response.json()["receipt_id"]

    with container.uow_factory().read_only() as tx:
        row = tx.connection.execute(
            "SELECT event_hash, body_json, processing_state FROM receipt_inbox WHERE id=?",
            (receipt_id,),
        ).fetchone()
        apply_jobs = tx.connection.execute(
            "SELECT count(*) FROM jobs WHERE kind='apply_receipt' AND state='PENDING'"
        ).fetchone()[0]
    persisted = __import__("json").loads(row["body_json"])
    assert row["processing_state"] == "RECEIVED"
    assert len(row["event_hash"]) == 64
    assert persisted["failed_step"] is None
    assert persisted["permalink"] == body["permalink"]
    assert apply_jobs == 1

    claim_now_ms = time.time_ns() // 1_000_000 + 1_000
    claimed = container.receipt_store.claim_apply_jobs(claim_now_ms)
    assert len(claimed) == 1
    job_id, lease_token, queued_receipt_id, correlation_id = claimed[0]
    applied = container.apply_receipt.execute(
        queued_receipt_id, correlation_id=correlation_id
    )
    assert applied.processing_state == "APPLIED"
    assert container.receipt_store.complete_apply_job(
        job_id, lease_token, at_ms=claim_now_ms
    )
    with container.uow_factory().read_only() as tx:
        receipt = tx.connection.execute(
            "SELECT processing_state FROM receipt_inbox WHERE id=?", (receipt_id,)
        ).fetchone()
        execution = tx.connection.execute(
            "SELECT state, external_outcome FROM executions WHERE delivery_id='delivery-sqlite'"
        ).fetchone()
        delivery = tx.connection.execute(
            "SELECT state, platform_post_id, permalink FROM deliveries WHERE id='delivery-sqlite'"
        ).fetchone()
        verify_jobs = tx.connection.execute(
            "SELECT count(*) FROM jobs WHERE kind='verify_publication'"
        ).fetchone()[0]
    assert receipt["processing_state"] == "APPLIED"
    assert execution["state"] == "REPORTED"
    assert delivery["state"] == "REPORTED_PUBLISHED"
    assert delivery["platform_post_id"] == "post-synthetic-001"
    assert delivery["permalink"] == body["permalink"]
    assert verify_jobs == 1


def test_two_processes_deduplicate_the_same_receipt(tmp_path: Path) -> None:
    container, settings, lease, grant, _bearer, now_ms = _make_authorized_container(tmp_path)
    body = _make_receipt_body(lease, grant, now_ms)
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    results = context.Queue()
    processes = [
        context.Process(
            target=_receive_receipt_process_worker,
            args=(settings.db_path, settings.media_root, body, barrier, results),
        )
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    outcomes = [results.get(timeout=30) for _ in processes]
    for process in processes:
        process.join(timeout=30)
        assert process.exitcode == 0
    results.close()
    results.join_thread()
    assert len({item[0] for item in outcomes}) == 1
    assert sorted(item[1] for item in outcomes) == [False, True]
    with container.uow_factory().read_only() as tx:
        counts = tx.connection.execute(
            "SELECT (SELECT count(*) FROM receipt_inbox), "
            "(SELECT count(*) FROM jobs WHERE kind='apply_receipt')"
        ).fetchone()
    assert tuple(counts) == (1, 1)


def test_sqlite_receipt_timeout_marks_unknown_once(tmp_path: Path) -> None:
    container, _settings, _lease, _grant, _bearer, now_ms = _make_authorized_container(tmp_path)
    with container.uow_factory().begin_immediate() as tx:
        tx.connection.execute(
            "UPDATE executions SET authorized_at=?, grant_expires_at=?, receipt_due_at=? "
            "WHERE delivery_id='delivery-sqlite'",
            (now_ms - 60_000, now_ms - 30_000, now_ms - 1),
        )

    first = container.watch_receipt_timeouts.execute()
    second = container.watch_receipt_timeouts.execute()
    assert first.timed_out == 1
    assert second.timed_out == 0
    with container.uow_factory().read_only() as tx:
        execution = tx.connection.execute(
            "SELECT state FROM executions WHERE delivery_id='delivery-sqlite'"
        ).fetchone()
        delivery = tx.connection.execute(
            "SELECT state FROM deliveries WHERE id='delivery-sqlite'"
        ).fetchone()
        incidents = tx.connection.execute(
            "SELECT count(*) FROM incidents WHERE type='UNKNOWN'"
        ).fetchone()[0]
    assert execution["state"] == "UNKNOWN"
    assert delivery["state"] == "UNKNOWN"
    assert incidents == 1


def _make_authorized_container(tmp_path: Path):
    bearer = "synthetic-receipt-bearer"
    now_ms = time.time_ns() // 1_000_000
    key_config = "receipt:" + base64.urlsafe_b64encode(b"t" * 32).decode().rstrip("=")
    settings = Settings(
        env="test",
        db_path=str(tmp_path / "receipt.db"),
        media_root=str(tmp_path / "receipt-media"),
        public_base_url="https://growth.example.test",
        capability_keys=key_config,
        service_tokens=f"make-fb-hanoi:{hashlib.sha256(bearer.encode()).hexdigest()}",
        make_webhook_urls={"PAGE_A": "https://hooks.example.test/route"},
    )
    container = build_container(settings)
    container.migration_service.run(Path(settings.db_path), check=False)
    _seed_approved_delivery(
        container.uow_factory,
        deadline_at_ms=now_ms + 600_000,
        media_root=Path(settings.media_root),
    )
    container.enqueue_due.execute(now_ms)
    lease = container.dispatch_store.claim_due(
        now_ms, 1, owner="receipt-test-setup", lease_ms=30_000,
        policy=container.publishing_policy,
    )[0]
    from growth_engine.application.publishing.authorize_publish import AuthorizePublishCommand

    grant = container.authorize_publish.execute(
        AuthorizePublishCommand(
            command_token=lease.command.envelope_token,
            payload_hash=lease.payload_hash,
            media_report_http_status=200,
            media_report_content_type="image/jpeg",
            principal_id="make-fb-hanoi",
            principal_channel_key="fb_hanoi",
            correlation_id="receipt-authorize-synthetic",
        )
    )
    assert grant.execute
    return container, settings, lease, grant, bearer, now_ms


def _make_receipt_body(lease, grant, now_ms: int) -> dict[str, object]:
    return {
        "schema_version": "growth.receipt.v2",
        "event_id": f"{grant.grant_id}:POST_CREATED",
        "command_id": lease.command.id,
        "execution_id": grant.execution_id,
        "grant_id": grant.grant_id,
        "delivery_id": lease.command.delivery_id,
        "revision_id": lease.command.revision_id,
        "channel_id": lease.channel_id,
        "remote_page_id": lease.remote_page_id,
        "payload_hash": lease.payload_hash,
        "outcome": "POST_CREATED",
        "platform_post_id": "post-synthetic-001",
        "permalink": "https://facebook.com/posts/synthetic",
        "failed_step": None,
        "error": None,
        "occurred_at_ms": now_ms + 1,
    }


def _receive_receipt_process_worker(database_path, media_root, body, barrier, results) -> None:
    from growth_engine.application.publishing.receive_receipt import ReceiveReceiptCommand

    container = build_container(
        Settings(
            env="test",
            db_path=database_path,
            media_root=media_root,
            public_base_url="https://growth.example.test",
        )
    )
    barrier.wait(timeout=20)
    result = container.receive_receipt.execute(
        ReceiveReceiptCommand(
            issuer_id="make-fb-hanoi",
            body=body,
            correlation_id="receipt-race-synthetic",
        )
    )
    results.put((result.receipt_id, result.duplicate))


def _seed_approved_delivery(
    uow_factory,
    *,
    deadline_at_ms: int = 10_000,
    media_root: Path | None = None,
) -> None:
    media_bytes = b"synthetic image bytes"
    media_sha = hashlib.sha256(media_bytes).hexdigest()
    media_key = f"variants/{media_sha[:2]}/{media_sha}.jpg"
    fact_hash = hashlib.sha256(b"{}").hexdigest()
    if media_root is not None:
        from growth_engine.adapters.outbound.media.local_store import LocalMediaStore

        media_key = LocalMediaStore(media_root).put_variant(media_bytes, media_sha)
    channel = Channel(
        id="channel-test-fb",
        project_id="venho_hotel",
        environment="test",
        channel_key="fb_hanoi",
        platform=ChannelPlatform.FACEBOOK,
        remote_account_id="synthetic-page",
        name="Synthetic Page",
        enabled=True,
    )
    config = ChannelConfig(
        id="config-test-fb",
        channel_id=channel.id,
        version=1,
        make_route_ref="GE_MAKE_WEBHOOK_URL_PAGE_A",
        graph_api_version="vNN.N",
        capability={"_synthetic": True, "note": "cần thay bằng fixture thật từ P0-T03/P0-T04"},
    )
    slot = Slot(
        "slot-sqlite", "venho_hotel", date(2026, 11, 4), "09:00", "Asia/Ho_Chi_Minh",
        "weekly", "cadence-v2", 1_000, deadline_at_ms,
    )
    target = SlotTarget("target-sqlite", slot.id, channel.id)
    package = ContentPackage(
        id="package-sqlite",
        slot_id=slot.id,
        topic_key="synthetic-topic",
        pillar="local_discovery",
        lane="weekly",
        source_snapshot_json='{"_synthetic":true}',
        fact_snapshot_json="{}",
        fact_snapshot_hash=fact_hash,
        generation_version="synthetic-v1",
        created_at_ms=1,
    )
    asset = MediaAsset(
        id="asset-sqlite",
        source_type="upload",
        source_ref="synthetic",
        source_revision="r1",
        source_sha256=media_sha,
        original_key="synthetic/original.jpg",
        metadata_json="{}",
        created_at_ms=1,
    )
    variant = MediaVariant(
        id="variant-sqlite",
        asset_id=asset.id,
        transform_version="synthetic-v1",
        sha256=media_sha,
        object_key=media_key,
        width=1080,
        height=1350,
        mime="image/jpeg",
        byte_size=1024,
        qc_status=VariantQcStatus.PASS,
        created_at_ms=1,
    )
    qc = QcReport(
        id="qc-sqlite",
        variant_id=variant.id,
        caption_hash=hashlib.sha256(b"Synthetic approved caption").hexdigest(),
        ruleset_hash="e" * 64,
        fact_snapshot_hash=package.fact_snapshot_hash,
        decision=QcDecision.PASS,
        coverage_gaps=(),
        result_json='{"_synthetic":true}',
        created_at_ms=1,
    )
    revision = DeliveryRevision.create(
        {
            "delivery_id": "delivery-sqlite",
            "revision_id": "revision-sqlite",
            "channel_id": channel.id,
            "remote_account_id": channel.remote_account_id,
            "channel_config_hash": config_hash(config),
            "caption": "Synthetic approved caption",
            "media": [{"sha256": variant.sha256, "mime": variant.mime, "width": 1080, "height": 1350}],
            "scheduled_at_ms": 1_000,
            "deadline_at_ms": deadline_at_ms,
            "qc_report_id": qc.id,
            "ruleset_hash": qc.ruleset_hash,
            "fact_snapshot_hash": package.fact_snapshot_hash,
        }
    )
    approval = ApprovalDecision(
        id="approval-sqlite",
        revision_id="revision-sqlite",
        payload_hash=revision.payload_hash,
        decision=ApprovalType.APPROVE,
        actor_id="synthetic-editor",
        created_at_ms=1,
    )
    delivery = Delivery("delivery-sqlite", DeliveryState.APPROVED)
    controls = RuntimeControls(PublishMode.LIVE_MANUAL, "epoch-test")
    with uow_factory().begin_immediate() as tx:
        tx.channels.save_channel(channel, created_at_ms=1)
        tx.channels.save_config(config, created_at_ms=1)
        tx.slots.save_slot(slot, created_at_ms=1)
        tx.slots.save_target(target)
        tx.packages.save(package)
        tx.media.save_asset(asset)
        tx.media.save_variant(variant)
        tx.qc.save(qc)
        tx.deliveries.save(
            delivery,
            target_id=target.id,
            channel_id=channel.id,
            package_id=package.id,
            created_at_ms=1,
            updated_at_ms=1,
            current_revision_id=revision.payload["revision_id"],
            active_approval_id=approval.id,
        )
        tx.deliveries.save_revision(
            revision,
            delivery_id=delivery.id,
            channel_id=channel.id,
            revision_no=1,
            channel_config_id=config.id,
            variant_id=variant.id,
            qc_report_id=qc.id,
            scheduled_at_ms=1_000,
            deadline_at_ms=deadline_at_ms,
            caption="Synthetic approved caption",
            created_by="synthetic-editor",
            created_at_ms=1,
        )
        tx.deliveries.save_approval(approval)
        tx.controls.save(
            controls,
            environment="test",
            policy_version="synthetic-v1",
            updated_at_ms=1,
        )


class _TokenClaims:
    def __init__(self, **values) -> None:
        for name, value in values.items():
            setattr(self, name, value)
