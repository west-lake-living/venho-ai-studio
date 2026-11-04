from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

from growth_engine.application.errors import Conflict, NotFound, PreconditionFailed
from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision, normalize_caption
from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.media.asset import MediaVariant, VariantQcStatus
from growth_engine.domain.media.qc import QcDecision, QcReport

_OPEN_COMMAND_STATES = frozenset({"PENDING", "DELIVERING", "ACKED"})


@dataclass(frozen=True)
class RevisionDraft:
    caption: str | None = None
    variant_id: str | None = None


@dataclass(frozen=True)
class RevisionContext:
    delivery: Delivery
    channel_id: str
    channel_config_id: str
    channel_config_hash: str
    remote_account_id: str
    next_revision_no: int
    scheduled_at_ms: int
    deadline_at_ms: int
    fact_snapshot_hash: str
    current_revision: DeliveryRevision | None
    active_approval: ApprovalDecision | None
    variant: MediaVariant
    qc_report: QcReport
    command_state: str | None
    live_execution: bool


@dataclass(frozen=True)
class RevisionWrite:
    context: RevisionContext
    updated_delivery: Delivery
    revision: DeliveryRevision
    revision_no: int
    revocation: ApprovalDecision | None
    expected_row_version: int
    actor: str
    created_at_ms: int
    cancel_open_command: bool


class RevisionStore(Protocol):
    """Persistence seam; apply_revision must perform the complete §7.4 write atomically.

    The implementation uses BEGIN IMMEDIATE and CAS on expected_row_version, then
    writes the immutable revision, optional REVOKE, delivery pointers/state,
    command cancellation, audit event, and review-notification job before commit.
    """

    def load_context(self, delivery_id: str, draft: RevisionDraft) -> RevisionContext | None: ...
    def apply_revision(self, write: RevisionWrite) -> None: ...


@dataclass(frozen=True)
class CreateRevisionResult:
    delivery_id: str
    revision: DeliveryRevision
    delivery_state: DeliveryState
    row_version: int


class CreateRevision:
    """Create an immutable review revision; the store applies it atomically with CAS/audit."""

    def __init__(self, store: RevisionStore, clock: Clock, ids: IdGenerator) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids

    def execute(
        self,
        delivery_id: str,
        *,
        expected_row_version: int,
        draft: RevisionDraft,
        actor: str,
    ) -> CreateRevisionResult:
        if not delivery_id.strip() or not actor.strip():
            raise ValueError("delivery_id and actor are required")
        if type(expected_row_version) is not int or expected_row_version < 1:
            raise ValueError("expected_row_version must be a positive integer")
        if not isinstance(draft, RevisionDraft):
            raise TypeError("draft must be RevisionDraft")

        context = self._store.load_context(delivery_id, draft)
        if context is None:
            raise NotFound("Không tìm thấy bài cần chỉnh sửa.")
        if context.delivery.row_version != expected_row_version:
            raise PreconditionFailed("Bài đã thay đổi; hãy mở lại bản xem trước.")
        if draft.variant_id is not None and context.variant.id != draft.variant_id:
            raise NotFound("Không tìm thấy biến thể ảnh.")
        if context.delivery.state not in {
            DeliveryState.DRAFT,
            DeliveryState.IN_REVIEW,
            DeliveryState.APPROVED,
            DeliveryState.QUEUED,
        }:
            raise Conflict("Trạng thái bài không cho phép tạo revision mới.")
        if context.delivery.state is DeliveryState.QUEUED and context.command_state == "AUTHORIZED":
            raise DomainError(
                ErrorCode.ALREADY_AUTHORIZED,
                "Bài đang được đăng, không thể sửa hoặc thu hồi.",
            )
        if context.live_execution:
            raise Conflict("Bài có execution đang hoạt động, không thể tạo revision mới.")
        if context.delivery.state in {DeliveryState.APPROVED, DeliveryState.QUEUED}:
            if context.active_approval is None:
                raise Conflict("Bản đã duyệt không có approval đang hiệu lực.")
            if context.current_revision is None or (
                context.active_approval.revision_id != context.current_revision.payload.get("revision_id")
                or context.active_approval.payload_hash != context.current_revision.payload_hash
                or context.active_approval.decision is not ApprovalType.APPROVE
            ):
                raise Conflict("Approval không khớp revision hiện hành.")
        if context.qc_report.variant_id != context.variant.id:
            raise Conflict("QC report không khớp biến thể ảnh.")
        if context.variant.qc_status in {VariantQcStatus.FAIL, VariantQcStatus.QUARANTINED}:
            raise DomainError(ErrorCode.QC_FAILED, "Ảnh chưa đạt kiểm tra chất lượng.")
        if context.qc_report.decision is QcDecision.FAIL:
            raise DomainError(ErrorCode.QC_FAILED, "Ảnh chưa đạt kiểm tra chất lượng.")

        caption = draft.caption
        if caption is None and context.current_revision is not None:
            current_caption = context.current_revision.payload.get("caption")
            caption = current_caption if isinstance(current_caption, str) else None
        if caption is None:
            raise ValueError("caption is required for the first revision")
        caption = normalize_caption(caption)
        if context.qc_report.caption_hash != hashlib.sha256(caption.encode("utf-8")).hexdigest():
            raise Conflict("QC report không khớp nội dung caption.")
        if context.qc_report.fact_snapshot_hash != context.fact_snapshot_hash:
            raise Conflict("QC report không khớp bộ facts hiện hành.")
        if context.next_revision_no < 1:
            raise Conflict("Số revision kế tiếp không hợp lệ.")

        now_ms = self._clock.now_ms()
        updated_delivery, _events = context.delivery.apply(
            DeliveryEvent.CREATE_REVISION,
            {
                "now_ms": now_ms,
                "if_match_matches": True,
                "revision_complete": True,
                "qc_status": context.variant.qc_status.value,
                "no_execution_live": not context.live_execution,
                "command_not_authorized": context.command_state != "AUTHORIZED",
            },
        )
        revision_id = self._ids.new_id()
        revision = DeliveryRevision.create(
            {
                "delivery_id": context.delivery.id,
                "revision_id": revision_id,
                "channel_id": context.channel_id,
                "remote_account_id": context.remote_account_id,
                "channel_config_hash": context.channel_config_hash,
                "caption": caption,
                "media": [
                    {
                        "sha256": context.variant.sha256,
                        "mime": context.variant.mime,
                        "width": context.variant.width,
                        "height": context.variant.height,
                    }
                ],
                "scheduled_at_ms": context.scheduled_at_ms,
                "deadline_at_ms": context.deadline_at_ms,
                "qc_report_id": context.qc_report.id,
                "ruleset_hash": context.qc_report.ruleset_hash,
                "fact_snapshot_hash": context.fact_snapshot_hash,
            }
        )
        revocation = None
        if context.active_approval is not None:
            revocation = ApprovalDecision(
                id=self._ids.new_id(),
                revision_id=context.active_approval.revision_id,
                payload_hash=context.active_approval.payload_hash,
                decision=ApprovalType.REVOKE,
                actor_id=actor,
                created_at_ms=now_ms,
                reason="Revision changed; approval required again.",
                revokes_id=context.active_approval.id,
            )
        write = RevisionWrite(
            context=context,
            updated_delivery=updated_delivery,
            revision=revision,
            revision_no=context.next_revision_no,
            revocation=revocation,
            expected_row_version=expected_row_version,
            actor=actor,
            created_at_ms=now_ms,
            cancel_open_command=context.command_state in _OPEN_COMMAND_STATES,
        )
        self._store.apply_revision(write)
        return CreateRevisionResult(
            delivery_id=context.delivery.id,
            revision=revision,
            delivery_state=updated_delivery.state,
            row_version=updated_delivery.row_version,
        )


def create_revision(
    use_case: CreateRevision,
    delivery_id: str,
    *,
    expected_row_version: int,
    draft: RevisionDraft,
    actor: str,
) -> CreateRevisionResult:
    return use_case.execute(
        delivery_id,
        expected_row_version=expected_row_version,
        draft=draft,
        actor=actor,
    )
