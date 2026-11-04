from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pytest

from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.migrator import MigrationRunner
from growth_engine.adapters.outbound.persistence.sqlite.uow import (
    ConcurrencyConflict,
    DatabaseBusy,
    SqliteUnitOfWork,
)
from growth_engine.domain.channels.channel import Channel, ChannelConfig, ChannelPlatform
from growth_engine.domain.content.candidate import CandidateState, ResearchCandidate
from growth_engine.domain.content.package import ContentPackage
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.kernel.hashing import sha256_hex
from growth_engine.domain.media.asset import MediaAsset, MediaVariant, VariantQcStatus
from growth_engine.domain.media.qc import QcDecision, QcReport
from growth_engine.domain.ops.incident import Incident, IncidentSeverity, IncidentState
from growth_engine.domain.publishing.command import OutboxCommand
from growth_engine.domain.publishing.execution import Execution, ExecutionState
from growth_engine.domain.publishing.receipt import Receipt, ReceiptOutcome
from growth_engine.domain.publishing.runtime_mode import PublishMode, RuntimeControls
from growth_engine.domain.scheduling.slot import Slot, SlotTarget


MIGRATIONS = Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")
HASH_A = "a" * 64
HASH_B = "b" * 64


@pytest.fixture

def database_path(tmp_path: Path) -> Path:
    path = tmp_path / "repositories.db"
    connection = connect(path)
    try:
        MigrationRunner(MIGRATIONS).apply(connection, application_version="pytest")
    finally:
        connection.close()
    return path


def _uow(path: Path, **kwargs: object) -> SqliteUnitOfWork:
    return SqliteUnitOfWork(lambda: connect(path), **kwargs)


def test_round_trip_each_persisted_domain_aggregate(database_path: Path) -> None:
    channel = Channel(
        id="channel-a",
        project_id="venho-test",
        environment="test",
        channel_key="fb_hanoi",
        platform=ChannelPlatform.FACEBOOK,
        remote_account_id="synthetic-page-a",
        name="Synthetic Page A",
        enabled=True,
    )
    config = ChannelConfig(
        id="config-a",
        channel_id=channel.id,
        version=1,
        make_route_ref="test-route",
        graph_api_version="v21.0",
        capability={"photos": True, "reels": False},
        caption_profile="hotel-default",
    )
    slot = Slot(
        id="slot-a",
        project_id=channel.project_id,
        local_date=date(2026, 11, 5),
        local_time="09:00",
        timezone="Asia/Ho_Chi_Minh",
        lane="weekly",
        cadence_version="cadence-v2",
        scheduled_at_ms=100,
        deadline_at_ms=200,
    )
    target = SlotTarget("target-a", slot.id, channel.id, required=True)
    package = ContentPackage(
        id="package-a",
        slot_id=slot.id,
        topic_key="topic-a",
        pillar="local_discovery",
        lane="weekly",
        source_snapshot_json='{"source":"synthetic"}',
        fact_snapshot_json="{}",
        fact_snapshot_hash=HASH_A,
        generation_version="generator-v1",
        created_at_ms=1,
    )
    asset = MediaAsset(
        id="asset-a",
        source_type="upload",
        source_ref="synthetic-input",
        source_revision="r1",
        source_sha256=HASH_A,
        original_key="synthetic/original.jpg",
        metadata_json="{}",
        created_at_ms=1,
    )
    variant = MediaVariant(
        id="variant-a",
        asset_id=asset.id,
        transform_version="jpeg-v1",
        sha256=HASH_B,
        object_key="synthetic/variant.jpg",
        width=1200,
        height=900,
        mime="image/jpeg",
        byte_size=4096,
        qc_status=VariantQcStatus.PASS,
        created_at_ms=2,
    )
    qc = QcReport(
        id="qc-a",
        variant_id=variant.id,
        caption_hash=HASH_A,
        ruleset_hash=HASH_B,
        fact_snapshot_hash=HASH_A,
        decision=QcDecision.PASS,
        coverage_gaps=("synthetic-gap",),
        result_json='{"score":100}',
        created_at_ms=3,
    )
    delivery = Delivery(id="delivery-a", state=DeliveryState.DRAFT, row_version=1)
    revision_fields = {
        "delivery_id": delivery.id,
        "revision_id": "revision-a",
        "channel_id": channel.id,
        "remote_account_id": channel.remote_account_id,
        "channel_config_hash": sha256_hex(b"synthetic-config"),
        "caption": "Xin chào 🌿",
        "media": [{"sha256": variant.sha256, "mime": variant.mime, "width": variant.width, "height": variant.height}],
        "scheduled_at_ms": 100,
        "deadline_at_ms": 200,
        "qc_report_id": qc.id,
        "ruleset_hash": qc.ruleset_hash,
        "fact_snapshot_hash": package.fact_snapshot_hash,
    }
    revision = DeliveryRevision.create(revision_fields)
    approval = ApprovalDecision(
        id="approval-a",
        revision_id="revision-a",
        payload_hash=revision.payload_hash,
        decision=ApprovalType.APPROVE,
        actor_id="test-operator",
        created_at_ms=4,
    )
    command = OutboxCommand.new(
        command_id="command-a",
        delivery_id=delivery.id,
        revision_id="revision-a",
        sequence_no=1,
        expires_at_ms=200,
        now_ms=100,
        envelope_token="synthetic-envelope-capability",
    )
    execution = Execution(
        id="execution-a",
        delivery_id=delivery.id,
        command_id=command.id,
        grant_id="grant-a",
        state=ExecutionState.AUTHORIZED,
        grant_expires_at_ms=150,
        receipt_due_at_ms=200,
    )
    receipt = Receipt(
        issuer="synthetic-make",
        event_id="event-a",
        execution_id=execution.id,
        grant_id=execution.grant_id,
        command_id=command.id,
        delivery_id=delivery.id,
        revision_id="revision-a",
        channel_id=channel.id,
        remote_account_id=channel.remote_account_id,
        payload_hash=revision.payload_hash,
        outcome=ReceiptOutcome.OUTCOME_UNKNOWN,
    )
    incident = Incident(
        id="incident-a",
        type="SYNTHETIC_TEST",
        fingerprint="SYNTHETIC_TEST:channel-a:delivery-a",
        channel_id=channel.id,
        ref=delivery.id,
        severity=IncidentSeverity.WARNING,
        state=IncidentState.OPEN,
        first_seen_at_ms=5,
        last_seen_at_ms=6,
        occurrence_count=2,
    )
    controls = RuntimeControls(PublishMode.DRY_RUN, "epoch-test", global_pause=True)
    candidate = ResearchCandidate(
        id="candidate-a",
        project_id=channel.project_id,
        source="local_intel",
        external_key="synthetic-event",
        source_revision="r1",
        event_key=None,
        topic_key="topic-a",
        event_start_at_ms=None,
        event_end_at_ms=None,
        expires_at_ms=300,
        source_hash=HASH_B,
        state=CandidateState.NEW,
    )

    uow = _uow(database_path)
    with uow.begin_immediate() as tx:
        tx.channels.save_channel(channel, created_at_ms=1)
        tx.channels.save_config(config, created_at_ms=2)
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
            created_at_ms=3,
            updated_at_ms=3,
        )
        tx.deliveries.save_revision(
            revision,
            delivery_id=delivery.id,
            channel_id=channel.id,
            revision_no=1,
            channel_config_id=config.id,
            variant_id=variant.id,
            qc_report_id=qc.id,
            scheduled_at_ms=100,
            deadline_at_ms=200,
            caption="Xin chào 🌿",
            created_by="test-operator",
            created_at_ms=3,
        )
        tx.deliveries.save_approval(approval)
        tx.commands.save(
            command,
            payload_hash=revision.payload_hash,
            dispatch_epoch="epoch-test",
            created_at_ms=4,
            updated_at_ms=4,
        )
        tx.executions.save(
            execution,
            principal_id="test-principal",
            authorized_at_ms=110,
            updated_at_ms=110,
        )
        tx.receipts.save(
            receipt,
            receipt_id="receipt-a",
            received_at_ms=120,
            processing_state="QUARANTINED",
        )
        tx.incidents.save(incident, details_json='{"synthetic":true}')
        tx.controls.save(controls, environment="test", policy_version="policy-test", updated_at_ms=1)
        tx.candidates.save(candidate, payload_json='{"synthetic":true}', created_at_ms=1)

    with uow.read_only() as tx:
        assert tx.channels.get_channel(channel.id) == channel
        assert tx.channels.get_config(config.id) == config
        assert tx.slots.get_slot(slot.id) == slot
        assert tx.slots.get_target(target.id) == target
        assert tx.packages.get(package.id) == package
        assert tx.media.get_asset(asset.id) == asset
        assert tx.media.get_variant(variant.id) == variant
        assert tx.qc.get(qc.id) == qc
        assert tx.deliveries.get(delivery.id) == delivery
        assert tx.deliveries.get_revision("revision-a") == revision
        assert tx.deliveries.get_approval(approval.id) == approval
        assert tx.commands.get(command.id, envelope_token=command.envelope_token) == command
        assert tx.executions.get(execution.id) == execution
        assert tx.receipts.get("receipt-a") == receipt
        assert tx.incidents.get(incident.id) == incident
        assert tx.controls.get("test") == controls
        assert tx.candidates.get(candidate.id) == candidate


def test_cas_update_increments_row_version_and_rejects_stale_version(database_path: Path) -> None:
    uow = _uow(database_path)
    slot = Slot(
        "slot-cas", "venho-test", date(2026, 11, 5), "09:00", "Asia/Ho_Chi_Minh",
        "weekly", "v1", 100, 200,
    )
    with uow.begin_immediate() as tx:
        tx.slots.save_slot(slot, created_at_ms=1)
        assert tx.cas_update(
            "slots", slot.id, expected_row_version=1,
            fields={"cancelled_at": 150, "cancel_reason": "operator"},
        ) == 2
    with uow.read_only() as tx:
        saved = tx.slots.get_slot(slot.id)
        assert saved is not None and saved.cancelled_at_ms == 150
    with uow.begin_immediate() as tx:
        with pytest.raises(ConcurrencyConflict):
            tx.cas_update("slots", slot.id, expected_row_version=1, fields={"lane": "new-lane"})


def test_transaction_rolls_back_on_exception_and_read_only_rejects_write(database_path: Path) -> None:
    uow = _uow(database_path)
    channel = Channel(
        "channel-rollback", "venho-test", "test", "fb_rollback", ChannelPlatform.FACEBOOK,
        "synthetic-rollback-page", "Rollback Test",
    )
    with pytest.raises(RuntimeError, match="rollback marker"):
        with uow.begin_immediate() as tx:
            tx.channels.save_channel(channel, created_at_ms=1)
            raise RuntimeError("rollback marker")
    with uow.read_only() as tx:
        assert tx.channels.get_channel(channel.id) is None
        with pytest.raises(sqlite3.OperationalError):
            tx.channels.save_channel(channel, created_at_ms=1)


def test_busy_begin_retries_five_times_then_raises_database_busy(database_path: Path) -> None:
    lock_holder = connect(database_path)
    lock_holder.execute("BEGIN IMMEDIATE")
    backoffs: list[float] = []
    attempts = 0

    def zero_timeout_connection() -> sqlite3.Connection:
        nonlocal attempts
        attempts += 1
        connection = connect(database_path)
        connection.execute("PRAGMA busy_timeout=0")
        return connection

    uow = SqliteUnitOfWork(zero_timeout_connection, sleep=backoffs.append)
    try:
        with pytest.raises(DatabaseBusy):
            with uow.begin_immediate():
                pytest.fail("locked database must not enter transaction")
        assert attempts == 1  # retry BEGIN on one connection, not a new connection
        assert backoffs == [0.02, 0.04, 0.08, 0.16, 0.2]
    finally:
        lock_holder.rollback()
        lock_holder.close()
