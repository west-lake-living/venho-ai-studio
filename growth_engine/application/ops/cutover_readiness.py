from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


_HANOI_PAGE_ID = "1124616474074140"
_HANOI_ROUTE_REF = "GE_MAKE_WEBHOOK_URL_PAGE_A"


@dataclass(frozen=True)
class CutoverReadinessResult:
    ready: bool
    slot_date: str
    slot_time: str
    delivery_id: str | None
    revision_id: str | None
    mapping_dry_run: str
    reasons: tuple[str, ...] = ()
    mapping_target_id: str | None = None
    mapping_route_ref: str | None = None


class CutoverReadiness:
    """Read-only P4 gate for an approved fb_hanoi delivery and exact route mapping."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path).expanduser()

    def execute(self, slot_date: str, slot_time: str = "09:00") -> CutoverReadinessResult:
        if not self._db_path.is_file():
            return CutoverReadinessResult(False, slot_date, slot_time, None, None, "FAIL", ("database_missing",))
        connection = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        reasons: list[str] = []
        try:
            controls = connection.execute(
                "SELECT publish_mode, global_pause FROM runtime_controls WHERE environment='production'"
            ).fetchone()
            if controls is None or controls["publish_mode"] != "DISABLED" or int(controls["global_pause"]) != 1:
                reasons.append("production_controls_not_disabled_and_paused")

            rows = connection.execute(
                """SELECT d.id AS delivery_id, d.state, d.current_revision_id, d.active_approval_id,
                          r.payload_json, r.payload_hash, r.variant_id, r.qc_report_id,
                          c.id AS channel_id, c.channel_key, c.platform, c.remote_account_id,
                          cc.config_hash, cc.caption_profile, cc.make_route_ref,
                          s.local_date, s.local_time,
                          a.id AS approval_id, a.revision_id AS approval_revision_id,
                          a.payload_hash AS approval_payload_hash, a.decision,
                          q.id AS qc_id, q.variant_id AS qc_variant_id, q.decision AS qc_decision,
                          v.sha256 AS variant_sha256
                   FROM deliveries d
                   JOIN slot_targets st ON st.id=d.target_id AND st.channel_id=d.channel_id
                   JOIN slots s ON s.id=st.slot_id
                   JOIN channels c ON c.id=d.channel_id
                   JOIN channel_configs cc ON cc.id=(
                       SELECT current_config.id FROM channel_configs current_config
                       WHERE current_config.channel_id=c.id
                       ORDER BY current_config.version DESC LIMIT 1
                   )
                   JOIN delivery_revisions r ON r.id=d.current_revision_id AND r.delivery_id=d.id
                   LEFT JOIN approval_decisions a ON a.id=d.active_approval_id
                   JOIN media_variants v ON v.id=r.variant_id
                   JOIN qc_reports q ON q.id=r.qc_report_id
                   WHERE c.environment='production' AND c.channel_key='fb_hanoi'
                     AND s.local_date=? AND s.local_time=? AND d.active=1
                   ORDER BY d.created_at DESC LIMIT 1""",
                (slot_date, slot_time),
            ).fetchone()
            if rows is None:
                reasons.append("approved_fb_hanoi_delivery_missing")
                return CutoverReadinessResult(
                    False, slot_date, slot_time, None, None, "FAIL", tuple(reasons)
                )

            payload = json.loads(str(rows["payload_json"]))
            mapping_ok = (
                rows["channel_key"] == "fb_hanoi"
                and rows["platform"] == "facebook"
                and rows["remote_account_id"] == _HANOI_PAGE_ID
                and rows["make_route_ref"] == _HANOI_ROUTE_REF
                and payload.get("channel_id") == rows["channel_id"]
                and payload.get("remote_account_id") == _HANOI_PAGE_ID
                and payload.get("channel_config_hash") == rows["config_hash"]
                and payload.get("channel_config_hash")
            )
            if not mapping_ok:
                reasons.append("slot_mapping_mismatch")
            approved = (
                rows["state"] == "APPROVED"
                and rows["approval_id"] == rows["active_approval_id"]
                and rows["decision"] == "APPROVE"
                and rows["approval_revision_id"] == rows["current_revision_id"]
                and rows["approval_payload_hash"] == rows["payload_hash"]
            )
            if not approved:
                reasons.append("delivery_not_approved_for_current_revision")
            if rows["qc_id"] != rows["qc_report_id"] or rows["qc_variant_id"] != rows["variant_id"]:
                reasons.append("revision_qc_mapping_mismatch")
            if rows["qc_decision"] == "FAIL":
                reasons.append("revision_qc_failed")

            command_count = int(connection.execute(
                "SELECT count(*) FROM outbox_commands WHERE delivery_id=?", (rows["delivery_id"],)
            ).fetchone()[0])
            execution_count = int(connection.execute(
                "SELECT count(*) FROM executions WHERE delivery_id=?", (rows["delivery_id"],)
            ).fetchone()[0])
            if command_count or execution_count:
                reasons.append("dispatch_artifact_exists_for_dry_run_delivery")

            return CutoverReadinessResult(
                not reasons,
                slot_date,
                slot_time,
                str(rows["delivery_id"]),
                str(rows["current_revision_id"]),
                "PASS" if mapping_ok else "FAIL",
                tuple(reasons),
                str(rows["remote_account_id"]),
                str(rows["make_route_ref"]),
            )
        finally:
            connection.close()
