# STATUS (2026-08-05 audit): implemented and unit-tested (publication →
# qualified inquiry/booking signal, DoD #25) but NOT called from
# `m08_analytics_bridge.py`, `measure_cmd`, or any other real entry point.
# No attribution evidence currently reaches a published report or advisory.
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AttributionPolicy:
    direct_window_hours: int
    assisted_window_days: int
    dedupe_fields: tuple[str, ...]
    pseudonymization: str = "sha256"

    @classmethod
    def from_file(cls, path: Path = Path("config/projects/venho_hotel/growth/attribution_policy.yaml")) -> "AttributionPolicy":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(
            direct_window_hours=int(payload.get("direct_window_hours", 72)),
            assisted_window_days=int(payload.get("assisted_window_days", 14)),
            dedupe_fields=tuple(payload.get("dedupe_fields", [])),
            pseudonymization=payload.get("pseudonymization", "sha256"),
        )


def pseudonymize_contact(contact: str, *, salt: str = "venho") -> str:
    normalized = contact.strip().casefold()
    return hashlib.sha256(f"{salt}:{normalized}".encode("utf-8")).hexdigest()


def build_utm_content(publication_id: str) -> str:
    if not publication_id.strip():
        raise ValueError("publication_id is required")
    return publication_id.strip()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _dedupe_key(event: dict[str, Any], fields: tuple[str, ...]) -> tuple[Any, ...]:
    return tuple(event.get(field) for field in fields)


def dedupe_conversion_events(events: list[dict[str, Any]], policy: AttributionPolicy) -> list[dict[str, Any]]:
    seen = set()
    unique = []
    for event in events:
        key = _dedupe_key(event, policy.dedupe_fields)
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)
    return unique


def attribute_conversion_event(event: dict[str, Any], publications: list[dict[str, Any]], policy: AttributionPolicy) -> dict[str, Any]:
    event_time = _parse_time(event["occurred_at"])
    utm_content = event.get("utm_content")
    if utm_content:
        matches = [item for item in publications if item["publication_id"] == utm_content]
        if len(matches) == 1:
            return {**event, "publication_id": matches[0]["publication_id"], "attribution_status": "direct"}
        if len(matches) > 1:
            raise ValueError("utm_content matched multiple publications")

    direct_candidates = []
    assisted_candidates = []
    for publication in publications:
        published_at = _parse_time(publication["published_at"])
        if event_time < published_at:
            continue
        delta = event_time - published_at
        if delta <= timedelta(hours=policy.direct_window_hours):
            direct_candidates.append(publication)
        elif delta <= timedelta(days=policy.assisted_window_days):
            assisted_candidates.append(publication)

    if len(direct_candidates) == 1:
        return {**event, "publication_id": direct_candidates[0]["publication_id"], "attribution_status": "direct"}
    if len(direct_candidates) > 1:
        raise ValueError("event matched multiple direct publications")
    if len(assisted_candidates) == 1:
        return {**event, "publication_id": assisted_candidates[0]["publication_id"], "attribution_status": "assisted"}
    return {**event, "publication_id": None, "attribution_status": "unattributed"}


def build_content_performance_view(snapshots: list[dict[str, Any]], scores: list[dict[str, Any]]) -> dict[str, Any]:
    score_by_snapshot = {score["snapshot_id"]: score for score in scores}
    rows = []
    for snapshot in snapshots:
        score = score_by_snapshot.get(snapshot["snapshot_id"], {})
        rows.append(
            {
                "snapshot_id": snapshot["snapshot_id"],
                "publication_id": snapshot.get("publication_id") or snapshot.get("package_id"),
                "platform": snapshot["platform"],
                "metrics": snapshot["metrics"],
                "performance_label": score.get("performance_label"),
                "relative_score": score.get("relative_score"),
            }
        )
    return {"source": "M08", "rows": rows}
