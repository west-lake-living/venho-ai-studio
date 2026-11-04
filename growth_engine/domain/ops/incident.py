from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class IncidentSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentState(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


def incident_fingerprint(type: str, channel_id: str | None, ref: str) -> str:
    if not type.strip() or not ref.strip():
        raise ValueError("incident type and ref are required")
    channel = channel_id.strip() if isinstance(channel_id, str) and channel_id.strip() else "-"
    return f"{type}:{channel}:{ref}"


@dataclass(frozen=True)
class Incident:
    id: str
    type: str
    fingerprint: str
    channel_id: str | None
    ref: str
    severity: IncidentSeverity
    state: IncidentState
    first_seen_at_ms: int
    last_seen_at_ms: int
    occurrence_count: int = 1

    def __post_init__(self) -> None:
        for name in ("id", "type", "fingerprint", "ref"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if type(self.first_seen_at_ms) is not int or type(self.last_seen_at_ms) is not int:
            raise ValueError("incident timestamps must be integer epoch milliseconds")
        if type(self.occurrence_count) is not int or self.occurrence_count < 1:
            raise ValueError("occurrence_count must be positive")


_SEVERITY_ORDER = {
    IncidentSeverity.INFO: 0,
    IncidentSeverity.WARNING: 1,
    IncidentSeverity.HIGH: 2,
    IncidentSeverity.CRITICAL: 3,
}


def escalate(incident: Incident, now_ms: int) -> Incident:
    if type(now_ms) is not int:
        raise ValueError("now_ms must be integer epoch milliseconds")
    if incident.state is IncidentState.RESOLVED:
        return incident
    if incident.type == "UNKNOWN":
        target = (
            IncidentSeverity.CRITICAL
            if now_ms - incident.first_seen_at_ms >= 60 * 60_000
            else IncidentSeverity.HIGH
        )
    elif incident.type in {"VERIFY_MISMATCH", "RECEIPT_CONFLICT", "DUPLICATE_POST"}:
        target = IncidentSeverity.CRITICAL
    else:
        target = incident.severity
    if _SEVERITY_ORDER[target] <= _SEVERITY_ORDER[incident.severity]:
        return incident
    return replace(incident, severity=target)
