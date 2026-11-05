from __future__ import annotations

import json
import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from growth_engine.application.errors import Conflict, NotFound, PreconditionFailed
from growth_engine.application.ports.clock import IdGenerator
from growth_engine.application.review.approve_group import (
    ApprovalBatchResult,
    ApprovalConflict,
    ApprovalItem,
)
from growth_engine.application.review.cancel_delivery import CancelWrite
from growth_engine.application.review.reject_revision import RejectContext, RejectionWrite
from growth_engine.application.review.revoke_approval import RevokeWrite
from growth_engine.application.scheduling.reschedule_slot import (
    RescheduleContext,
    RescheduleDeliveryContext,
    RescheduleWrite,
)
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.kernel.hashing import canonical_json_bytes
from growth_engine.domain.media.asset import MediaVariant, VariantQcStatus
from growth_engine.domain.media.qc import QcDecision, QcReport
from growth_engine.domain.scheduling.slot import Slot
from growth_engine.adapters.outbound.persistence.sqlite.repositories.jobs import JobRecord


_LIVE = ("AUTHORIZED", "REPORTED", "UNKNOWN")
_OPEN = ("PENDING", "DELIVERING", "ACKED")


@dataclass(frozen=True)
class _WorkflowContext:
    delivery: Delivery
    current_revision: DeliveryRevision | None
    current_revision_id: str | None
    active_approval: ApprovalDecision | None
    command_state: str | None
    live_execution: bool


class SqliteReviewWorkflowStore:
    """BEGIN IMMEDIATE adapters for approval and delivery review mutations."""

    def __init__(self, uow_factory: Callable[[], Any], ids: IdGenerator) -> None:
        self._uow_factory = uow_factory
        self._ids = ids

    def load_context(self, delivery_id: str) -> _WorkflowContext | None:
        with self._uow_factory().read_only() as tx:
            return self._load_context(tx.connection, delivery_id)

    def apply_rejection(self, write: RejectionWrite) -> None:
        delivery_id = write.context.delivery.id
        with self._uow_factory().begin_immediate() as tx:
            current = self._require_current(
                tx.connection, delivery_id, write.context.delivery.row_version,
                write.expected_revision_id,
            )
            if current["state"] != "IN_REVIEW":
                raise Conflict("Chỉ có thể từ chối bài đang chờ duyệt.")
            self._ensure_no_live_execution(tx.connection, delivery_id)
            tx.deliveries.save_approval(write.decision)
            fields: dict[str, object] = {
                "state": write.updated_delivery.state.value,
                "updated_at": write.created_at_ms,
            }
            if write.replacement_delivery_id is not None:
                fields.update({"active": 0, "active_approval_id": None})
            version = tx.cas_update(
                "deliveries", delivery_id,
                expected_row_version=write.context.delivery.row_version,
                fields=fields,
            )
            if version != write.updated_delivery.row_version:
                raise Conflict("Delivery version không khớp lần từ chối.")
            if write.replacement_delivery_id is not None:
                replacement = Delivery(write.replacement_delivery_id, DeliveryState.DRAFT)
                tx.deliveries.save(
                    replacement,
                    target_id=current["target_id"],
                    channel_id=current["channel_id"],
                    package_id=current["package_id"],
                    created_at_ms=write.created_at_ms,
                    updated_at_ms=write.created_at_ms,
                )
            if write.job_id is not None and write.job_kind is not None:
                self._save_job(
                    tx,
                    job_id=write.job_id,
                    kind=write.job_kind,
                    lane="jobs",
                    business_key=f"review:{delivery_id}:{write.expected_revision_id}:{write.job_kind}",
                    payload={
                        "delivery_id": delivery_id,
                        "revision_id": write.expected_revision_id,
                        "replacement_delivery_id": write.replacement_delivery_id,
                        "reason": write.decision.reason,
                        "_synthetic": False,
                    },
                    at_ms=write.created_at_ms,
                )
            self._append_audit(
                tx,
                aggregate_id=delivery_id,
                actor=write.actor,
                action="REJECT_REVISION",
                before_hash=write.context.current_revision.payload_hash,
                after_hash=write.context.current_revision.payload_hash,
                details={
                    "revision_id": write.expected_revision_id,
                    "replace_mode": write.replace_mode.value,
                    "replacement_delivery_id": write.replacement_delivery_id,
                },
                correlation_id=write.correlation_id,
                at_ms=write.created_at_ms,
            )

    def apply_revocation(self, write: RevokeWrite) -> None:
        delivery_id = write.context.delivery.id
        revision_id = str(write.context.current_revision.payload["revision_id"])
        with self._uow_factory().begin_immediate() as tx:
            current = self._require_current(
                tx.connection, delivery_id, write.expected_row_version, revision_id
            )
            if current["active_approval_id"] != write.context.active_approval.id:
                raise PreconditionFailed("Approval hiện hành đã thay đổi.")
            self._ensure_no_live_execution(tx.connection, delivery_id)
            tx.deliveries.save_approval(write.revocation)
            if write.cancel_open_command:
                self._cancel_commands(tx.connection, delivery_id, write.created_at_ms)
            self._cas_delivery(
                tx, delivery_id, write.expected_row_version, write.updated_delivery,
                write.created_at_ms, active_approval_id=None,
            )
            self._append_audit(
                tx, aggregate_id=delivery_id, actor=write.actor, action="REVOKE_APPROVAL",
                before_hash=write.context.current_revision.payload_hash,
                after_hash=write.context.current_revision.payload_hash,
                details={"revocation_id": write.revocation.id, "reason": write.reason},
                correlation_id=write.correlation_id, at_ms=write.created_at_ms,
            )

    def apply_cancellation(self, write: CancelWrite) -> None:
        delivery_id = write.context.delivery.id
        with self._uow_factory().begin_immediate() as tx:
            current = self._require_current(tx.connection, delivery_id, write.expected_row_version)
            self._ensure_no_live_execution(tx.connection, delivery_id)
            if write.cancel_open_command:
                self._cancel_commands(tx.connection, delivery_id, write.cancelled_at_ms)
            self._cas_delivery(
                tx, delivery_id, write.expected_row_version, write.updated_delivery,
                write.cancelled_at_ms,
            )
            self._append_audit(
                tx, aggregate_id=delivery_id, actor=write.actor, action="CANCEL_DELIVERY",
                before_hash=None, after_hash=None,
                details={"reason": write.reason, "previous_state": current["state"]},
                correlation_id=write.correlation_id, at_ms=write.cancelled_at_ms,
            )

    def approve_batch(
        self,
        items: tuple[ApprovalItem, ...],
        *,
        actor: str,
        principal: str,
        idempotency_key: str,
        request_hash: str,
        approved_at_ms: int,
    ) -> ApprovalBatchResult:
        from growth_engine.adapters.outbound.persistence.sqlite.repositories.idempotency import (
            IdempotencyResult,
        )

        with self._uow_factory().begin_immediate() as tx:
            reserved = tx.idempotency.get_or_reserve(
                principal, "approval.batch", idempotency_key, request_hash,
                now_ms=approved_at_ms, expires_at_ms=approved_at_ms + 24 * 60 * 60 * 1000,
            )
            if reserved.kind == "MISMATCH":
                raise DomainError(ErrorCode.IDEMPOTENCY_MISMATCH, "Idempotency-Key đã dùng với batch khác.")
            if reserved.kind == "REPLAY":
                data = json.loads(reserved.response_json or "null")
                return _approval_result(data)

            conflicts: list[ApprovalConflict] = []
            contexts: list[tuple[ApprovalItem, Any, Any]] = []
            for item in items:
                row = self._approval_context(tx.connection, item.delivery_id)
                reason = self._approval_conflict(row, item, approved_at_ms)
                if reason is not None:
                    conflicts.append(ApprovalConflict(
                        item.delivery_id, reason,
                        None if row is None else int(row["row_version"]),
                    ))
                else:
                    contexts.append((item, row, row["active_approval_id"]))
            if conflicts:
                result = ApprovalBatchResult(conflicts=tuple(conflicts))
                tx.idempotency.save_response(
                    principal, "approval.batch", idempotency_key,
                    request_hash=request_hash, response_status=409,
                    response_json=json.dumps({
                        "approvals": [],
                        "conflicts": [item.as_dict() for item in conflicts],
                    }, separators=(",", ":")),
                )
                return result

            approvals: list[ApprovalDecision] = []
            for item, row, _active in contexts:
                approval = ApprovalDecision(
                    id=self._ids.new_id(), revision_id=item.revision_id,
                    payload_hash=item.payload_hash, decision=ApprovalType.APPROVE,
                    actor_id=actor, created_at_ms=approved_at_ms,
                )
                tx.deliveries.save_approval(approval)
                tx.cas_update(
                    "deliveries", item.delivery_id,
                    expected_row_version=item.expected_row_version,
                    fields={
                        "state": DeliveryState.APPROVED.value,
                        "active_approval_id": approval.id,
                        "updated_at": approved_at_ms,
                    },
                )
                self._append_audit(
                    tx, aggregate_id=item.delivery_id, actor=actor, action="APPROVE_REVISION",
                    before_hash=None, after_hash=item.payload_hash,
                    details={"revision_id": item.revision_id, "approval_id": approval.id},
                    correlation_id=f"approval:{principal}:{idempotency_key}", at_ms=approved_at_ms,
                )
                approvals.append(approval)
            serialized = {
                "approvals": [_approval_dict(item) for item in approvals],
                "conflicts": [],
            }
            tx.idempotency.save_response(
                principal, "approval.batch", idempotency_key,
                request_hash=request_hash, response_status=200,
                response_json=json.dumps(serialized, separators=(",", ":")),
            )
            return ApprovalBatchResult(approvals=tuple(approvals))

    def _load_context(self, connection: Any, delivery_id: str) -> _WorkflowContext | None:
        row = connection.execute(
            """SELECT d.id, d.state, d.row_version, d.permalink, d.current_revision_id,
                      d.active_approval_id, r.payload_json, r.payload_hash,
                      a.id AS approval_id, a.revision_id AS approval_revision_id,
                      a.payload_hash AS approval_hash, a.decision AS approval_decision,
                      a.actor_id, a.reason, a.revokes_id, a.created_at,
                      (SELECT e.state FROM executions e WHERE e.delivery_id=d.id
                        AND e.state IN ('AUTHORIZED','REPORTED','UNKNOWN') LIMIT 1) AS execution_state,
                      EXISTS(SELECT 1 FROM executions e WHERE e.delivery_id=d.id
                        AND e.state IN ('AUTHORIZED','REPORTED','UNKNOWN')) AS live_execution,
                      (SELECT oc.state FROM outbox_commands oc WHERE oc.delivery_id=d.id
                        ORDER BY oc.created_at DESC LIMIT 1) AS command_state
               FROM deliveries d LEFT JOIN delivery_revisions r
                 ON r.id=d.current_revision_id AND r.delivery_id=d.id
               LEFT JOIN approval_decisions a ON a.id=d.active_approval_id WHERE d.id=?""",
            (delivery_id,),
        ).fetchone()
        if row is None:
            return None
        revision = (
            None if row["payload_json"] is None
            else DeliveryRevision(row["payload_json"], row["payload_hash"])
        )
        approval = None
        if row["approval_id"] is not None:
            approval = ApprovalDecision(
                row["approval_id"], row["approval_revision_id"], row["approval_hash"],
                ApprovalType(row["approval_decision"]), row["actor_id"],
                int(row["created_at"]), row["reason"], row["revokes_id"],
            )
        return _WorkflowContext(
            Delivery(row["id"], DeliveryState(row["state"]), int(row["row_version"]), row["permalink"]),
            revision, row["current_revision_id"], approval,
            row["execution_state"] or row["command_state"], bool(row["live_execution"]),
        )

    def _approval_context(self, connection: Any, delivery_id: str):
        return connection.execute(
            """SELECT d.id, d.state, d.row_version, d.current_revision_id, d.active_approval_id,
                      r.payload_json, r.payload_hash, r.variant_id, r.qc_report_id,
                      c.enabled, c.paused, cc.config_hash, s.scheduled_at, s.deadline_at,
                      v.qc_status, v.sha256 AS variant_sha256,
                      q.variant_id AS qc_variant_id, q.decision AS qc_decision, q.caption_hash,
                      p.fact_snapshot_hash,
                      NOT EXISTS(SELECT 1 FROM package_facts pf WHERE pf.package_id=p.id
                        AND pf.valid_until IS NOT NULL AND pf.valid_until<=s.scheduled_at) AS facts_valid,
                      EXISTS(SELECT 1 FROM executions e WHERE e.delivery_id=d.id
                        AND e.state IN ('AUTHORIZED','REPORTED','UNKNOWN')) AS live_execution
               FROM deliveries d JOIN channels c ON c.id=d.channel_id
               JOIN slot_targets st ON st.id=d.target_id AND st.channel_id=d.channel_id
               JOIN slots s ON s.id=st.slot_id JOIN content_packages p ON p.id=d.package_id
               LEFT JOIN delivery_revisions r ON r.id=d.current_revision_id AND r.delivery_id=d.id
               LEFT JOIN channel_configs cc ON cc.channel_id=c.id
               LEFT JOIN media_variants v ON v.id=r.variant_id
               LEFT JOIN qc_reports q ON q.id=r.qc_report_id
               WHERE d.id=? ORDER BY cc.version DESC LIMIT 1""",
            (delivery_id,),
        ).fetchone()

    @staticmethod
    def _approval_conflict(row: Any, item: ApprovalItem, now_ms: int) -> str | None:
        if row is None:
            return ErrorCode.NOT_FOUND.value
        if int(row["row_version"]) != item.expected_row_version:
            return ErrorCode.REVISION_CONFLICT.value
        if row["state"] != DeliveryState.IN_REVIEW.value or row["active_approval_id"] is not None:
            return ErrorCode.STATE_CONFLICT.value
        if row["current_revision_id"] != item.revision_id or row["payload_hash"] != item.payload_hash:
            return ErrorCode.REVISION_CONFLICT.value
        if row["live_execution"]:
            return ErrorCode.ALREADY_AUTHORIZED.value
        if not bool(row["enabled"]) or bool(row["paused"]):
            return ErrorCode.STATE_CONFLICT.value
        if row["scheduled_at"] is None or row["deadline_at"] is None or now_ms >= row["deadline_at"]:
            return ErrorCode.DEADLINE_PASSED.value
        if row["qc_status"] not in {VariantQcStatus.PASS.value, VariantQcStatus.REVIEW.value}:
            return ErrorCode.QC_FAILED.value
        if row["qc_decision"] not in {QcDecision.PASS.value, QcDecision.REVIEW.value}:
            return ErrorCode.QC_FAILED.value
        if not row["config_hash"]:
            return ErrorCode.REVISION_CONFLICT.value
        try:
            payload = json.loads(row["payload_json"])
        except (TypeError, json.JSONDecodeError):
            return ErrorCode.REVISION_CONFLICT.value
        if payload.get("channel_config_hash") != row["config_hash"]:
            return ErrorCode.REVISION_CONFLICT.value
        if payload.get("fact_snapshot_hash") != row["fact_snapshot_hash"]:
            return ErrorCode.REVISION_CONFLICT.value
        media = payload.get("media")
        caption = payload.get("caption")
        if (
            not bool(row["facts_valid"])
            or not isinstance(media, list)
            or not media
            or not isinstance(media[0], dict)
            or media[0].get("sha256") != row["variant_sha256"]
            or row["qc_variant_id"] != row["variant_id"]
            or not isinstance(caption, str)
            or row["caption_hash"] != hashlib.sha256(caption.encode("utf-8")).hexdigest()
        ):
            return ErrorCode.REVISION_CONFLICT.value
        return None

    @staticmethod
    def _require_current(connection: Any, delivery_id: str, expected_version: int, revision_id: str | None = None):
        row = connection.execute(
            "SELECT id, row_version, state, current_revision_id, active_approval_id, target_id, channel_id, package_id FROM deliveries WHERE id=?",
            (delivery_id,),
        ).fetchone()
        if row is None:
            raise NotFound("Không tìm thấy bài cần cập nhật.")
        if int(row["row_version"]) != expected_version:
            raise PreconditionFailed("Bài đã thay đổi; hãy tải lại.")
        if revision_id is not None and row["current_revision_id"] != revision_id:
            raise PreconditionFailed("Revision hiện hành đã thay đổi.")
        return row

    @staticmethod
    def _ensure_no_live_execution(connection: Any, delivery_id: str) -> None:
        row = connection.execute(
            "SELECT 1 FROM executions WHERE delivery_id=? AND state IN ('AUTHORIZED','REPORTED','UNKNOWN') LIMIT 1",
            (delivery_id,),
        ).fetchone()
        if row is not None:
            raise Conflict("Bài có execution đang hoạt động.")

    @staticmethod
    def _cancel_commands(connection: Any, delivery_id: str, at_ms: int) -> None:
        connection.execute(
            """UPDATE outbox_commands SET state='CANCELLED', lease_owner=NULL, lease_token=NULL,
               lease_until=NULL, updated_at=? WHERE delivery_id=? AND state IN ('PENDING','DELIVERING','ACKED')""",
            (at_ms, delivery_id),
        )

    @staticmethod
    def _cas_delivery(tx: Any, delivery_id: str, expected: int, delivery: Delivery, at_ms: int,
                      *, active_approval_id: str | None | object = ...) -> None:
        fields: dict[str, object] = {
            "state": delivery.state.value,
            "active": int(delivery.active),
            "updated_at": at_ms,
        }
        if active_approval_id is not ...:
            fields["active_approval_id"] = active_approval_id
        tx.cas_update(
            "deliveries", delivery_id, expected_row_version=expected,
            fields=fields,
        )

    def _append_audit(self, tx: Any, *, aggregate_id: str, actor: str, action: str,
                      before_hash: str | None, after_hash: str | None, details: dict[str, object],
                      correlation_id: str, at_ms: int) -> None:
        tx.audit.append(
            event_id=self._ids.new_id(), aggregate_type="delivery", aggregate_id=aggregate_id,
            actor=actor, action=action, before_hash=before_hash, after_hash=after_hash,
            details_json=json.dumps(details, separators=(",", ":")),
            correlation_id=correlation_id, created_at_ms=at_ms,
        )

    def _save_job(self, tx: Any, *, job_id: str, kind: str, lane: str, business_key: str,
                  payload: dict[str, object], at_ms: int) -> None:
        tx.jobs.save(JobRecord(
            id=job_id, kind=kind, lane=lane, business_key=business_key,
            payload_json=canonical_json_bytes(payload).decode("utf-8"), state="PENDING",
            run_at_ms=at_ms, created_at_ms=at_ms, updated_at_ms=at_ms,
        ))


class SqliteRescheduleStore:
    """SQLite slot/delivery reschedule adapter with one writer transaction."""

    def __init__(self, uow_factory: Callable[[], Any], ids: IdGenerator) -> None:
        self._uow_factory = uow_factory
        self._ids = ids

    def load_context(self, slot_id: str) -> RescheduleContext | None:
        with self._uow_factory().read_only() as tx:
            row = tx.connection.execute(
                "SELECT id, project_id, local_date, local_time, timezone, lane, cadence_version, scheduled_at, deadline_at, cancelled_at, row_version FROM slots WHERE id=?",
                (slot_id,),
            ).fetchone()
            if row is None:
                return None
            slot = Slot(
                row["id"], row["project_id"], date.fromisoformat(row["local_date"]),
                row["local_time"], row["timezone"], row["lane"], row["cadence_version"],
                int(row["scheduled_at"]), int(row["deadline_at"]), row["cancelled_at"],
            )
            deliveries = tx.connection.execute(
                """SELECT d.id, d.state, d.row_version, d.permalink, d.current_revision_id,
                          d.active_approval_id, d.package_id, d.channel_id, r.payload_json,
                          r.payload_hash, r.revision_no, r.variant_id, r.qc_report_id,
                          r.channel_config_id, r.scheduled_at AS revision_scheduled,
                          r.deadline_at AS revision_deadline, v.id AS variant_found,
                          v.asset_id, v.transform_version, v.sha256, v.object_key, v.width,
                          v.height, v.mime, v.byte_size, v.qc_status, v.created_at AS variant_created,
                          q.id AS qc_id, q.caption_hash, q.ruleset_hash, q.fact_snapshot_hash,
                          q.variant_id AS qc_variant_id, q.decision AS qc_decision,
                          q.coverage_gaps_json, q.result_json,
                          q.created_at AS qc_created,
                          a.id AS approval_id, a.revision_id AS approval_revision_id,
                          a.payload_hash AS approval_hash, a.decision AS approval_decision,
                          a.actor_id, a.reason, a.revokes_id, a.created_at AS approval_created,
                          EXISTS(SELECT 1 FROM executions e WHERE e.delivery_id=d.id) AS any_execution,
                          (SELECT e.state FROM executions e WHERE e.delivery_id=d.id
                            AND e.state IN ('AUTHORIZED','REPORTED','UNKNOWN') LIMIT 1) AS execution_state,
                          (SELECT oc.state FROM outbox_commands oc WHERE oc.delivery_id=d.id
                            ORDER BY oc.created_at DESC LIMIT 1) AS command_state
                   FROM deliveries d LEFT JOIN delivery_revisions r
                     ON r.id=d.current_revision_id AND r.delivery_id=d.id
                   LEFT JOIN media_variants v ON v.id=r.variant_id
                   LEFT JOIN qc_reports q ON q.id=r.qc_report_id
                   LEFT JOIN approval_decisions a ON a.id=d.active_approval_id
                   WHERE d.target_id IN (SELECT id FROM slot_targets WHERE slot_id=?) AND d.active=1
                   ORDER BY d.id""",
                (slot_id,),
            ).fetchall()
            items: list[RescheduleDeliveryContext] = []
            for item in deliveries:
                revision = None if item["payload_json"] is None else DeliveryRevision(item["payload_json"], item["payload_hash"])
                variant = None if item["variant_found"] is None else _variant(item)
                qc = None if item["qc_id"] is None else _qc(item)
                approval = None if item["approval_id"] is None else ApprovalDecision(
                    item["approval_id"], item["approval_revision_id"], item["approval_hash"],
                    ApprovalType(item["approval_decision"]), item["actor_id"],
                    int(item["approval_created"]), item["reason"], item["revokes_id"],
                )
                fact_rows = tx.connection.execute(
                    "SELECT valid_until FROM package_facts WHERE package_id=?", (item["package_id"],)
                ).fetchall()
                items.append(RescheduleDeliveryContext(
                    delivery=Delivery(item["id"], DeliveryState(item["state"]), int(item["row_version"]), item["permalink"]),
                    current_revision=revision, variant=variant, qc_report=qc,
                    active_approval=approval, command_state=item["execution_state"] or item["command_state"],
                    has_execution=bool(item["any_execution"]),
                    next_revision_no=int(item["revision_no"] or 0) + 1,
                    facts_valid_until_ms=tuple(int(f["valid_until"]) for f in fact_rows if f["valid_until"] is not None),
                ))
            has_execution = any(item.has_execution for item in items)
            return RescheduleContext(slot, int(row["row_version"]), tuple(items), has_execution)

    def apply_reschedule(self, write: RescheduleWrite) -> None:
        with self._uow_factory().begin_immediate() as tx:
            current_slot = tx.connection.execute(
                "SELECT row_version FROM slots WHERE id=?", (write.context.slot.id,)
            ).fetchone()
            if current_slot is None:
                raise NotFound("Không tìm thấy lịch cần đổi.")
            if int(current_slot["row_version"]) != write.expected_slot_row_version:
                raise PreconditionFailed("Lịch đã thay đổi; hãy tải lại.")
            slot_execution = tx.connection.execute(
                """SELECT 1 FROM executions e JOIN deliveries d ON d.id=e.delivery_id
                   JOIN slot_targets st ON st.id=d.target_id WHERE st.slot_id=? LIMIT 1""",
                (write.context.slot.id,),
            ).fetchone()
            if slot_execution is not None:
                raise Conflict("Không thể đổi lịch khi bất kỳ target nào đã có execution.")
            target_ids = [item.delivery.id for item in write.context.deliveries]
            for delivery_id in target_ids:
                self._ensure_no_execution(tx.connection, delivery_id)
            tx.cas_update(
                "slots", write.context.slot.id,
                expected_row_version=write.expected_slot_row_version,
                fields={
                    "local_date": write.updated_slot.local_date.isoformat(),
                    "local_time": write.updated_slot.local_time,
                    "scheduled_at": write.updated_slot.scheduled_at_ms,
                    "deadline_at": write.updated_slot.deadline_at_ms,
                },
            )
            for item in write.delivery_writes:
                delivery_id = item.context.delivery.id
                revision_id = str(item.revision.payload["revision_id"])
                current = tx.connection.execute(
                    "SELECT current_revision_id, channel_id FROM deliveries WHERE id=?", (delivery_id,)
                ).fetchone()
                if current is None or current["current_revision_id"] != item.context.current_revision.payload.get("revision_id"):
                    raise PreconditionFailed("Revision hiện hành đã thay đổi.")
                config = tx.connection.execute(
                    "SELECT channel_config_id FROM delivery_revisions WHERE id=?", (current["current_revision_id"],)
                ).fetchone()
                if config is None:
                    raise Conflict("Không tìm thấy cấu hình revision hiện hành.")
                payload = item.revision.payload
                tx.deliveries.save_revision(
                    item.revision, delivery_id=delivery_id, channel_id=current["channel_id"],
                    revision_no=item.revision_no, channel_config_id=config["channel_config_id"],
                    variant_id=item.context.variant.id, qc_report_id=item.context.qc_report.id,
                    scheduled_at_ms=write.updated_slot.scheduled_at_ms,
                    deadline_at_ms=write.updated_slot.deadline_at_ms, caption=str(payload["caption"]),
                    created_by=write.actor, created_at_ms=write.changed_at_ms,
                )
                if item.revocation is not None:
                    tx.deliveries.save_approval(item.revocation)
                if item.cancel_open_command:
                    SqliteReviewWorkflowStore._cancel_commands(tx.connection, delivery_id, write.changed_at_ms)
                tx.cas_update(
                    "deliveries", delivery_id,
                    expected_row_version=item.context.delivery.row_version,
                    fields={
                        "current_revision_id": revision_id,
                        "active_approval_id": None,
                        "state": item.updated_delivery.state.value,
                        "updated_at": write.changed_at_ms,
                    },
                )
                tx.jobs.save(JobRecord(
                    id=item.notification_job_id, kind="notify", lane="publish",
                    business_key=f"notify:rescheduled:{delivery_id}:{revision_id}",
                    payload_json=canonical_json_bytes({
                        "type": "REVIEW_NEEDED", "delivery_id": delivery_id,
                        "revision_id": revision_id,
                        "scheduled_at_ms": write.updated_slot.scheduled_at_ms,
                    }).decode("utf-8"),
                    state="PENDING", run_at_ms=write.changed_at_ms,
                    created_at_ms=write.changed_at_ms, updated_at_ms=write.changed_at_ms,
                ))
                self._audit(
                    tx, delivery_id, write.actor, "RESCHEDULE_REVISION",
                    item.context.current_revision.payload_hash, item.revision.payload_hash,
                    {"revision_id": revision_id, "slot_id": write.context.slot.id},
                    write.correlation_id, write.changed_at_ms,
                )
            self._audit(
                tx, write.context.slot.id, write.actor, "RESCHEDULE_SLOT", None, None,
                {"scheduled_at_ms": write.updated_slot.scheduled_at_ms,
                 "deadline_at_ms": write.updated_slot.deadline_at_ms},
                write.correlation_id, write.changed_at_ms, aggregate_type="slot",
            )

    @staticmethod
    def _ensure_no_execution(connection: Any, delivery_id: str) -> None:
        if connection.execute(
            "SELECT 1 FROM executions WHERE delivery_id=? LIMIT 1",
            (delivery_id,),
        ).fetchone() is not None:
            raise Conflict("Không thể đổi lịch khi target có execution.")

    def _audit(self, tx: Any, aggregate_id: str, actor: str, action: str,
               before_hash: str | None, after_hash: str | None, details: dict[str, object],
               correlation_id: str, at_ms: int, aggregate_type: str = "delivery") -> None:
        tx.audit.append(
            event_id=self._ids.new_id(), aggregate_type=aggregate_type, aggregate_id=aggregate_id,
            actor=actor, action=action, before_hash=before_hash, after_hash=after_hash,
            details_json=json.dumps(details, separators=(",", ":")),
            correlation_id=correlation_id, created_at_ms=at_ms,
        )


def _approval_dict(approval: ApprovalDecision) -> dict[str, object]:
    return {
        "id": approval.id, "revision_id": approval.revision_id, "payload_hash": approval.payload_hash,
        "decision": approval.decision.value, "actor_id": approval.actor_id,
        "created_at_ms": approval.created_at_ms, "reason": approval.reason,
        "revokes_id": approval.revokes_id,
    }


def _approval_result(data: dict[str, Any]) -> ApprovalBatchResult:
    conflicts = tuple(
        ApprovalConflict(item["delivery_id"], item["code"], item.get("current_row_version"))
        for item in data.get("conflicts", [])
    )
    approvals = tuple(
        ApprovalDecision(
            item["id"], item["revision_id"], item["payload_hash"],
            ApprovalType(item["decision"]), item["actor_id"], int(item["created_at_ms"]),
            item.get("reason"), item.get("revokes_id"),
        )
        for item in data.get("approvals", [])
    )
    return ApprovalBatchResult(approvals=approvals, replayed=bool(approvals), conflicts=conflicts)


def _variant(row: Any) -> MediaVariant:
    return MediaVariant(
        id=row["variant_found"], asset_id=row["asset_id"], transform_version=row["transform_version"],
        sha256=row["sha256"], object_key=row["object_key"], width=int(row["width"]),
        height=int(row["height"]), mime=row["mime"], byte_size=int(row["byte_size"]),
        qc_status=VariantQcStatus(row["qc_status"]), created_at_ms=int(row["variant_created"]),
    )


def _qc(row: Any) -> QcReport:
    return QcReport(
        id=row["qc_id"], variant_id=row["qc_variant_id"], caption_hash=row["caption_hash"],
        ruleset_hash=row["ruleset_hash"], fact_snapshot_hash=row["fact_snapshot_hash"],
        decision=QcDecision(row["qc_decision"]),
        coverage_gaps=tuple(json.loads(row["coverage_gaps_json"])),
        result_json=row["result_json"], created_at_ms=int(row["qc_created"]),
    )
