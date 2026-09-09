from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Literal


class AngleType(str, Enum):
    PRACTICAL = "practical"
    OBSERVATION = "observation"
    GUIDE = "guide"
    STORY = "story"
    CONTEXT = "context"
    SERVICE = "service"


Weekday = Literal["monday", "wednesday", "friday", "saturday"]


@dataclass(frozen=True)
class ThemeAngle:
    weekday: Weekday
    angle_type: AngleType
    title: str
    premise: str
    concrete_details: tuple[str, ...]
    source: Literal["local_beat", "seasonal", "trend_radar", "evergreen"]
    guest_question: str = ""
    what_we_can_say: str = ""
    what_we_cannot_claim: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["angle_type"] = self.angle_type.value
        payload["concrete_details"] = list(self.concrete_details)
        payload["what_we_cannot_claim"] = list(self.what_we_cannot_claim)
        return payload


@dataclass(frozen=True)
class WeeklyThemePlan:
    iso_week: str
    spine: str
    spine_source: Literal["local_beat", "seasonal", "trend_radar", "evergreen"]
    angles: dict[Weekday, ThemeAngle]
    banned_openers: list[str] = field(default_factory=list)
    banned_phrases: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict) -> "WeeklyThemePlan":
        angles = {}
        for weekday, raw in (payload.get("angles") or {}).items():
            angles[weekday] = ThemeAngle(
                weekday=weekday,
                angle_type=AngleType(str(raw["angle_type"])),
                title=str(raw.get("title", "")),
                premise=str(raw.get("premise", "")),
                concrete_details=tuple(str(item) for item in raw.get("concrete_details", [])),
                source=str(raw.get("source", "evergreen")),
                guest_question=str(raw.get("guest_question", "")),
                what_we_can_say=str(raw.get("what_we_can_say", "")),
                what_we_cannot_claim=tuple(str(item) for item in raw.get("what_we_cannot_claim", [])),
            )
        return cls(
            iso_week=str(payload.get("iso_week", "")), spine=str(payload.get("spine", "")),
            spine_source=str(payload.get("spine_source", "evergreen")), angles=angles,
            banned_openers=list(payload.get("banned_openers", [])),
            banned_phrases=list(payload.get("banned_phrases", [])),
            warnings=list(payload.get("warnings", [])),
        )

    def to_dict(self) -> dict:
        return {
            "iso_week": self.iso_week,
            "spine": self.spine,
            "spine_source": self.spine_source,
            "angles": {day: angle.to_dict() for day, angle in self.angles.items()},
            "banned_openers": list(self.banned_openers),
            "banned_phrases": list(self.banned_phrases),
            "warnings": list(self.warnings),
        }
