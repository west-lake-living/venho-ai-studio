from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pytest
from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner
from growth_engine.adapters.outbound.persistence.sqlite.review_store import SqliteReviewStore, _asset_label
from growth_engine.adapters.outbound.persistence.sqlite.uow import SqliteUnitOfWork
from growth_engine.application.review.build_review_snapshot import BuildReviewSnapshot
from growth_engine.application.review.create_revision import CreateRevision, RevisionDraft
from growth_engine.domain.channels.channel import Channel, ChannelConfig, ChannelPlatform
from growth_engine.domain.content.package import ContentPackage
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.kernel.hashing import sha256_hex
from growth_engine.domain.media.asset import MediaAsset, MediaVariant, VariantQcStatus
from growth_engine.domain.media.qc import QcDecision, QcReport
from growth_engine.domain.scheduling.slot import Slot, SlotTarget
from tests.growth_engine.support.fakes import FakeClock, SeqIds


def _fixture(tmp_path: Path, *, queued_authorized: bool = False):
    database = tmp_path / "review.sqlite"
    connection = connect(database)
    try:
        MigrationRunner(Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")).apply(
            connection, application_version="revision-store-integration"
        )
    finally:
        connection.close()
    uow_factory = lambda: SqliteUnitOfWork(lambda: connect(database), sleep=lambda _: None)
    channel = Channel(
        "channel-synthetic", "venho_hotel", "test", "fb_hanoi", ChannelPlatform.FACEBOOK,
        "synthetic-page-id", "Synthetic Hanoi", enabled=True,
    )
    config = ChannelConfig(
        "config-synthetic", channel.id, 1, "SYNTHETIC_ROUTE", "vNN.N",
        {"_synthetic": True, "note": "cần thay bằng fixture thật từ P0-T03/P0-T04"},
    )
    slot = Slot("slot-synthetic", "venho_hotel", date(2026, 11, 5), "09:00", "Asia/Ho_Chi_Minh",
                "regular", "cadence-v2", 1_000, 10_000)
    target = SlotTarget("target-synthetic", slot.id, channel.id)
    facts_hash = sha256_hex(b"{}")
    package = ContentPackage(
        "package-synthetic", slot.id, "topic-synthetic", "west_lake_life", "regular",
        '{"_synthetic":true}', "{}", facts_hash, "synthetic-v1", 1,
    )
    original_bytes = b"synthetic-original"
    asset_hash = sha256_hex(original_bytes)
    asset = MediaAsset(
        "asset-synthetic", "upload", "synthetic-source", "r1", asset_hash,
        "originals/synthetic.jpg", '{"_synthetic":true}', 1,
    )
    variant_a = _variant("variant-a", asset.id, b"synthetic-variant-a", VariantQcStatus.PASS)
    variant_b = _variant("variant-b", asset.id, b"synthetic-variant-b", VariantQcStatus.PASS)
    caption_a = "Synthetic approved caption"
    caption_b = "Synthetic edited caption"
    qc_a = _qc("qc-a", variant_a, caption_a, facts_hash)
    qc_b = _qc("qc-b", variant_b, caption_b, facts_hash)
    revision_a = DeliveryRevision.create(
        {
            "delivery_id": "delivery-synthetic", "revision_id": "revision-a",
            "channel_id": channel.id, "remote_account_id": channel.remote_account_id,
            "channel_config_hash": _config_hash(config), "caption": caption_a,
            "media": [{"sha256": variant_a.sha256, "mime": "image/jpeg", "width": 1080, "height": 1350}],
            "scheduled_at_ms": slot.scheduled_at_ms, "deadline_at_ms": slot.deadline_at_ms,
            "qc_report_id": qc_a.id, "ruleset_hash": qc_a.ruleset_hash,
            "fact_snapshot_hash": facts_hash,
        }
    )
    approval = ApprovalDecision(
        "approval-a", "revision-a", revision_a.payload_hash, ApprovalType.APPROVE,
        "synthetic-operator", 1,
    )
    state = DeliveryState.QUEUED if queued_authorized else DeliveryState.APPROVED
    delivery = Delivery("delivery-synthetic", state, row_version=4)
    with uow_factory().begin_immediate() as tx:
        tx.channels.save_channel(channel, created_at_ms=1)
        tx.channels.save_config(config, created_at_ms=1)
        tx.slots.save_slot(slot, created_at_ms=1)
        tx.slots.save_target(target)
        tx.packages.save(package)
        tx.media.save_asset(asset)
        tx.media.save_variant(variant_a)
        tx.media.save_variant(variant_b)
        tx.qc.save(qc_a)
        tx.qc.save(qc_b)
        tx.deliveries.save(
            delivery, target_id=target.id, channel_id=channel.id, package_id=package.id,
            created_at_ms=1, updated_at_ms=1,
            current_revision_id="revision-a", active_approval_id=approval.id,
        )
        tx.deliveries.save_revision(
            revision_a, delivery_id=delivery.id, channel_id=channel.id, revision_no=1,
            channel_config_id=config.id, variant_id=variant_a.id, qc_report_id=qc_a.id,
            scheduled_at_ms=slot.scheduled_at_ms, deadline_at_ms=slot.deadline_at_ms,
            caption=caption_a, created_by="synthetic-operator", created_at_ms=1,
        )
        tx.deliveries.save_approval(approval)
        if queued_authorized:
            tx.connection.execute(
                """INSERT INTO outbox_commands
                   (id, delivery_id, revision_id, sequence_no, kind, business_key, payload_hash,
                    state, dispatch_epoch, expires_at, next_attempt_at, created_at, updated_at)
                   VALUES ('command-synthetic','delivery-synthetic','revision-a',1,'PUBLISH',
                    'publish:synthetic','%s','AUTHORIZED','epoch-test',10000,1,1,1)"""
                % revision_a.payload_hash
            )
            tx.connection.execute(
                """INSERT INTO executions
                   (id, command_id, delivery_id, principal_id, state, grant_id, authorized_at,
                    grant_expires_at, receipt_due_at, updated_at)
                   VALUES ('execution-synthetic','command-synthetic','delivery-synthetic',
                    'synthetic-principal','AUTHORIZED','grant-synthetic',2,3000,4000,2)"""
            )
    return database, uow_factory, slot, variant_b, caption_b, revision_a


def _variant(identifier: str, asset_id: str, body: bytes, status: VariantQcStatus) -> MediaVariant:
    digest = sha256_hex(body)
    return MediaVariant(
        identifier, asset_id, "synthetic-v1", digest, f"variants/{digest[:2]}/{digest}.jpg",
        1080, 1350, "image/jpeg", len(body), status, 1,
    )


def _qc(identifier: str, variant: MediaVariant, caption: str, facts_hash: str) -> QcReport:
    return QcReport(
        identifier, variant.id, hashlib.sha256(caption.encode()).hexdigest(), "e" * 64,
        facts_hash, QcDecision.PASS, (), '{"_synthetic":true}', 1,
    )


def _config_hash(config: ChannelConfig) -> str:
    from growth_engine.domain.channels.channel import config_hash

    return config_hash(config)


def test_sqlite_revision_write_revokes_approval_and_queues_review_atomically(tmp_path: Path) -> None:
    _, uow_factory, _, variant_b, caption_b, old_revision = _fixture(tmp_path)
    clock = FakeClock(2_000)
    store = SqliteReviewStore(uow_factory, SeqIds("review"), clock)
    result = CreateRevision(store, clock, SeqIds("revision")).execute(
        "delivery-synthetic", expected_row_version=4,
        draft=RevisionDraft(caption=caption_b, variant_id=variant_b.id), actor="synthetic-editor",
    )

    assert result.delivery_state is DeliveryState.IN_REVIEW
    assert result.row_version == 5
    assert result.revision.payload["media"][0]["sha256"] == variant_b.sha256
    with uow_factory().read_only() as tx:
        delivery = tx.connection.execute(
            "SELECT state, row_version, current_revision_id, active_approval_id FROM deliveries WHERE id=?",
            (result.delivery_id,),
        ).fetchone()
        revisions = tx.connection.execute(
            "SELECT revision_no, variant_id, qc_report_id FROM delivery_revisions WHERE delivery_id=? ORDER BY revision_no",
            (result.delivery_id,),
        ).fetchall()
        approvals = tx.connection.execute(
            "SELECT decision, revision_id, revokes_id FROM approval_decisions ORDER BY created_at, id"
        ).fetchall()
        job = tx.connection.execute(
            "SELECT kind, lane, payload_json FROM jobs WHERE business_key=?",
            (f"notify:review:{result.delivery_id}:{result.revision.payload['revision_id']}",),
        ).fetchone()
        audit = tx.connection.execute(
            "SELECT action, before_hash, after_hash FROM audit_events WHERE aggregate_id=?",
            (result.delivery_id,),
        ).fetchone()
    assert (delivery["state"], delivery["row_version"], delivery["active_approval_id"]) == (
        "IN_REVIEW", 5, None,
    )
    assert delivery["current_revision_id"] == result.revision.payload["revision_id"]
    assert [(row["revision_no"], row["variant_id"]) for row in revisions] == [
        (1, "variant-a"), (2, "variant-b")
    ]
    assert [row["decision"] for row in approvals] == ["APPROVE", "REVOKE"]
    assert approvals[1]["revision_id"] == "revision-a" and approvals[1]["revokes_id"] == "approval-a"
    assert (job["kind"], job["lane"]) == ("notify", "publish")
    assert audit["action"] == "CREATE_REVISION"
    assert audit["before_hash"] == old_revision.payload_hash
    assert audit["after_hash"] == result.revision.payload_hash

    snapshot = BuildReviewSnapshot(
        store, preview_url_builder=lambda digest: f"https://preview.example/{digest}"
    ).execute(result.delivery_id)
    assert snapshot.preview_sha256 == variant_b.sha256
    assert snapshot.preview_url == f"https://preview.example/{variant_b.sha256}"
    assert snapshot.caption == caption_b
    assert snapshot.row_version == 5


def test_sqlite_revision_refuses_authorized_execution_without_writes(tmp_path: Path) -> None:
    _, uow_factory, _, variant_b, caption_b, _ = _fixture(tmp_path, queued_authorized=True)
    clock = FakeClock(2_000)
    store = SqliteReviewStore(uow_factory, SeqIds("review"), clock)

    with pytest.raises(DomainError) as caught:
        CreateRevision(store, clock, SeqIds("revision")).execute(
            "delivery-synthetic", expected_row_version=4,
            draft=RevisionDraft(caption=caption_b, variant_id=variant_b.id), actor="synthetic-editor",
        )
    assert caught.value.code == ErrorCode.ALREADY_AUTHORIZED.value

    with uow_factory().read_only() as tx:
        delivery = tx.connection.execute(
            "SELECT state, row_version, current_revision_id FROM deliveries WHERE id=?",
            ("delivery-synthetic",),
        ).fetchone()
        assert tx.connection.execute(
            "SELECT count(*) FROM delivery_revisions WHERE delivery_id=?", ("delivery-synthetic",)
        ).fetchone()[0] == 1
    assert (delivery["state"], delivery["row_version"], delivery["current_revision_id"]) == (
        "QUEUED", 4, "revision-a",
    )


def test_review_store_labels_fallback_assets() -> None:
    assert _asset_label('{"option_id":"FALLBACK"}') == "Ảnh dự phòng"
    assert _asset_label('{"option_id":"A"}') is None
