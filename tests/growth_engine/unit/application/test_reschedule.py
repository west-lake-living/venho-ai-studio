from __future__ import annotations

from datetime import date
from hashlib import sha256

import pytest

from growth_engine.application.errors import Conflict
from growth_engine.application.scheduling.reschedule_slot import RescheduleSlot
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.media.asset import MediaVariant, VariantQcStatus
from growth_engine.domain.media.qc import QcDecision, QcReport
from growth_engine.domain.scheduling.slot import Slot
from tests.growth_engine.support.fakes import FakeClock, SeqIds


def test_reschedule_is_rejected_if_any_target_has_an_execution() -> None:
    store = _RescheduleStore(has_live_execution=True)
    use_case = RescheduleSlot(store, FakeClock(1_000), SeqIds("reschedule"))

    with pytest.raises(Conflict):
        use_case.execute(
            "slot-1", expected_row_version=3,
            local_date=date(2026, 11, 12), local_time="09:00",
            actor="operator-1", correlation_id="request-1",
        )

    assert store.write is None


def test_reschedule_creates_new_revision_and_revokes_approval_atomically() -> None:
    revision = _revision()
    approval = ApprovalDecision(
        "approval-1", "revision-1", revision.payload_hash, ApprovalType.APPROVE, "operator", 100
    )
    delivery = Delivery("delivery-1", DeliveryState.APPROVED, row_version=4)
    variant = MediaVariant(
        id="variant-1", asset_id="asset-1", transform_version="test", sha256="a" * 64,
        object_key="variants/aa/asset.jpg", width=640, height=480, mime="image/jpeg",
        byte_size=1_000, qc_status=VariantQcStatus.PASS, created_at_ms=10,
    )
    report = QcReport(
        id="qc-1", variant_id="variant-1", caption_hash=sha256(b"Caption").hexdigest(),
        ruleset_hash="2" * 64, fact_snapshot_hash="3" * 64, decision=QcDecision.PASS,
        coverage_gaps=(), result_json='{"_synthetic":true}', created_at_ms=10,
    )
    slot = Slot(
        id="slot-1", project_id="project-1", local_date=date(2026, 11, 10),
        local_time="09:00", timezone="Asia/Ho_Chi_Minh", lane="weekly",
        cadence_version="v1", scheduled_at_ms=1_000, deadline_at_ms=10_000,
    )
    context = _RescheduleContext(
        slot=slot, row_version=3, has_execution=False,
        deliveries=(
            _RescheduleDeliveryContext(
                delivery=delivery, current_revision=revision, variant=variant, qc_report=report,
                active_approval=approval, command_state="ACKED", has_execution=False,
                next_revision_no=2, facts_valid_until_ms=(1_900_000_000_000,),
            ),
        ),
    )
    store = _ContextRescheduleStore(context)
    result = RescheduleSlot(store, FakeClock(1_000), SeqIds("reschedule")).execute(
        "slot-1", expected_row_version=3, local_date=date(2026, 11, 12),
        local_time="09:30", actor="operator-1", correlation_id="request-1",
    )

    assert len(result.revisions_created) == 1
    assert store.write is not None
    changed = store.write.delivery_writes[0]
    assert changed.updated_delivery.state is DeliveryState.IN_REVIEW
    assert changed.revision.payload["scheduled_at_ms"] == result.scheduled_at_ms
    assert changed.revision.payload["deadline_at_ms"] == result.deadline_at_ms
    assert changed.revocation is not None and changed.revocation.revokes_id == approval.id
    assert changed.cancel_open_command is True
    assert changed.notification_job_id


class _RescheduleStore:
    def __init__(self, *, has_live_execution: bool) -> None:
        self.write = None
        self.context = _RescheduleContext(
            slot=Slot(
                id="slot-1", project_id="project-1", local_date=date(2026, 11, 10),
                local_time="09:00", timezone="Asia/Ho_Chi_Minh", lane="weekly",
                cadence_version="v1", scheduled_at_ms=1_000, deadline_at_ms=10_000,
            ),
            row_version=3,
            has_execution=has_live_execution,
            deliveries=(),
        )

    def load_context(self, slot_id: str):
        return self.context if slot_id == self.context.slot.id else None

    def apply_reschedule(self, write) -> None:
        self.write = write


class _RescheduleContext:
    def __init__(self, *, slot, row_version, has_execution, deliveries) -> None:
        self.slot = slot
        self.row_version = row_version
        self.has_execution = has_execution
        self.deliveries = deliveries


class _RescheduleDeliveryContext:
    def __init__(
        self, *, delivery, current_revision, variant, qc_report, active_approval,
        command_state, has_execution, next_revision_no, facts_valid_until_ms,
    ) -> None:
        self.delivery = delivery
        self.current_revision = current_revision
        self.variant = variant
        self.qc_report = qc_report
        self.active_approval = active_approval
        self.command_state = command_state
        self.has_execution = has_execution
        self.next_revision_no = next_revision_no
        self.facts_valid_until_ms = facts_valid_until_ms


class _ContextRescheduleStore:
    def __init__(self, context) -> None:
        self.context = context
        self.write = None

    def load_context(self, slot_id: str):
        return self.context if slot_id == self.context.slot.id else None

    def apply_reschedule(self, write) -> None:
        self.write = write


def _revision() -> DeliveryRevision:
    return DeliveryRevision.create({
        "delivery_id": "delivery-1", "revision_id": "revision-1",
        "channel_id": "channel-1", "remote_account_id": "page-1",
        "channel_config_hash": "1" * 64, "caption": "Caption",
        "media": [{"sha256": "a" * 64, "mime": "image/jpeg", "width": 640, "height": 480}],
        "scheduled_at_ms": 1_000, "deadline_at_ms": 10_000, "qc_report_id": "qc-1",
        "ruleset_hash": "2" * 64, "fact_snapshot_hash": "3" * 64,
    })
