from __future__ import annotations

from datetime import datetime, timedelta, timezone


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def add_window(published_timestamp: str, window: str) -> str:
    published = parse_utc(published_timestamp)
    if window.endswith("h"):
        return utc_iso(published + timedelta(hours=int(window[:-1])))
    if window.endswith("d"):
        return utc_iso(published + timedelta(days=int(window[:-1])))
    raise ValueError(f"unsupported analytics window: {window}")


def days_since(published_timestamp: str, snapshot_timestamp_utc: str) -> int:
    delta = parse_utc(snapshot_timestamp_utc) - parse_utc(published_timestamp)
    return max(0, int(delta.total_seconds() // 86400))
