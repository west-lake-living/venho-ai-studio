from __future__ import annotations

import hashlib
import json
from datetime import datetime


def approve_exact_versions(package: dict, *, approved_by: str) -> dict:
    if package.get("state") != "READY_FOR_REVIEW":
        raise ValueError("Package is not ready for review")
    snapshot = {
        "content_package_id": package["id"],
        "copy_version_ids": package.get("copy_version_ids") or [package.get("selected_copy_candidate_id")],
        "asset_version_ids": package.get("asset_version_ids", []),
        "validation_snapshot_id": package.get("validation_snapshot_id") or "validation-inline",
    }
    checksum = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "approval_request_id": f"approval-{package['id']}",
        **snapshot,
        "status": "approved",
        "checksum": checksum,
        "approved_by": approved_by,
        "approved_at": datetime.now().isoformat(),
    }
