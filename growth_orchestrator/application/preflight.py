from __future__ import annotations

from datetime import datetime
from typing import Any


def run_preflight_check(package: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    """08:45 pre-flight gate before 09:00 dispatch (v3.1 9.4, PB-005).

    Every check is deterministic and reads only what the caller already
    resolved onto the package snapshot (fact expiry, approval status, asset
    reachability, event verification, weather validity) -- this function does
    not itself hit the fact store, M04, or any provider.
    """
    failures: list[str] = []

    for fact in package.get("referenced_facts", []):
        valid_to = fact.get("valid_to")
        if valid_to and datetime.fromisoformat(valid_to) <= now:
            failures.append(f"fact_expired:{fact.get('fact_key')}")

    if package.get("approval_status") != "approved":
        failures.append(f"approval_not_valid:{package.get('approval_status')}")

    for asset in package.get("assets", []):
        if not asset.get("reachable", True) or asset.get("hash") != asset.get("expected_hash"):
            failures.append(f"asset_unreachable_or_hash_mismatch:{asset.get('asset_id')}")

    for event in package.get("event_claims", []):
        if not event.get("verified_by_human"):
            failures.append(f"event_not_verified:{event.get('rs_id')}")
            continue
        event_end = event.get("event_end")
        if event_end and datetime.fromisoformat(event_end) < now:
            failures.append(f"event_already_passed:{event.get('rs_id')}")

    weather = package.get("weather_context")
    if weather:
        expires_at = weather.get("expires_at")
        if expires_at and datetime.fromisoformat(expires_at) <= now:
            failures.append(f"weather_signal_expired:{weather.get('rs_id')}")

    return {"passed": not failures, "failures": failures}
