from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sign_export_payload(secret: str, payload: dict[str, Any]) -> str:
    message = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def export_approved_package(
    package: dict[str, Any],
    *,
    secret: str,
    export_root: Path = Path("data/projects/venho_hotel/growth/exports"),
    now: datetime | None = None,
) -> Path:
    """Export an ALREADY-approved package for cloud fallback dispatch (v3.1 10.4).

    Security invariant: this function only serializes and HMAC-signs a
    package whose approval already happened on the Mac Mini. There is no
    parameter or code path here that sets `approval_status`, so the cloud
    side that later reads this export can only replay the signed command --
    it can never mint a new approval, even in the fallback scenario.
    """
    if package.get("approval_status") != "approved":
        raise ValueError("only approved packages can be exported for cloud fallback")
    timestamp = now or datetime.now(timezone.utc)
    payload = {
        "content_package_id": package["content_package_id"],
        "publication_command": package["publication_command"],
        "approved_at": package["approved_at"],
        "exported_at": timestamp.isoformat(),
    }
    signature = sign_export_payload(secret, payload)
    signed = {**payload, "signature": signature}
    path = export_root / timestamp.strftime("%Y") / timestamp.strftime("%m") / package["content_package_id"] / "export.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(signed, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def verify_export_signature(payload: dict[str, Any], signature: str, *, secret: str) -> bool:
    body = {key: value for key, value in payload.items() if key != "signature"}
    expected = sign_export_payload(secret, body)
    return hmac.compare_digest(expected, signature)
