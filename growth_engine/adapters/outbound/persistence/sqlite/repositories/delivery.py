from __future__ import annotations

from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
from growth_engine.domain.delivery.delivery import Delivery
from growth_engine.domain.delivery.revision import DeliveryRevision
from growth_engine.domain.delivery.states import DeliveryState

from ._base import SqliteRepository


class DeliveryRepository(SqliteRepository):
    def save(
        self,
        delivery: Delivery,
        *,
        target_id: str,
        channel_id: str,
        package_id: str,
        created_at_ms: int,
        updated_at_ms: int,
        current_revision_id: str | None = None,
        active_approval_id: str | None = None,
        blocked_reason: str | None = None,
        platform_post_id: str | None = None,
    ) -> None:
        self.connection.execute(
            """INSERT INTO deliveries
               (id, target_id, channel_id, package_id, current_revision_id, active_approval_id,
                state, active, row_version, blocked_reason, platform_post_id, permalink,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                delivery.id,
                target_id,
                channel_id,
                package_id,
                current_revision_id,
                active_approval_id,
                delivery.state.value,
                int(delivery.active),
                delivery.row_version,
                blocked_reason,
                platform_post_id,
                delivery.permalink,
                created_at_ms,
                updated_at_ms,
            ),
        )

    def get(self, delivery_id: str) -> Delivery | None:
        row = self.connection.execute(
            "SELECT id, state, row_version, permalink FROM deliveries WHERE id=?",
            (delivery_id,),
        ).fetchone()
        if row is None:
            return None
        return Delivery(
            id=row["id"],
            state=DeliveryState(row["state"]),
            row_version=row["row_version"],
            permalink=row["permalink"],
        )

    def save_revision(
        self,
        revision: DeliveryRevision,
        *,
        delivery_id: str,
        channel_id: str,
        revision_no: int,
        channel_config_id: str,
        variant_id: str,
        qc_report_id: str,
        scheduled_at_ms: int,
        deadline_at_ms: int,
        caption: str,
        created_by: str,
        created_at_ms: int,
        tracking_url: str | None = None,
    ) -> None:
        self.connection.execute(
            """INSERT INTO delivery_revisions
               (id, delivery_id, channel_id, revision_no, channel_config_id, variant_id,
                qc_report_id, scheduled_at, deadline_at, caption, tracking_url, payload_json,
                payload_hash, created_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(revision.payload["revision_id"]),
                delivery_id,
                channel_id,
                revision_no,
                channel_config_id,
                variant_id,
                qc_report_id,
                scheduled_at_ms,
                deadline_at_ms,
                caption,
                tracking_url,
                revision.payload_json,
                revision.payload_hash,
                created_by,
                created_at_ms,
            ),
        )

    def get_revision(self, revision_id: str) -> DeliveryRevision | None:
        row = self.connection.execute(
            "SELECT payload_json, payload_hash FROM delivery_revisions WHERE id=?",
            (revision_id,),
        ).fetchone()
        if row is None:
            return None
        return DeliveryRevision(payload_json=row["payload_json"], payload_hash=row["payload_hash"])

    def save_approval(self, approval: ApprovalDecision) -> None:
        self.connection.execute(
            """INSERT INTO approval_decisions
               (id, revision_id, payload_hash, decision, actor_id, reason, revokes_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                approval.id,
                approval.revision_id,
                approval.payload_hash,
                approval.decision.value,
                approval.actor_id,
                approval.reason,
                approval.revokes_id,
                approval.created_at_ms,
            ),
        )

    def get_approval(self, approval_id: str) -> ApprovalDecision | None:
        row = self.connection.execute(
            """SELECT id, revision_id, payload_hash, decision, actor_id, reason, revokes_id,
                      created_at
               FROM approval_decisions WHERE id=?""",
            (approval_id,),
        ).fetchone()
        if row is None:
            return None
        return ApprovalDecision(
            id=row["id"],
            revision_id=row["revision_id"],
            payload_hash=row["payload_hash"],
            decision=ApprovalType(row["decision"]),
            actor_id=row["actor_id"],
            reason=row["reason"],
            revokes_id=row["revokes_id"],
            created_at_ms=row["created_at"],
        )
