from __future__ import annotations


def verify_event(event_note: dict, *, verified_by_human: bool) -> dict:
    if not verified_by_human:
        raise ValueError("Event must be verified by human before it can shape content")
    return {**event_note, "verified_by_human": True, "status": "reviewed"}
