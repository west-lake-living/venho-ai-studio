from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Protocol, Sequence

from growth_engine.application.errors import Conflict, NotFound, PreconditionFailed
from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.kernel.time import BusinessCalendar
from growth_engine.domain.media.asset import MediaVariant, VariantQcStatus
from growth_engine.domain.media.qc import QcDecision, QcReport
from growth_engine.domain.scheduling.slot import Slot

_OPEN_COMMAND_STATES = frozenset({"PENDING", "DELIVERING", "ACKED"})


@dataclass(frozen=True)
class RescheduleDeliveryContext:
    delivery: Delivery
    current_revision: DeliveryRevision | None
    variant: MediaVariant | None
    qc_report: QcReport | None
    active_approval: ApprovalDecision | None
    command_state: str | None
    has_execution: bool
    next_revision_no: int
    facts_valid_until_ms: tuple[int, ...] = ()


@dataclass(frozen=True)
class RescheduleContext:
    slot: Slot
    row_version: int
    deliveries: tuple[RescheduleDeliveryContext, ...]
    has_execution: bool = False


@dataclass(frozen=True)
class DeliveryRescheduleWrite:
    context: RescheduleDeliveryContext
    updated_delivery: Delivery
    revision: DeliveryRevision
    revision_no: int
    revocation: ApprovalDecision | None
    cancel_open_command: bool
    notification_job_id: str


@dataclass(frozen=True)
class RescheduleWrite:
    context: RescheduleContext
    updated_slot: Slot
    delivery_writes: tuple[DeliveryRescheduleWrite, ...]
    expected_slot_row_version: int
    actor: str
    correlation_id: str
    changed_at_ms: int


class RescheduleStore(Protocol):
    """Apply slot + every affected delivery update in one BEGIN IMMEDIATE transaction.

    The adapter CAS-checks the slot and each delivery row_version, verifies no target
    gained an execution, inserts immutable revisions/revocations, cancels open
    commands, updates pointers/state, appends audit and queues review notification
    jobs before committing.
    """

    def load_context(self, slot_id: str) -> RescheduleContext | None: ...
    def apply_reschedule(self, write: RescheduleWrite) -> None: ...


@dataclass(frozen=True)
class RescheduleResult:
    slot_id: str
    scheduled_at_ms: int
    deadline_at_ms: int
    revisions_created: tuple[str, ...]


class RescheduleSlot:
    def __init__(self, store: RescheduleStore, clock: Clock, ids: IdGenerator) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids

    def execute(
        self,
        slot_id: str,
        *,
        expected_row_version: int,
        local_date: date,
        local_time: str,
        actor: str,
        correlation_id: str,
    ) -> RescheduleResult:
        if not slot_id.strip() or not actor.strip() or not correlation_id.strip():
            raise ValueError("slot_id, actor and correlation_id are required")
        if type(expected_row_version) is not int or expected_row_version < 1:
            raise ValueError("expected_row_version must be a positive integer")
        if isinstance(local_date, datetime) or not isinstance(local_date, date):
            raise ValueError("local_date must be a date")
        context = self._store.load_context(slot_id)
        if context is None:
            raise NotFound("Không tìm thấy lịch cần đổi.")
        if context.row_version != expected_row_version:
            raise PreconditionFailed("Lịch đã thay đổi; hãy tải lại.")
        if context.slot.cancelled_at_ms is not None:
            raise Conflict("Không thể đổi lịch đã bị huỷ.")

        calendar = BusinessCalendar(context.slot.timezone)
        scheduled_at_ms = int(calendar.local_to_epoch_ms(local_date, local_time))
        duration_ms = context.slot.deadline_at_ms - context.slot.scheduled_at_ms
        deadline_at_ms = scheduled_at_ms + duration_ms
        now_ms = self._clock.now_ms()
        if scheduled_at_ms <= now_ms:
            raise Conflict("Giờ mới phải nằm trong tương lai.")
        if context.has_execution or any(item.has_execution for item in context.deliveries):
            raise Conflict("Không thể đổi lịch khi bất kỳ target nào đã có execution.")
        if len({item.delivery.id for item in context.deliveries}) != len(context.deliveries):
            raise Conflict("Slot có delivery bị trùng.")

        delivery_writes = tuple(
            self._build_delivery_write(
                item,
                scheduled_at_ms=scheduled_at_ms,
                deadline_at_ms=deadline_at_ms,
                now_ms=now_ms,
                actor=actor,
                current_slot=context.slot,
            )
            for item in context.deliveries
            if item.current_revision is not None
        )
        if any(
            item.current_revision is None and item.delivery.state is not DeliveryState.DRAFT
            for item in context.deliveries
        ):
            raise Conflict("Delivery đang có trạng thái cần revision nhưng revision hiện hành bị thiếu.")

        updated_slot = replace(
            context.slot,
            local_date=local_date,
            local_time=local_time,
            scheduled_at_ms=scheduled_at_ms,
            deadline_at_ms=deadline_at_ms,
        )
        self._store.apply_reschedule(
            RescheduleWrite(
                context=context,
                updated_slot=updated_slot,
                delivery_writes=delivery_writes,
                expected_slot_row_version=expected_row_version,
                actor=actor,
                correlation_id=correlation_id,
                changed_at_ms=now_ms,
            )
        )
        return RescheduleResult(
            slot_id=slot_id,
            scheduled_at_ms=scheduled_at_ms,
            deadline_at_ms=deadline_at_ms,
            revisions_created=tuple(
                str(item.revision.payload.get("revision_id")) for item in delivery_writes
            ),
        )

    def _build_delivery_write(
        self,
        context: RescheduleDeliveryContext,
        *,
        scheduled_at_ms: int,
        deadline_at_ms: int,
        now_ms: int,
        actor: str,
        current_slot: Slot,
    ) -> DeliveryRescheduleWrite:
        revision = context.current_revision
        if revision is None:
            raise Conflict("Không tìm thấy revision hiện hành.")
        if context.next_revision_no < 1:
            raise Conflict("Số revision kế tiếp không hợp lệ.")
        if context.delivery.state not in {
            DeliveryState.IN_REVIEW,
            DeliveryState.APPROVED,
            DeliveryState.QUEUED,
        }:
            raise Conflict("Trạng thái delivery không cho phép đổi lịch.")
        if context.variant is None or context.qc_report is None:
            raise Conflict("Thiếu variant hoặc QC report cho revision hiện hành.")
        media = revision.payload.get("media")
        if (
            not isinstance(media, list)
            or not media
            or not isinstance(media[0], dict)
            or media[0].get("sha256") != context.variant.sha256
            or context.qc_report.variant_id != context.variant.id
        ):
            raise Conflict("Revision, variant và QC report không đồng nhất.")
        if (
            revision.payload.get("delivery_id") != context.delivery.id
            or revision.payload.get("scheduled_at_ms") != current_slot.scheduled_at_ms
            or revision.payload.get("deadline_at_ms") != current_slot.deadline_at_ms
        ):
            raise Conflict("Revision hiện hành không khớp lịch slot.")
        if context.variant.qc_status not in {VariantQcStatus.PASS, VariantQcStatus.REVIEW}:
            raise DomainError(ErrorCode.QC_FAILED, "Ảnh chưa đạt kiểm tra chất lượng.")
        if context.qc_report.decision is QcDecision.FAIL:
            raise DomainError(ErrorCode.QC_FAILED, "Ảnh chưa đạt kiểm tra chất lượng.")
        if context.qc_report.fact_snapshot_hash != revision.payload.get("fact_snapshot_hash"):
            raise Conflict("QC report không khớp facts của revision.")
        if (
            context.qc_report.id != revision.payload.get("qc_report_id")
            or context.qc_report.ruleset_hash != revision.payload.get("ruleset_hash")
        ):
            raise Conflict("QC report không khớp policy của revision.")
        caption = revision.payload.get("caption")
        if (
            not isinstance(caption, str)
            or context.qc_report.caption_hash != hashlib.sha256(caption.encode("utf-8")).hexdigest()
        ):
            raise Conflict("QC report không khớp caption của revision.")
        if any(valid_until <= scheduled_at_ms for valid_until in context.facts_valid_until_ms):
            raise Conflict("Một hoặc nhiều facts hết hạn trước giờ đăng mới.")
        if context.delivery.state is DeliveryState.QUEUED and context.command_state == "AUTHORIZED":
            raise DomainError(ErrorCode.ALREADY_AUTHORIZED, "Lệnh đăng đã được cấp quyền.")

        approval = context.active_approval
        current_revision_id = revision.payload.get("revision_id")
        if context.delivery.state in {DeliveryState.APPROVED, DeliveryState.QUEUED}:
            if (
                approval is None
                or approval.decision is not ApprovalType.APPROVE
                or approval.revision_id != current_revision_id
                or approval.payload_hash != revision.payload_hash
            ):
                raise Conflict("Approval không khớp revision hiện hành.")
        elif approval is not None:
            raise Conflict("Delivery IN_REVIEW không được có active approval.")

        updated_delivery, _events = context.delivery.apply(
            DeliveryEvent.CREATE_REVISION,
            {
                "now_ms": now_ms,
                "if_match_matches": True,
                "revision_complete": True,
                "qc_status": context.variant.qc_status.value,
                "no_execution_live": True,
                "command_not_authorized": context.command_state != "AUTHORIZED",
            },
        )
        payload = dict(revision.payload)
        payload["revision_id"] = self._ids.new_id()
        payload["scheduled_at_ms"] = scheduled_at_ms
        payload["deadline_at_ms"] = deadline_at_ms
        updated_revision = DeliveryRevision.create(payload)
        revocation = None
        if approval is not None:
            revocation = ApprovalDecision(
                id=self._ids.new_id(),
                revision_id=approval.revision_id,
                payload_hash=approval.payload_hash,
                decision=ApprovalType.REVOKE,
                actor_id=actor,
                created_at_ms=now_ms,
                reason="Slot rescheduled; approval required again.",
                revokes_id=approval.id,
            )
        return DeliveryRescheduleWrite(
            context=context,
            updated_delivery=updated_delivery,
            revision=updated_revision,
            revision_no=context.next_revision_no,
            revocation=revocation,
            cancel_open_command=context.command_state in _OPEN_COMMAND_STATES,
            notification_job_id=self._ids.new_id(),
        )


def reschedule_slot(
    use_case: RescheduleSlot,
    slot_id: str,
    *,
    expected_row_version: int,
    local_date: date,
    local_time: str,
    actor: str,
    correlation_id: str,
) -> RescheduleResult:
    return use_case.execute(
        slot_id,
        expected_row_version=expected_row_version,
        local_date=local_date,
        local_time=local_time,
        actor=actor,
        correlation_id=correlation_id,
    )
