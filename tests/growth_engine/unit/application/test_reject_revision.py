from __future__ import annotations

import pytest

from growth_engine.application.review.reject_revision import RejectRevision, ReplaceMode
from growth_engine.application.review.cancel_delivery import CancelDelivery
from growth_engine.application.review.revoke_approval import RevokeApproval
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from tests.growth_engine.support.fakes import FakeClock, SeqIds


def test_reject_none_records_reject_without_replacement_job() -> None:
    store = _RejectStore()
    result = RejectRevision(store, FakeClock(500), SeqIds("reject")).execute(
        "delivery-1", revision_id="revision-1", reason="Need a clearer offer.",
        replace_mode=ReplaceMode.NONE, actor="operator-1",
    )

    assert result.decision.decision is ApprovalType.REJECT
    assert store.write is not None
    assert store.write.job_kind is None
    assert store.write.updated_delivery.state is DeliveryState.IN_REVIEW


def test_reject_revise_enqueues_revision_job() -> None:
    store = _RejectStore()
    RejectRevision(store, FakeClock(500), SeqIds("reject")).execute(
        "delivery-1", revision_id="revision-1", reason="Revise the caption.",
        replace_mode=ReplaceMode.REVISE, actor="operator-1",
    )

    assert store.write is not None
    assert store.write.job_kind == "revise"
    assert store.write.replacement_delivery_id is None


def test_reject_new_topic_supersedes_and_creates_replacement_in_one_write() -> None:
    store = _RejectStore()
    result = RejectRevision(store, FakeClock(500), SeqIds("reject")).execute(
        "delivery-1", revision_id="revision-1", reason="Use a different topic.",
        replace_mode=ReplaceMode.NEW_TOPIC, actor="operator-1",
    )

    assert result.delivery_state is DeliveryState.SUPERSEDED
    assert store.write is not None
    assert store.write.job_kind == "new_topic"
    assert store.write.replacement_delivery_id == "reject-3"


def test_revoke_approval_moves_queued_delivery_to_review_and_cancels_open_command() -> None:
    revision = _revision()
    approval = ApprovalDecision(
        "approval-1", "revision-1", revision.payload_hash, ApprovalType.APPROVE, "operator", 100
    )
    store = _RevokeStore(
        delivery=Delivery("delivery-1", DeliveryState.QUEUED, row_version=3),
        current_revision=revision,
        active_approval=approval,
        command_state="ACKED",
        live_execution=False,
    )

    result = RevokeApproval(store, FakeClock(500), SeqIds("revoke")).execute(
        "delivery-1", actor="operator-1", reason="Pause this post."
    )

    assert result.delivery_state is DeliveryState.IN_REVIEW
    assert store.write is not None
    assert store.write.revocation.revokes_id == approval.id
    assert store.write.cancel_open_command is True


def test_revoke_after_authorization_returns_409_without_writes() -> None:
    revision = _revision()
    approval = ApprovalDecision(
        "approval-1", "revision-1", revision.payload_hash, ApprovalType.APPROVE, "operator", 100
    )
    store = _RevokeStore(
        delivery=Delivery("delivery-1", DeliveryState.QUEUED, row_version=3),
        current_revision=revision,
        active_approval=approval,
        command_state="AUTHORIZED",
        live_execution=False,
    )

    with pytest.raises(DomainError) as caught:
        RevokeApproval(store, FakeClock(500), SeqIds("revoke")).execute(
            "delivery-1", actor="operator-1", reason="Pause this post."
        )
    assert caught.value.code == ErrorCode.ALREADY_AUTHORIZED.value
    assert store.write is None


def test_cancel_delivery_moves_to_cancelled_and_cancels_open_command() -> None:
    store = _CancelStore(
        delivery=Delivery("delivery-1", DeliveryState.BLOCKED, row_version=3),
        command_state="PENDING",
        live_execution=False,
    )

    result = CancelDelivery(store, FakeClock(500)).execute(
        "delivery-1", actor="operator-1", reason="Content withdrawn."
    )

    assert result.delivery_state is DeliveryState.CANCELLED
    assert store.write is not None
    assert store.write.cancel_open_command is True


class _RejectStore:
    def __init__(self) -> None:
        self.write = None
        self.context = _RejectContext(
            delivery=Delivery("delivery-1", DeliveryState.IN_REVIEW, row_version=2),
            current_revision=_revision(),
            current_revision_id="revision-1",
            live_execution=False,
        )

    def load_context(self, delivery_id: str):
        return self.context if delivery_id == "delivery-1" else None

    def apply_rejection(self, write) -> None:
        self.write = write


def _revision() -> DeliveryRevision:
    return DeliveryRevision.create({
        "delivery_id": "delivery-1", "revision_id": "revision-1",
        "channel_id": "channel-1", "remote_account_id": "page-1",
        "channel_config_hash": "1" * 64, "caption": "Caption",
        "media": [{"sha256": "a" * 64, "mime": "image/jpeg", "width": 640, "height": 480}],
        "scheduled_at_ms": 100, "deadline_at_ms": 200, "qc_report_id": "qc-1",
        "ruleset_hash": "2" * 64, "fact_snapshot_hash": "3" * 64,
    })


class _RejectContext:
    def __init__(self, *, delivery, current_revision, current_revision_id, live_execution) -> None:
        self.delivery = delivery
        self.current_revision = current_revision
        self.current_revision_id = current_revision_id
        self.live_execution = live_execution


class _RevokeStore:
    def __init__(self, *, delivery, current_revision, active_approval, command_state, live_execution) -> None:
        self.write = None
        self.context = type("Context", (), {
            "delivery": delivery,
            "current_revision": current_revision,
            "active_approval": active_approval,
            "command_state": command_state,
            "live_execution": live_execution,
        })()

    def load_context(self, delivery_id: str):
        return self.context if delivery_id == self.context.delivery.id else None

    def apply_revocation(self, write) -> None:
        self.write = write


class _CancelStore:
    def __init__(self, *, delivery, command_state, live_execution) -> None:
        self.write = None
        self.context = type("Context", (), {
            "delivery": delivery,
            "command_state": command_state,
            "live_execution": live_execution,
        })()

    def load_context(self, delivery_id: str):
        return self.context if delivery_id == self.context.delivery.id else None

    def apply_cancellation(self, write) -> None:
        self.write = write
