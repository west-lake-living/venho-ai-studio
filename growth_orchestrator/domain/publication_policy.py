from __future__ import annotations

import hashlib


def publication_idempotency_key(*, brand: str, platform: str, account: str, content_package_id: str, copy_version_id: str, asset_version_id: str, scheduled_at: str) -> str:
    raw = "|".join([brand, platform, account, content_package_id, copy_version_id, asset_version_id, scheduled_at])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
