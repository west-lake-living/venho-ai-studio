from __future__ import annotations

from dataclasses import replace
from hashlib import sha256

import pytest

from growth_engine.application.errors import PreconditionFailed
from growth_engine.application.queries.delivery_views import ReviewSnapshotData
from growth_engine.application.review.build_review_snapshot import BuildReviewSnapshot
from growth_engine.application.review.create_revision import (
    CreateRevision,
    RevisionContext,
    RevisionDraft,
    RevisionWrite,
)
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.media.asset import MediaVariant, VariantQcStatus
from growth_engine.domain.media.qc import QcDecision, QcReport
from tests.growth_engine.support.fakes import FakeClock, SeqIds

_SHA_A = "a" * 64
_SHA_B = "b" * 64


def test_editing_approved_delivery_revokes_approval_and_creates_revision() -> None:
    store = _RevisionStore(_context(DeliveryState.APPROVED, active_approval=True))
    use_case = CreateRevision(store, FakeClock(500), SeqIds("revision"))

    result = use_case.execute(
        "delivery-1",
        expected_row_version=4,
        draft=RevisionDraft(caption="Edited caption", variant_id="variant-b"),
        actor="operator-1",
    )

    assert result.delivery_state is DeliveryState.IN_REVIEW
    assert result.row_version == 5
    assert result.revision.payload["caption"] == "Edited caption"
    assert result.revision.payload["media"][0]["sha256"] == _SHA_B
    assert store.write is not None
    assert store.write.revocation is not None
    assert store.write.revocation.decision is ApprovalType.REVOKE
    assert store.write.revocation.revokes_id == "approval-1"
    assert store.write.cancel_open_command is False


def test_queued_delivery_with_authorized_command_returns_409_without_writes() -> None:
    store = _RevisionStore(
        _context(DeliveryState.QUEUED, active_approval=True, command_state="AUTHORIZED")
    )
    use_case = CreateRevision(store, FakeClock(500), SeqIds("revision"))

    with pytest.raises(DomainError) as caught:
        use_case.execute(
            "delivery-1",
            expected_row_version=4,
            draft=RevisionDraft(caption="Edited caption"),
            actor="operator-1",
        )

    assert caught.value.code == ErrorCode.ALREADY_AUTHORIZED.value
    assert store.write is None


def test_stale_expected_row_version_is_rejected_before_writes() -> None:
    store = _RevisionStore(_context(DeliveryState.IN_REVIEW, active_approval=False))
    use_case = CreateRevision(store, FakeClock(500), SeqIds("revision"))

    with pytest.raises(PreconditionFailed):
        use_case.execute(
            "delivery-1",
            expected_row_version=3,
            draft=RevisionDraft(caption="Edited caption"),
            actor="operator-1",
        )
    assert store.write is None


def test_review_snapshot_preview_sha_matches_exact_variant_and_includes_actions() -> None:
    revision = _revision()
    data = ReviewSnapshotData(
        delivery=Delivery("delivery-1", DeliveryState.IN_REVIEW, row_version=7),
        revision=revision,
        channel_key="fb_hanoi",
        channel_name="Ven Hồ Hotel Hanoi",
        remote_account_id="page-synthetic",
        scheduled_at_ms=100,
        deadline_at_ms=200,
        variant=_variant("variant-a", _SHA_A),
        action_context={"revision_is_current": True, "no_execution_live": True},
    )
    use_case = BuildReviewSnapshot(
        _ReviewReader(data), preview_url_builder=lambda digest: f"https://preview.test/{digest}"
    )

    snapshot = use_case.execute("delivery-1")

    assert snapshot.preview_sha256 == _SHA_A
    assert snapshot.preview_url == f"https://preview.test/{_SHA_A}"
    assert snapshot.etag == '"delivery:delivery-1:7"'
    assert snapshot.payload_hash == revision.payload_hash
    assert {item["action"] for item in snapshot.allowed_actions} >= {"approve", "edit_caption", "replace_image"}


class _RevisionStore:
    def __init__(self, context: RevisionContext) -> None:
        self.context = context
        self.write: RevisionWrite | None = None

    def load_context(self, delivery_id: str, draft: RevisionDraft) -> RevisionContext | None:
        assert delivery_id == self.context.delivery.id
        if draft.variant_id is None and draft.caption is None:
            return self.context
        variant_id = draft.variant_id or self.context.variant.id
        variant = self.context.variant if variant_id == self.context.variant.id else _variant(variant_id, _SHA_B)
        caption = draft.caption or self.context.current_revision.payload["caption"]
        qc_report = replace(
            _qc_report(variant_id),
            caption_hash=sha256(caption.encode("utf-8")).hexdigest(),
        )
        return replace(self.context, variant=variant, qc_report=qc_report)

    def apply_revision(self, write: RevisionWrite) -> None:
        self.write = write
        self.context = replace(
            self.context,
            delivery=write.updated_delivery,
            current_revision=write.revision,
            active_approval=None,
            next_revision_no=self.context.next_revision_no + 1,
        )


class _ReviewReader:
    def __init__(self, data: ReviewSnapshotData) -> None:
        self.data = data

    def load_review_data(self, delivery_id: str) -> ReviewSnapshotData | None:
        return self.data if delivery_id == self.data.delivery.id else None


def _context(
    state: DeliveryState,
    *,
    active_approval: bool,
    command_state: str | None = None,
) -> RevisionContext:
    current_revision = _revision() if state is not DeliveryState.DRAFT else None
    approval = (
        ApprovalDecision(
            "approval-1",
            "revision-current",
            current_revision.payload_hash,
            ApprovalType.APPROVE,
            "operator",
            100,
        )
        if active_approval and current_revision is not None
        else None
    )
    return RevisionContext(
        delivery=Delivery("delivery-1", state, row_version=4),
        channel_id="channel-1",
        channel_config_id="config-1",
        channel_config_hash="1" * 64,
        remote_account_id="page-synthetic",
        next_revision_no=2,
        scheduled_at_ms=100,
        deadline_at_ms=200,
        fact_snapshot_hash="2" * 64,
        current_revision=current_revision,
        active_approval=approval,
        variant=_variant("variant-a", _SHA_A),
        qc_report=_qc_report("variant-a"),
        command_state=command_state,
        live_execution=False,
    )


def _revision() -> DeliveryRevision:
    return DeliveryRevision.create(
        {
            "delivery_id": "delivery-1",
            "revision_id": "revision-current",
            "channel_id": "channel-1",
            "remote_account_id": "page-synthetic",
            "channel_config_hash": "1" * 64,
            "caption": "Original caption",
            "media": [{"sha256": _SHA_A, "mime": "image/jpeg", "width": 640, "height": 480}],
            "scheduled_at_ms": 100,
            "deadline_at_ms": 200,
            "qc_report_id": "qc-1",
            "ruleset_hash": "3" * 64,
            "fact_snapshot_hash": "2" * 64,
        }
    )


def _variant(variant_id: str, digest: str) -> MediaVariant:
    return MediaVariant(
        id=variant_id,
        asset_id="asset-1",
        transform_version="test-profile",
        sha256=digest,
        object_key=f"variants/{digest[:2]}/{digest}.jpg",
        width=640,
        height=480,
        mime="image/jpeg",
        byte_size=1234,
        qc_status=VariantQcStatus.PASS,
        created_at_ms=10,
    )


def _qc_report(variant_id: str) -> QcReport:
    return QcReport(
        id="qc-2",
        variant_id=variant_id,
        caption_hash=sha256(b"Original caption").hexdigest(),
        ruleset_hash="3" * 64,
        fact_snapshot_hash="2" * 64,
        decision=QcDecision.PASS,
        coverage_gaps=(),
        result_json='{"_synthetic":true}',
        created_at_ms=10,
    )
