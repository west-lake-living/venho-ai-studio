from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone


def _canonical_package_versions(package: dict) -> dict:
    return {
        "content_package_id": package["id"],
        "copy_version_ids": list(package.get("copy_version_ids", [])),
        "asset_version_ids": list(package.get("asset_version_ids", [])),
        "validation_snapshot_id": package.get("validation_snapshot_id"),
        "fact_version_ids": list(package.get("fact_version_ids", [])),
        "brief_version_id": package.get("brief_version_id"),
    }


def package_versions_checksum(package: dict) -> str:
    payload = _canonical_package_versions(package)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def create_approval_snapshot(package: dict, *, approved_by: str | None = None) -> dict:
    version_payload = _canonical_package_versions(package)
    snapshot = {
        "approval_request_id": f"approval-{package['id']}",
        **version_payload,
        "status": "approved" if approved_by else "pending",
        "approved_by": approved_by,
        "approved_at": datetime.now(timezone.utc).isoformat() if approved_by else None,
        "revoked_reason": None,
        "package_versions_checksum": package_versions_checksum(package),
    }
    snapshot["checksum"] = hashlib.sha256(json.dumps(snapshot, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return snapshot


def revoke_if_versions_changed(snapshot: dict, package: dict) -> dict:
    if snapshot.get("package_versions_checksum") == package_versions_checksum(package):
        return snapshot
    for field, reason in [
        ("copy_version_ids", "copy_version_changed"),
        ("asset_version_ids", "asset_version_changed"),
        ("validation_snapshot_id", "validation_snapshot_changed"),
        ("fact_version_ids", "fact_version_changed"),
        ("brief_version_id", "brief_version_changed"),
    ]:
        if snapshot.get(field) != _canonical_package_versions(package).get(field):
            return {**snapshot, "status": "revoked", "revoked_reason": reason}
    return {**snapshot, "status": "revoked", "revoked_reason": "package_versions_changed"}


def assert_dispatch_allowed(snapshot: dict, package: dict) -> None:
    current = revoke_if_versions_changed(snapshot, package)
    if current.get("status") != "approved":
        reason = current.get("revoked_reason") or current.get("status") or "approval_not_valid"
        raise ValueError(f"dispatch blocked: {reason}")


def build_final_review_state(package: dict, snapshot: dict | None, validation_report: dict | None = None) -> dict:
    if snapshot is None:
        status = "PENDING_APPROVAL"
        reason = "missing_approval_snapshot"
    else:
        current = revoke_if_versions_changed(snapshot, package)
        status = "APPROVED" if current.get("status") == "approved" else "BLOCKED"
        reason = current.get("revoked_reason")
    if validation_report and validation_report.get("verdict") not in {"READY_FOR_REVIEW", "APPROVED"}:
        status = "BLOCKED"
        reason = "validation_not_ready"
    return {
        "content_package_id": package["id"],
        "status": status,
        "reason": reason,
        "version_checksum": package_versions_checksum(package),
    }
