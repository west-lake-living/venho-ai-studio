from __future__ import annotations


def runway_status(open_slot_count: int, policy: dict) -> str:
    """Runway measured in open PublishingSlots, not calendar days (v3.1 PB-003)."""
    runway = policy.get("runway_slots") or policy.get("runway_days", {})
    if open_slot_count >= runway.get("healthy_min", 6):
        return "healthy"
    if open_slot_count >= runway.get("warning_min", 4):
        return "warning"
    if open_slot_count >= runway.get("critical_min", 2):
        return "critical"
    return "empty"
