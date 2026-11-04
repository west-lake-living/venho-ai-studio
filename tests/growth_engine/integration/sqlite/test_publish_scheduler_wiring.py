from __future__ import annotations

import base64
from datetime import date
from pathlib import Path

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


def _seed_approved_delivery(uow_factory, *, deadline_at_ms: int = 10_000) -> None:
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
        fact_snapshot_hash="b" * 64,
        generation_version="synthetic-v1",
        created_at_ms=1,
    )
    asset = MediaAsset(
        id="asset-sqlite",
        source_type="upload",
        source_ref="synthetic",
        source_revision="r1",
        source_sha256="c" * 64,
        original_key="synthetic/original.jpg",
        metadata_json="{}",
        created_at_ms=1,
    )
    variant = MediaVariant(
        id="variant-sqlite",
        asset_id=asset.id,
        transform_version="synthetic-v1",
        sha256="a" * 64,
        object_key="synthetic/variant.jpg",
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
        caption_hash="d" * 64,
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
