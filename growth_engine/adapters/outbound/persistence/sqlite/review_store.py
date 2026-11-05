from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Any

from growth_engine.application.errors import Conflict, NotFound, PreconditionFailed
from growth_engine.application.ports.clock import IdGenerator
from growth_engine.application.queries.delivery_views import ReviewSnapshotData
from growth_engine.application.review.create_revision import RevisionContext, RevisionDraft, RevisionWrite
from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision, normalize_caption
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.media.asset import MediaVariant, VariantQcStatus
from growth_engine.domain.media.qc import QcDecision, QcReport
from growth_engine.domain.kernel.hashing import canonical_json_bytes, sha256_hex
from growth_engine.adapters.outbound.persistence.sqlite.repositories.jobs import JobRecord


_LIVE_EXECUTIONS = ("AUTHORIZED", "REPORTED", "UNKNOWN")
_OPEN_COMMANDS = ("PENDING", "DELIVERING", "ACKED")


class SqliteReviewStore:
    """SQLite persistence for revision writes and review snapshot reads."""

    def __init__(self, uow_factory: Callable[[], Any], ids: IdGenerator, clock: Any) -> None:
        self._uow_factory = uow_factory
        self._ids = ids
        self._clock = clock

    def load_context(self, delivery_id: str, draft: RevisionDraft) -> RevisionContext | None:
        with self._uow_factory().read_only() as tx:
            row = tx.connection.execute(
                """SELECT d.id, d.state, d.row_version, d.permalink, d.current_revision_id,
                          d.active_approval_id, d.package_id, d.channel_id,
                          c.remote_account_id, cc.id AS channel_config_id, cc.config_hash,
                          s.scheduled_at, s.deadline_at,
                          r.id AS revision_id, r.payload_json AS revision_json,
                          r.payload_hash AS revision_hash, r.revision_no,
                          r.variant_id AS current_variant_id,
                          a.id AS approval_id, a.revision_id AS approval_revision_id,
                          a.payload_hash AS approval_hash, a.decision AS approval_decision,
                          a.actor_id AS approval_actor, a.reason AS approval_reason,
                          a.revokes_id AS approval_revokes_id, a.created_at AS approval_created_at,
                          p.fact_snapshot_hash,
                          EXISTS(SELECT 1 FROM executions e WHERE e.delivery_id=d.id
                            AND e.state IN ('AUTHORIZED','REPORTED','UNKNOWN')) AS live_execution,
                          (SELECT e.state FROM executions e WHERE e.delivery_id=d.id
                            AND e.state IN ('AUTHORIZED','REPORTED','UNKNOWN') LIMIT 1) AS execution_state,
                          (SELECT oc.state FROM outbox_commands oc WHERE oc.delivery_id=d.id
                            ORDER BY oc.created_at DESC LIMIT 1) AS latest_command_state
                   FROM deliveries d
                   JOIN channels c ON c.id=d.channel_id
                   JOIN slot_targets st ON st.id=d.target_id AND st.channel_id=d.channel_id
                   JOIN slots s ON s.id=st.slot_id
                   JOIN content_packages p ON p.id=d.package_id
                   LEFT JOIN channel_configs cc ON cc.channel_id=c.id
                   LEFT JOIN delivery_revisions r ON r.id=d.current_revision_id AND r.delivery_id=d.id
                   LEFT JOIN approval_decisions a ON a.id=d.active_approval_id
                   WHERE d.id=?
                   ORDER BY cc.version DESC LIMIT 1""",
                (delivery_id,),
            ).fetchone()
            if row is None:
                return None
            if not row["channel_config_id"]:
                raise Conflict("Bài chưa có cấu hình kênh để tạo revision.")

            current_revision = (
                None
                if row["revision_id"] is None
                else DeliveryRevision(row["revision_json"], row["revision_hash"])
            )
            effective_caption = draft.caption
            if effective_caption is None and current_revision is not None:
                value = current_revision.payload.get("caption")
                effective_caption = value if isinstance(value, str) else None
            variant_id = draft.variant_id or row["current_variant_id"]
            if not variant_id:
                raise NotFound("Không tìm thấy biến thể ảnh cho revision.")
            variant_row = tx.connection.execute(
                """SELECT id, asset_id, transform_version, sha256, object_key, width, height,
                          mime, byte_size, qc_status, created_at
                   FROM media_variants WHERE id=?""",
                (variant_id,),
            ).fetchone()
            if variant_row is None:
                raise NotFound("Không tìm thấy biến thể ảnh.")
            variant = _variant(variant_row)
            if effective_caption is None:
                raise Conflict("Cần caption để tìm QC report khớp revision.")
            caption_hash = hashlib.sha256(normalize_caption(effective_caption).encode("utf-8")).hexdigest()
            qc_row = tx.connection.execute(
                """SELECT id, variant_id, caption_hash, ruleset_hash, fact_snapshot_hash,
                          decision, coverage_gaps_json, result_json, created_at
                   FROM qc_reports WHERE variant_id=? AND caption_hash=? AND fact_snapshot_hash=?
                   ORDER BY created_at DESC LIMIT 1""",
                (variant.id, caption_hash, row["fact_snapshot_hash"]),
            ).fetchone()
            if qc_row is None:
                raise Conflict("Chưa có QC report khớp caption, facts và biến thể ảnh.")
            approval = None
            if row["approval_id"] is not None:
                approval = ApprovalDecision(
                    id=row["approval_id"],
                    revision_id=row["approval_revision_id"],
                    payload_hash=row["approval_hash"],
                    decision=ApprovalType(row["approval_decision"]),
                    actor_id=row["approval_actor"],
                    created_at_ms=int(row["approval_created_at"]),
                    reason=row["approval_reason"],
                    revokes_id=row["approval_revokes_id"],
                )
            command_state = row["execution_state"] or row["latest_command_state"]
            next_revision_no = int(row["revision_no"] or 0) + 1
            return RevisionContext(
                delivery=Delivery(
                    row["id"], DeliveryState(row["state"]), int(row["row_version"]), row["permalink"]
                ),
                channel_id=row["channel_id"],
                channel_config_id=row["channel_config_id"],
                channel_config_hash=row["config_hash"],
                remote_account_id=row["remote_account_id"],
                next_revision_no=next_revision_no,
                scheduled_at_ms=int(row["scheduled_at"]),
                deadline_at_ms=int(row["deadline_at"]),
                fact_snapshot_hash=row["fact_snapshot_hash"],
                current_revision=current_revision,
                active_approval=approval,
                variant=variant,
                qc_report=_qc_report(qc_row),
                command_state=command_state,
                live_execution=bool(row["live_execution"]),
            )

    def apply_revision(self, write: RevisionWrite) -> None:
        delivery_id = write.context.delivery.id
        revision_id = str(write.revision.payload["revision_id"])
        try:
            with self._uow_factory().begin_immediate() as tx:
                current = tx.connection.execute(
                    """SELECT row_version, state, current_revision_id, active_approval_id, channel_id
                       FROM deliveries WHERE id=?""",
                    (delivery_id,),
                ).fetchone()
                if current is None:
                    raise NotFound("Không tìm thấy bài cần chỉnh sửa.")
                if int(current["row_version"]) != write.expected_row_version:
                    raise PreconditionFailed("Bài đã thay đổi; hãy mở lại bản xem trước.")
                if current["channel_id"] != write.context.channel_id:
                    raise Conflict("Kênh của bài đã thay đổi.")
                if current["current_revision_id"] != (
                    None if write.context.current_revision is None
                    else write.context.current_revision.payload.get("revision_id")
                ):
                    raise PreconditionFailed("Revision hiện hành đã thay đổi.")
                live = tx.connection.execute(
                    """SELECT 1 FROM executions WHERE delivery_id=?
                       AND state IN ('AUTHORIZED','REPORTED','UNKNOWN') LIMIT 1""",
                    (delivery_id,),
                ).fetchone()
                if live is not None:
                    raise Conflict("Bài có execution đang hoạt động, không thể tạo revision mới.")
                if current["active_approval_id"] != (
                    None if write.context.active_approval is None else write.context.active_approval.id
                ):
                    raise PreconditionFailed("Approval hiện hành đã thay đổi.")

                payload = write.revision.payload
                tx.deliveries.save_revision(
                    write.revision,
                    delivery_id=delivery_id,
                    channel_id=write.context.channel_id,
                    revision_no=write.revision_no,
                    channel_config_id=write.context.channel_config_id,
                    variant_id=write.context.variant.id,
                    qc_report_id=write.context.qc_report.id,
                    scheduled_at_ms=write.context.scheduled_at_ms,
                    deadline_at_ms=write.context.deadline_at_ms,
                    caption=str(payload["caption"]),
                    created_by=write.actor,
                    created_at_ms=write.created_at_ms,
                )
                if write.revocation is not None:
                    tx.deliveries.save_approval(write.revocation)
                if write.cancel_open_command:
                    tx.connection.execute(
                        """UPDATE outbox_commands
                           SET state='CANCELLED', lease_owner=NULL, lease_token=NULL,
                               lease_until=NULL, updated_at=?
                           WHERE delivery_id=? AND state IN ('PENDING','DELIVERING','ACKED')""",
                        (write.created_at_ms, delivery_id),
                    )
                new_version = tx.cas_update(
                    "deliveries",
                    delivery_id,
                    expected_row_version=write.expected_row_version,
                    fields={
                        "current_revision_id": revision_id,
                        "active_approval_id": None,
                        "state": write.updated_delivery.state.value,
                        "active": int(write.updated_delivery.active),
                        "updated_at": write.created_at_ms,
                    },
                )
                if new_version != write.updated_delivery.row_version:
                    raise Conflict("Revision version không khớp lần ghi.")

                tx.audit.append(
                    event_id=self._ids.new_id(),
                    aggregate_type="delivery",
                    aggregate_id=delivery_id,
                    actor=write.actor,
                    action="CREATE_REVISION",
                    before_hash=(
                        None if write.context.current_revision is None
                        else write.context.current_revision.payload_hash
                    ),
                    after_hash=write.revision.payload_hash,
                    details_json=json.dumps(
                        {
                            "revision_id": revision_id,
                            "revision_no": write.revision_no,
                            "revoked_approval_id": None if write.revocation is None else write.revocation.id,
                        },
                        separators=(",", ":"),
                    ),
                    correlation_id=f"revision:{delivery_id}:{revision_id}",
                    created_at_ms=write.created_at_ms,
                )
                tx.jobs.save(
                    JobRecord(
                        id=self._ids.new_id(),
                        kind="notify",
                        lane="publish",
                        business_key=f"notify:review:{delivery_id}:{revision_id}",
                        payload_json=canonical_json_bytes(
                            {
                                "type": "REVIEW_NEEDED",
                                "delivery_id": delivery_id,
                                "revision_id": revision_id,
                                "channel_id": write.context.channel_id,
                                "scheduled_at_ms": write.context.scheduled_at_ms,
                            }
                        ).decode("utf-8"),
                        state="PENDING",
                        run_at_ms=write.created_at_ms,
                        created_at_ms=write.created_at_ms,
                        updated_at_ms=write.created_at_ms,
                    )
                )
        except PreconditionFailed:
            raise
        except Conflict:
            raise

    def load_review_data(self, delivery_id: str) -> ReviewSnapshotData | None:
        with self._uow_factory().read_only() as tx:
            row = tx.connection.execute(
                """SELECT d.id, d.state, d.row_version, d.permalink, d.current_revision_id,
                          c.channel_key, c.name AS channel_name, c.remote_account_id,
                          c.enabled AS channel_enabled, c.paused,
                          cc.config_hash,
                          s.scheduled_at, s.deadline_at,
                          r.id AS revision_id, r.payload_json AS revision_json,
                          r.payload_hash AS revision_hash, r.variant_id, v.id AS variant_found,
                          v.asset_id, v.transform_version, v.sha256, v.object_key, v.width,
                          v.height, v.mime, v.byte_size, v.qc_status, v.created_at AS variant_created_at,
                          q.decision AS qc_decision,
                          EXISTS(SELECT 1 FROM executions e WHERE e.delivery_id=d.id
                            AND e.state IN ('AUTHORIZED','REPORTED','UNKNOWN')) AS live_execution,
                          (SELECT oc.state FROM outbox_commands oc WHERE oc.delivery_id=d.id
                            ORDER BY oc.created_at DESC LIMIT 1) AS latest_command_state,
                          p.fact_snapshot_hash
                   FROM deliveries d JOIN channels c ON c.id=d.channel_id
                   JOIN slot_targets st ON st.id=d.target_id AND st.channel_id=d.channel_id
                   JOIN slots s ON s.id=st.slot_id JOIN content_packages p ON p.id=d.package_id
                   LEFT JOIN channel_configs cc ON cc.channel_id=c.id
                   LEFT JOIN delivery_revisions r ON r.id=d.current_revision_id AND r.delivery_id=d.id
                   LEFT JOIN media_variants v ON v.id=r.variant_id
                   LEFT JOIN qc_reports q ON q.id=r.qc_report_id
                   WHERE d.id=? ORDER BY cc.version DESC LIMIT 1""",
                (delivery_id,),
            ).fetchone()
            if row is None:
                return None
            revision = (
                None if row["revision_id"] is None
                else DeliveryRevision(row["revision_json"], row["revision_hash"])
            )
            variant = None if row["variant_found"] is None else _variant_from_row(row)
            active_execution = bool(row["live_execution"])
            facts_valid = True
            if row["revision_id"] is not None:
                fact_rows = tx.connection.execute(
                    "SELECT valid_until FROM package_facts WHERE package_id=?",
                    (tx.connection.execute("SELECT package_id FROM deliveries WHERE id=?", (delivery_id,)).fetchone()[0],),
                ).fetchall()
                facts_valid = all(item["valid_until"] is None or int(item["valid_until"]) >= int(row["scheduled_at"]) for item in fact_rows)
            payload = {} if revision is None else revision.payload
            config_hash_matches = bool(
                revision is not None
                and row["config_hash"]
                and payload.get("channel_config_hash") == row["config_hash"]
            )
            action_context = {
                "permalink": row["permalink"],
                "revision_is_current": revision is not None and row["current_revision_id"] == row["revision_id"],
                "no_execution_live": not active_execution,
                "command_not_authorized": row["latest_command_state"] != "AUTHORIZED" and not active_execution,
                "payload_hash_matches": revision is not None and payload.get("revision_id") == row["revision_id"],
                "qc_status": None if variant is None else variant.qc_status.value,
                "facts_valid_at_scheduled": facts_valid,
                "now_ms": self._clock.now_ms(),
                "scheduled_at_ms": int(row["scheduled_at"]),
                "deadline_at_ms": int(row["deadline_at"]),
                "channel_enabled": bool(row["channel_enabled"]),
                "paused": bool(row["paused"]),
                "config_hash_matches": config_hash_matches,
            }
            if row["qc_decision"] is not None:
                action_context["qc_decision"] = row["qc_decision"]
            return ReviewSnapshotData(
                delivery=Delivery(row["id"], DeliveryState(row["state"]), int(row["row_version"]), row["permalink"]),
                revision=revision,
                channel_key=row["channel_key"],
                channel_name=row["channel_name"],
                remote_account_id=row["remote_account_id"],
                scheduled_at_ms=int(row["scheduled_at"]),
                deadline_at_ms=int(row["deadline_at"]),
                variant=variant,
                action_context=action_context,
            )


def _variant(row: Any) -> MediaVariant:
    return MediaVariant(
        id=row["id"], asset_id=row["asset_id"], transform_version=row["transform_version"],
        sha256=row["sha256"], object_key=row["object_key"], width=int(row["width"]),
        height=int(row["height"]), mime=row["mime"], byte_size=int(row["byte_size"]),
        qc_status=VariantQcStatus(row["qc_status"]), created_at_ms=int(row["created_at"]),
    )


def _variant_from_row(row: Any) -> MediaVariant:
    return MediaVariant(
        id=row["variant_found"], asset_id=row["asset_id"], transform_version=row["transform_version"],
        sha256=row["sha256"], object_key=row["object_key"], width=int(row["width"]),
        height=int(row["height"]), mime=row["mime"], byte_size=int(row["byte_size"]),
        qc_status=VariantQcStatus(row["qc_status"]), created_at_ms=int(row["variant_created_at"]),
    )


def _qc_report(row: Any) -> QcReport:
    gaps = json.loads(row["coverage_gaps_json"])
    if not isinstance(gaps, list) or not all(isinstance(item, str) for item in gaps):
        raise Conflict("QC report có coverage_gaps không hợp lệ.")
    return QcReport(
        id=row["id"], variant_id=row["variant_id"], caption_hash=row["caption_hash"],
        ruleset_hash=row["ruleset_hash"], fact_snapshot_hash=row["fact_snapshot_hash"],
        decision=QcDecision(row["decision"]), coverage_gaps=tuple(gaps),
        result_json=row["result_json"], created_at_ms=int(row["created_at"]),
    )
