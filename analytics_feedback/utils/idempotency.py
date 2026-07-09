from __future__ import annotations

import hashlib


def snapshot_id(package_id: str, platform: str, snapshot_timestamp_utc: str) -> str:
    raw = f"{package_id}:{platform}:{snapshot_timestamp_utc}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
