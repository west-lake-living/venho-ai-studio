from __future__ import annotations

from growth_engine.domain.ops.incident import (
    Incident,
    IncidentSeverity,
    IncidentState,
    escalate,
    incident_fingerprint,
)


def incident(*, type: str = "UNKNOWN", severity: IncidentSeverity = IncidentSeverity.INFO) -> Incident:
    return Incident(
        id="incident-synthetic-1",
        type=type,
        fingerprint=incident_fingerprint(type, "page_b", "delivery-synthetic-1"),
        channel_id="page_b",
        ref="delivery-synthetic-1",
        severity=severity,
        state=IncidentState.OPEN,
        first_seen_at_ms=1_000,
        last_seen_at_ms=1_000,
        occurrence_count=1,
    )


def test_fingerprint_uses_channel_or_dash_and_reference() -> None:
    assert incident_fingerprint("UNKNOWN", "page_b", "delivery-1") == "UNKNOWN:page_b:delivery-1"
    assert incident_fingerprint("DEPENDENCY_DOWN", None, "meta_graph") == "DEPENDENCY_DOWN:-:meta_graph"


def test_unknown_escalates_high_then_critical_after_sixty_minutes() -> None:
    assert escalate(incident(), now_ms=1_000).severity is IncidentSeverity.HIGH
    high = escalate(incident(), now_ms=1_000)
    assert escalate(high, now_ms=3_600_999).severity is IncidentSeverity.HIGH
    assert escalate(high, now_ms=3_601_000).severity is IncidentSeverity.CRITICAL


def test_definitive_mismatch_is_critical_and_escalation_never_lowers_severity() -> None:
    assert escalate(incident(type="VERIFY_MISMATCH"), now_ms=1_000).severity is IncidentSeverity.CRITICAL
    already_critical = incident(type="UNKNOWN", severity=IncidentSeverity.CRITICAL)
    assert escalate(already_critical, now_ms=1_000).severity is IncidentSeverity.CRITICAL


def test_resolved_incident_does_not_escalate() -> None:
    resolved = incident()
    resolved = Incident(**{**resolved.__dict__, "state": IncidentState.RESOLVED})
    assert escalate(resolved, now_ms=9_000_000) is resolved
