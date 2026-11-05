from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.adapters.outbound.persistence.sqlite.review_workflows import (
    SqliteRescheduleStore,
    SqliteReviewWorkflowStore,
)
from growth_engine.application.errors import Conflict
from growth_engine.application.review.approve_group import ApprovalItem, ApproveGroup
from growth_engine.application.review.cancel_delivery import CancelDelivery
from growth_engine.application.review.reject_revision import RejectRevision, ReplaceMode
from growth_engine.application.review.revoke_approval import RevokeApproval
from growth_engine.application.scheduling.reschedule_slot import RescheduleSlot
from growth_engine.domain.channels.channel import Channel, ChannelConfig, ChannelPlatform, config_hash
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.scheduling.slot import SlotTarget
from tests.growth_engine.integration.sqlite.test_revision_store import _fixture
from tests.growth_engine.support.fakes import FakeClock, SeqIds


def _in_review(tmp_path: Path):
    database, uow_factory, slot, variant_b, caption_b, revision = _fixture(tmp_path)
    with uow_factory().begin_immediate() as tx:
        tx.connection.execute(
            "UPDATE deliveries SET state='IN_REVIEW', active_approval_id=NULL WHERE id='delivery-synthetic'"
        )
    return database, uow_factory, slot, variant_b, caption_b, revision


def _add_second_review_delivery(uow_factory, slot, revision: DeliveryRevision) -> DeliveryRevision:
    channel = Channel(
        "channel-synthetic-b", "venho_hotel", "test", "fb_venho", ChannelPlatform.FACEBOOK,
        "synthetic-page-b", "Synthetic Ven Ho", enabled=True,
    )
    config = ChannelConfig(
        "config-synthetic-b", channel.id, 1, "SYNTHETIC_ROUTE_B", "vNN.N",
        {"_synthetic": True, "note": "cần thay bằng fixture thật từ P0-T03/P0-T04"},
    )
    target = "target-synthetic-b"
    updated = DeliveryRevision.create({
        **revision.payload,
        "delivery_id": "delivery-second",
        "revision_id": "revision-second",
        "channel_id": channel.id,
        "remote_account_id": channel.remote_account_id,
        "channel_config_hash": config_hash(config),
    })
    with uow_factory().begin_immediate() as tx:
        tx.channels.save_channel(channel, created_at_ms=1)
        tx.channels.save_config(config, created_at_ms=1)
        tx.slots.save_target(SlotTarget(target, slot.id, channel.id))
        tx.deliveries.save(
            Delivery("delivery-second", DeliveryState.IN_REVIEW, row_version=7),
            target_id=target, channel_id=channel.id, package_id="package-synthetic",
            created_at_ms=1, updated_at_ms=1,
            current_revision_id="revision-second", active_approval_id=None,
        )
        tx.deliveries.save_revision(
            updated, delivery_id="delivery-second", channel_id=channel.id,
            revision_no=1, channel_config_id=config.id, variant_id="variant-a",
            qc_report_id="qc-a", scheduled_at_ms=slot.scheduled_at_ms,
            deadline_at_ms=slot.deadline_at_ms, caption=str(updated.payload["caption"]),
            created_by="synthetic-operator", created_at_ms=1,
        )
    return updated


def test_sqlite_approval_batch_is_atomic_idempotent_and_never_queues_publish(tmp_path: Path) -> None:
    _, uow_factory, slot, _, _, first_revision = _in_review(tmp_path)
    second_revision = _add_second_review_delivery(uow_factory, slot, first_revision)
    store = SqliteReviewWorkflowStore(uow_factory, SeqIds("workflow"))
    use_case = ApproveGroup(store, FakeClock(2_000))
    items = (
        ApprovalItem("delivery-synthetic", "revision-a", first_revision.payload_hash, 4),
        ApprovalItem("delivery-second", "revision-second", second_revision.payload_hash, 6),
    )

    with pytest.raises(Conflict):
        use_case.execute(items, actor="synthetic-operator", principal="bff-test", idempotency_key="stale-batch")
    with uow_factory().read_only() as tx:
        states = tx.connection.execute(
            "SELECT id, state, active_approval_id FROM deliveries ORDER BY id"
        ).fetchall()
        assert tx.connection.execute(
            "SELECT count(*) FROM approval_decisions WHERE decision='APPROVE'"
        ).fetchone()[0] == 1  # only the seeded historical approval
        assert tx.connection.execute("SELECT count(*) FROM outbox_commands").fetchone()[0] == 0
    assert [(row["state"], row["active_approval_id"]) for row in states] == [
        ("IN_REVIEW", None), ("IN_REVIEW", None)
    ]

    valid_items = (
        items[0],
        ApprovalItem("delivery-second", "revision-second", second_revision.payload_hash, 7),
    )
    args = dict(actor="synthetic-operator", principal="bff-test", idempotency_key="valid-batch")
    first = use_case.execute(valid_items, **args)
    replay = use_case.execute(valid_items, **args)
    assert len(first.approvals) == 2 and replay.replayed
    assert replay.approvals == first.approvals
    with uow_factory().read_only() as tx:
        assert tx.connection.execute("SELECT count(*) FROM outbox_commands").fetchone()[0] == 0
        assert tx.connection.execute("SELECT count(*) FROM jobs").fetchone()[0] == 0


def test_sqlite_reject_new_topic_supersedes_and_queues_replacement_job(tmp_path: Path) -> None:
    _, uow_factory, _, _, _, revision = _in_review(tmp_path)
    store = SqliteReviewWorkflowStore(uow_factory, SeqIds("workflow"))
    result = RejectRevision(store, FakeClock(2_000), SeqIds("reject")).execute(
        "delivery-synthetic", revision_id="revision-a", reason="Synthetic new topic",
        replace_mode=ReplaceMode.NEW_TOPIC, actor="synthetic-operator", correlation_id="reject-test",
    )

    assert result.delivery_state is DeliveryState.SUPERSEDED
    assert result.replacement_delivery_id is not None
    with uow_factory().read_only() as tx:
        old = tx.deliveries.get("delivery-synthetic")
        new = tx.deliveries.get(result.replacement_delivery_id)
        job = tx.connection.execute(
            "SELECT kind, lane FROM jobs WHERE business_key LIKE '%new_topic'"
        ).fetchone()
        rejection = tx.connection.execute(
            "SELECT decision, reason FROM approval_decisions WHERE decision='REJECT'"
        ).fetchone()
    assert old is not None and old.state is DeliveryState.SUPERSEDED
    assert new is not None and new.state is DeliveryState.DRAFT
    assert (job["kind"], job["lane"]) == ("new_topic", "jobs")
    assert rejection["reason"] == "Synthetic new topic"


def test_sqlite_revoke_then_cancel_persists_state_and_revoke_evidence(tmp_path: Path) -> None:
    _, uow_factory, _, _, _, _ = _fixture(tmp_path)
    with uow_factory().begin_immediate() as tx:
        revision_hash = tx.connection.execute(
            "SELECT payload_hash FROM delivery_revisions WHERE id='revision-a'"
        ).fetchone()[0]
        tx.connection.execute(
            """INSERT INTO outbox_commands
               (id, delivery_id, revision_id, sequence_no, kind, business_key, payload_hash,
                state, dispatch_epoch, expires_at, next_attempt_at, created_at, updated_at)
               VALUES ('command-open','delivery-synthetic','revision-a',1,'PUBLISH',
                'publish:synthetic-open',?, 'ACKED','epoch-test',10000,1,1,1)""",
            (revision_hash,),
        )
    store = SqliteReviewWorkflowStore(uow_factory, SeqIds("workflow"))
    revoked = RevokeApproval(store, FakeClock(2_000), SeqIds("revoke")).execute(
        "delivery-synthetic", actor="synthetic-operator", reason="Synthetic pause",
    )
    cancelled = CancelDelivery(store, FakeClock(2_000)).execute(
        "delivery-synthetic", actor="synthetic-operator", reason="Synthetic withdrawal",
    )
    assert revoked.delivery_state is DeliveryState.IN_REVIEW
    assert cancelled.delivery_state is DeliveryState.CANCELLED
    with uow_factory().read_only() as tx:
        decisions = tx.connection.execute(
            "SELECT decision, revokes_id FROM approval_decisions ORDER BY created_at, id"
        ).fetchall()
        delivery = tx.connection.execute(
            "SELECT state, active_approval_id FROM deliveries WHERE id='delivery-synthetic'"
        ).fetchone()
        command_state = tx.connection.execute(
            "SELECT state FROM outbox_commands WHERE id='command-open'"
        ).fetchone()[0]
    assert decisions[-1]["decision"] == "REVOKE" and decisions[-1]["revokes_id"] == "approval-a"
    assert (delivery["state"], delivery["active_approval_id"]) == ("CANCELLED", None)
    assert command_state == "CANCELLED"


def test_sqlite_reschedule_creates_revision_and_blocks_any_prior_execution(tmp_path: Path) -> None:
    _, uow_factory, _, _, _, _ = _fixture(tmp_path)
    store = SqliteRescheduleStore(uow_factory, SeqIds("reschedule"))
    use_case = RescheduleSlot(store, FakeClock(2_000), SeqIds("reschedule-case"))
    result = use_case.execute(
        "slot-synthetic", expected_row_version=1, local_date=date(2026, 11, 12),
        local_time="09:30", actor="synthetic-operator", correlation_id="reschedule-test",
    )
    assert len(result.revisions_created) == 1
    with uow_factory().read_only() as tx:
        delivery = tx.connection.execute(
            "SELECT state, current_revision_id, active_approval_id FROM deliveries WHERE id='delivery-synthetic'"
        ).fetchone()
        job = tx.connection.execute("SELECT kind, lane FROM jobs WHERE kind='notify'").fetchone()
        slot = tx.connection.execute("SELECT scheduled_at FROM slots WHERE id='slot-synthetic'").fetchone()
    assert delivery["state"] == "IN_REVIEW" and delivery["active_approval_id"] is None
    assert delivery["current_revision_id"] == result.revisions_created[0]
    assert (job["kind"], job["lane"]) == ("notify", "publish")
    assert slot["scheduled_at"] == result.scheduled_at_ms

    live_path = tmp_path / "live"
    live_path.mkdir()
    _, live_uow, _, _, _, _ = _fixture(live_path, queued_authorized=True)
    with pytest.raises(Conflict):
        RescheduleSlot(SqliteRescheduleStore(live_uow, SeqIds("live-reschedule")),
                       FakeClock(2_000), SeqIds("live-case")).execute(
            "slot-synthetic", expected_row_version=1, local_date=date(2026, 11, 12),
            local_time="09:30", actor="synthetic-operator", correlation_id="reschedule-live",
        )


def test_sqlite_authorized_delivery_blocks_revoke_and_cancel(tmp_path: Path) -> None:
    _, uow_factory, _, _, _, _ = _fixture(tmp_path, queued_authorized=True)
    store = SqliteReviewWorkflowStore(uow_factory, SeqIds("workflow"))
    with pytest.raises(DomainError) as caught:
        RevokeApproval(store, FakeClock(2_000), SeqIds("revoke")).execute(
            "delivery-synthetic", actor="synthetic-operator", reason="Synthetic pause",
        )
    assert caught.value.code == ErrorCode.ALREADY_AUTHORIZED.value
    with pytest.raises(DomainError) as caught_cancel:
        CancelDelivery(store, FakeClock(2_000)).execute(
            "delivery-synthetic", actor="synthetic-operator", reason="Synthetic stop",
        )
    assert caught_cancel.value.code == ErrorCode.ALREADY_AUTHORIZED.value
