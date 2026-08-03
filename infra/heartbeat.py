from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable


def build_heartbeat_payload(*, host_id: str, now: datetime | None = None) -> dict[str, Any]:
    timestamp = now or datetime.now(timezone.utc)
    return {"host_id": host_id, "sent_at": timestamp.isoformat(), "status": "alive"}


def send_heartbeat(
    *,
    host_id: str,
    http_post: Callable[..., dict[str, Any]],
    endpoint: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Send a heartbeat to the cloud deadman-switch endpoint.

    `http_post` is always injected by the caller (a real script wires in
    `requests.post`) so this stays a pure, mockable unit in tests -- no
    network call happens unless the caller supplies one.
    """
    payload = build_heartbeat_payload(host_id=host_id, now=now)
    return http_post(endpoint, json=payload)


def is_heartbeat_stale(last_heartbeat_at: str, *, now: datetime, stale_after_minutes: int = 15) -> bool:
    last = datetime.fromisoformat(last_heartbeat_at)
    return (now - last).total_seconds() > stale_after_minutes * 60
