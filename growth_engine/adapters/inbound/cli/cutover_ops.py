from __future__ import annotations

import sqlite3
import tempfile
import time
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit

from growth_engine.bootstrap import build_backup_alert, build_backup_tools, build_offsite_tools
from growth_engine.application.ops.cutover_readiness import CutoverReadiness
from growth_engine.domain.publishing.runtime_mode import PublishMode
from growth_engine.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]

TARGETS = {
    "fb_hanoi": ("facebook", "1124616474074140", "GE_MAKE_WEBHOOK_URL_PAGE_A"),
    "fb_venho": ("facebook", "803531149684177", "GE_MAKE_WEBHOOK_URL_PAGE_B"),
    "ig_venho": ("instagram", "17841457936965829", "GE_MAKE_WEBHOOK_URL_IG_VENHO"),
}


def now_ms() -> int:
    return time.time_ns() // 1_000_000


def database(settings: Settings) -> Path:
    path = Path(settings.db_path)
    if settings.env != "production" or not path.is_absolute() or not path.is_file():
        raise ValueError("production_database_required")
    return path


def fresh_backup(settings: Settings) -> Path:
    _, _, staged_backups, staging_directory = build_backup_tools()
    copies = staged_backups(staging_directory(database(settings)))
    if not copies or not 0 <= now_ms() - copies[0][0] < 3_600_000:
        raise ValueError("backup_missing_or_at_least_one_hour_old")
    return copies[0][1]


def backup(settings: Settings) -> dict:
    service, _, _, _ = build_backup_tools()
    copy = service.stage(db_path=database(settings), media_root=Path(settings.media_root), now_ms=now_ms())
    return {"result": "PASS", "snapshot": copy.destination.name, "artifacts": copy.artifact_count}


def offsite_backup(settings: Settings) -> dict:
    offsite = build_offsite_tools()
    return offsite.upload_latest(database(settings), REPO_ROOT, offsite.GoogleDrive.from_env,
                                  alert=build_backup_alert(settings))


def create_offsite_folder(settings: Settings) -> dict:
    database(settings)
    offsite = build_offsite_tools()
    try:
        folder = offsite.GoogleDrive.from_env().create_folder()
    except offsite.OffsiteError:
        raise
    except Exception:
        raise ValueError("offsite_drive_folder_create_failed") from None
    if not offsite.DRIVE_ID.fullmatch(folder):
        raise ValueError("offsite_drive_folder_invalid")
    return {"result": "PASS", "folder_id": folder}


def check_offsite_folder(settings: Settings, candidate: str | None) -> dict:
    database(settings)
    offsite = build_offsite_tools()
    folder = offsite.folder_id(candidate)
    try:
        offsite.GoogleDrive.from_env().check_folder(folder)
    except offsite.OffsiteError:
        raise
    except Exception:
        raise ValueError("offsite_drive_folder_check_failed") from None
    return {"result": "PASS"}


def require_offsite(settings: Settings) -> dict:
    offsite = build_offsite_tools()
    return offsite.require_fresh_remote(database(settings), REPO_ROOT, now_ms, offsite.GoogleDrive.from_env)


def offsite_status(settings: Settings) -> dict:
    receipt = require_offsite(settings)
    return {"result": "PASS", "snapshot": receipt["name"], "checksum": "PASS",
            "sha256": receipt["sha256"], "md5": receipt["md5"]}


def offsite_warning(settings: Settings) -> str:
    offsite = build_offsite_tools()
    try:
        recipient, checksum = offsite.load_recipient(REPO_ROOT)
        offsite.check_recipient(recipient)
    except offsite.OffsiteError as error:
        return f"WARN: {error}"
    receipt, reason = offsite.receipt_status(database(settings), checksum, now_ms())
    return "PASS" if receipt else f"WARN: {reason}"


def rehearsal(settings: Settings) -> dict:
    snapshot = fresh_backup(settings)
    _, service, _, _ = build_backup_tools()
    with tempfile.TemporaryDirectory(prefix="gc2-rehearsal-") as temporary:
        result = service.restore_archive(
            archive=snapshot, target=Path(temporary) / "restore", now_ms=now_ms()
        )
        if result.dispatch_epochs_rotated < 1:
            raise ValueError("restored_controls_missing")
    return {"result": "PASS", "snapshot": snapshot.name, "integrity_check": "ok",
            "foreign_key_check": "ok", "artifact_check": "ok", "dispatch_epochs_rotated": result.dispatch_epochs_rotated}


def state(settings: Settings, date: str) -> dict:
    db = database(settings)
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN")
        controls = connection.execute(
            "SELECT publish_mode, global_pause, dispatch_epoch FROM runtime_controls WHERE environment='production'"
        ).fetchone()
        if controls is None:
            raise ValueError("production_controls_missing")
        channels = [dict(row) for row in connection.execute(
            """SELECT c.channel_key, c.platform, c.remote_account_id, c.enabled, c.paused, cc.make_route_ref
               FROM channels c LEFT JOIN channel_configs cc ON cc.id=(
                 SELECT id FROM channel_configs WHERE channel_id=c.id ORDER BY version DESC LIMIT 1
               ) WHERE c.environment='production' ORDER BY c.channel_key"""
        )]
        deliveries = []
        for row in connection.execute(
            """SELECT d.id, c.channel_key, d.state, d.platform_post_id
               FROM deliveries d JOIN channels c ON c.id=d.channel_id
               JOIN slot_targets t ON t.id=d.target_id JOIN slots s ON s.id=t.slot_id
               WHERE c.environment='production' AND s.local_date=? AND s.local_time='09:00' AND d.active=1
               ORDER BY c.channel_key""",
            (date,),
        ):
            item = dict(row)
            for key, query in {
                "commands": "SELECT id,state FROM outbox_commands WHERE delivery_id=? ORDER BY sequence_no",
                "executions": "SELECT id,state,external_outcome FROM executions WHERE delivery_id=?",
                "receipts": "SELECT id,execution_id,processing_state FROM receipt_inbox WHERE execution_id IN (SELECT id FROM executions WHERE delivery_id=?)",
                "verifications": """SELECT execution_id,source,existence,ownership,media_present,caption_match,quality
                                    FROM publication_verifications WHERE delivery_id=? ORDER BY checked_at,id""",
            }.items():
                item[key] = [dict(result) for result in connection.execute(query, (row["id"],))]
            deliveries.append(item)
        grants = connection.execute(
            """SELECT count(*) FROM executions e JOIN deliveries d ON d.id=e.delivery_id
               JOIN channels c ON c.id=d.channel_id WHERE c.environment='production'"""
        ).fetchone()[0]
    return {"result": "PASS", "slot_date": date, "controls": dict(controls), "channels": channels,
            "deliveries": deliveries, "production_grants": grants}


def verified_hanoi(settings: Settings, date: str) -> dict:
    status = state(settings, date)
    rows = [row for row in status["deliveries"] if row["channel_key"] == "fb_hanoi"]
    if len(rows) != 1:
        raise ValueError("hanoi_delivery_missing_or_ambiguous")
    row = rows[0]
    reported = {item["id"] for item in row["executions"]
                if item["state"] == "REPORTED" and item["external_outcome"] == "POST_CREATED"}
    applied = {item["execution_id"] for item in row["receipts"] if item["processing_state"] == "APPLIED"}
    verified = {item["execution_id"] for item in row["verifications"]
                if item["existence"] == "EXISTS" and item["ownership"] == "MATCH"}
    if (row["state"] != "PUBLISHED"
        or not str(row["platform_post_id"]).startswith(TARGETS["fb_hanoi"][1] + "_")
        or not reported & applied & verified):
        raise ValueError("hanoi_receipt_or_verification_not_confirmed")
    return status


def gate(settings: Settings, action: str, date: str, *, actor: str, correlation_id: str) -> dict:
    from growth_engine.bootstrap import build_container

    database(settings)
    container = build_container(settings).operator_controls
    audit = {"actor": actor, "correlation_id": correlation_id}
    # Pause first for rollback, then check for grants against the now-closed authorization gate.
    if action == "pause":
        container.pause(**audit)
        return state(settings, date)
    status = state(settings, date)
    if status["controls"]["global_pause"] != 1:
        raise ValueError("global_pause_required")
    if action == "rollback":
        if status["production_grants"]:
            raise ValueError("production_grant_exists_use_forward_recovery")
        container.set_mode(PublishMode.DISABLED, **audit)
    elif action == "epoch":
        fresh_backup(settings)
        if status["controls"]["publish_mode"] != "DISABLED" or status["production_grants"]:
            raise ValueError("epoch_requires_disabled_and_no_grants")
        container.bump_epoch(**audit)
    elif action == "dry-run":
        if status["controls"]["publish_mode"] not in {"DISABLED", "DRY_RUN"} or status["production_grants"]:
            raise ValueError("dry_run_requires_no_grants")
        fresh_backup(settings)
        container.set_mode(PublishMode.DRY_RUN, **audit)
    elif action in {"live-hanoi", "resume-hanoi", "resume-all"}:
        fresh_backup(settings)
        enabled = {row["channel_key"] for row in status["channels"] if row["enabled"] and not row["paused"]}
        expected = set(TARGETS) if action == "resume-all" else {"fb_hanoi"}
        if enabled != expected or any(row["enabled"] and row["paused"] for row in status["channels"]):
            raise ValueError("unexpected_enabled_channels")
        expected_mode = "DRY_RUN" if action == "live-hanoi" else "LIVE_MANUAL"
        if status["controls"]["publish_mode"] != expected_mode:
            raise ValueError("unexpected_publish_mode")
        if pending_gate(settings, date, approved=True, channels=expected)["result"] != "PASS":
            raise ValueError("approved_slot_gate_failed")
        if action == "resume-all":
            require_offsite(settings)
        if action == "live-hanoi":
            container.set_mode(PublishMode.LIVE_MANUAL, **audit)
        else:
            container.resume(**audit)
    else:
        raise ValueError("unrecognized_cutover_action")
    return state(settings, date)


def pending_gate(
    settings: Settings, date: str, *, approved: bool = False, channels: set[str] | None = None,
    require_disabled: bool = False,
) -> dict:
    fresh_backup(settings)
    status = state(settings, date)
    expected = channels or {"fb_hanoi"}
    readiness = CutoverReadiness(database(settings))
    snapshots = [readiness.execute(date, require_approval=approved, require_disabled=False,
                                   channel_key=key, target_id=TARGETS[key][1], route_ref=TARGETS[key][2])
                 for key in sorted(expected)]
    overdue = sorted({row.delivery_id for snapshot in snapshots for row in snapshot.overdue_deliveries})
    mapped = {
        row["channel_key"]: (row["platform"], row["remote_account_id"], row["make_route_ref"])
        for row in status["channels"]
    }
    reasons = sorted({reason for snapshot in snapshots for reason in snapshot.reasons})
    if mapped != TARGETS:
        reasons.append("production_mapping_mismatch")
    # All three routes belong to the one production scenario. Never include URLs in the result.
    configured_urls = {settings.make_webhook_urls.get(ref.removeprefix("GE_MAKE_WEBHOOK_URL_"), "").strip()
                       for _, _, ref in TARGETS.values()}
    if any(not endpoint.startswith("https://") or not urlsplit(endpoint).hostname or
           "REQUIRED_FROM_P0" in endpoint for endpoint in configured_urls):
        reasons.append("production_make_route_ref_missing")
    elif len(configured_urls) != 1:
        reasons.append("production_routes_do_not_share_one_webhook")
    if overdue:
        reasons.append("overdue_nonterminal_deliveries")
    if status["controls"]["global_pause"] != 1:
        reasons.append("global_pause_required")
    if require_disabled and status["controls"]["publish_mode"] != "DISABLED":
        reasons.append("production_not_disabled")
    if {row["channel_key"] for row in status["deliveries"]} != expected:
        reasons.append("unexpected_slot_targets")
    if approved and any(row["state"] != "APPROVED" for row in status["deliveries"]):
        reasons.append("slot_targets_not_approved")
    return {**status, "result": "FAIL" if reasons else "PASS", "reasons": reasons,
            "offsite_backup": offsite_warning(settings),
            "overdue_delivery_ids": overdue}
