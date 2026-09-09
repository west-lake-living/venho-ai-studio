from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class BeatStatus(str, Enum):
    RUMORED = "rumored"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    AFFECTING_GUESTS = "affecting_guests"
    COMPLETED = "completed"
    STALLED = "stalled"


@dataclass(frozen=True)
class BeatEntity:
    id: str
    name: str
    queries: tuple[str, ...]
    category: str
    guest_relevance: str
    tracked_since: str
    operator_note: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BeatEntity":
        required = ("id", "name", "queries", "category", "guest_relevance", "tracked_since")
        missing = [key for key in required if not payload.get(key)]
        if missing:
            raise ValueError(f"BeatEntity missing: {', '.join(missing)}")
        return cls(
            id=str(payload["id"]),
            name=str(payload["name"]),
            queries=tuple(str(item) for item in payload["queries"]),
            category=str(payload["category"]),
            guest_relevance=str(payload["guest_relevance"]),
            tracked_since=str(payload["tracked_since"]),
            operator_note=str(payload.get("operator_note", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SearchResult:
    url: str
    title: str
    snippet: str = ""
    content: str = ""
    published_at: str | None = None
    source: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SearchResult":
        if not payload.get("url") or not payload.get("title"):
            raise ValueError("SearchResult requires url and title")
        return cls(
            url=str(payload["url"]), title=str(payload["title"]), snippet=str(payload.get("snippet", "")),
            content=str(payload.get("content", "")), published_at=payload.get("published_at"), source=str(payload.get("source", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BeatItem:
    id: str
    entity_id: str
    entity_name: str
    url: str
    title: str
    snippet: str
    content: str
    published_at: str | None
    detected_at: str
    status: BeatStatus
    status_reason: str = ""
    changed: bool = True
    evidence_level: str = "R0"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BeatItem":
        return cls(
            id=str(payload["id"]), entity_id=str(payload["entity_id"]), entity_name=str(payload["entity_name"]),
            url=str(payload["url"]), title=str(payload["title"]), snippet=str(payload.get("snippet", "")),
            content=str(payload.get("content", "")), published_at=payload.get("published_at"),
            detected_at=str(payload["detected_at"]), status=BeatStatus(str(payload.get("status", BeatStatus.RUMORED.value))),
            status_reason=str(payload.get("status_reason", "")), changed=bool(payload.get("changed", True)),
            evidence_level=str(payload.get("evidence_level", "R0")),
        )


@dataclass(frozen=True)
class WeekSnapshot:
    week: str
    items: tuple[BeatItem, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {"week": self.week, "items": [item.to_dict() for item in self.items]}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WeekSnapshot":
        return cls(week=str(payload.get("week", "")), items=tuple(BeatItem.from_dict(item) for item in payload.get("items", [])))


@dataclass(frozen=True)
class GuestAngle:
    entity_id: str
    beat_item_id: str
    status: BeatStatus
    guest_question: str
    concrete_details: tuple[str, ...]
    what_we_can_say: str
    what_we_cannot_claim: tuple[str, ...]
    evidence_urls: tuple[str, ...]
    evidence_date: date
    fact_ids_r3: tuple[str, ...]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "GuestAngle":
        """Strict schema boundary for LLM output; invalid payloads fail closed."""
        required = (
            "entity_id", "beat_item_id", "status", "guest_question", "concrete_details",
            "what_we_can_say", "what_we_cannot_claim", "evidence_urls", "evidence_date", "fact_ids_r3",
        )
        if set(payload) != set(required):
            raise ValueError("GuestAngle schema mismatch")
        if not isinstance(payload["concrete_details"], list) or not all(isinstance(item, str) for item in payload["concrete_details"]):
            raise ValueError("GuestAngle concrete_details must be a list[str]")
        return cls(
            entity_id=str(payload["entity_id"]), beat_item_id=str(payload["beat_item_id"]),
            status=BeatStatus(str(payload["status"])), guest_question=str(payload["guest_question"]),
            concrete_details=tuple(payload["concrete_details"]), what_we_can_say=str(payload["what_we_can_say"]),
            what_we_cannot_claim=tuple(str(item) for item in payload["what_we_cannot_claim"]),
            evidence_urls=tuple(str(item) for item in payload["evidence_urls"]),
            evidence_date=date.fromisoformat(str(payload["evidence_date"])),
            fact_ids_r3=tuple(str(item) for item in payload["fact_ids_r3"]),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["concrete_details"] = list(self.concrete_details)
        payload["what_we_cannot_claim"] = list(self.what_we_cannot_claim)
        payload["evidence_urls"] = list(self.evidence_urls)
        payload["evidence_date"] = self.evidence_date.isoformat()
        payload["fact_ids_r3"] = list(self.fact_ids_r3)
        return payload
