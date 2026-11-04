from __future__ import annotations

from collections.abc import Mapping
from typing import Callable

from growth_engine.application.errors import Conflict
from growth_engine.application.ops.controls import append_audit
from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.application.ports.uow import UnitOfWork
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.kernel.hashing import canonical_json_bytes
from growth_engine.domain.ops.incident import (
    Incident,
    IncidentSeverity,
    IncidentState,
    escalate,
    incident_fingerprint,
)


_SEVERITY_ORDER = {
    IncidentSeverity.INFO: 0,
    IncidentSeverity.WARNING: 1,
    IncidentSeverity.HIGH: 2,
    IncidentSeverity.CRITICAL: 3,
}


class IncidentUseCase:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._ids = ids

    def open_or_touch_incident(
        self,
        *,
        incident_type: str,
        channel_id: str | None,
        ref: str,
        severity: IncidentSeverity,
        details: Mapping[str, object],
        actor: str,
        correlation_id: str,
    ) -> Incident:
        _validate_audit(actor, correlation_id)
        if not isinstance(severity, IncidentSeverity):
            raise ValueError("severity must be an IncidentSeverity")
        now_ms = self._clock.now_ms()
        fingerprint = incident_fingerprint(incident_type, channel_id, ref)
        with self._uow_factory().begin_immediate() as tx:
            before = tx.incidents.get_open_by_fingerprint(fingerprint)
            chosen_severity = severity
            if before is not None:
                escalated = escalate(before, now_ms)
                chosen_severity = max(
                    (severity, escalated.severity),
                    key=_SEVERITY_ORDER.__getitem__,
                )
            incoming = Incident(
                id=self._ids.new_id(),
                type=incident_type,
                fingerprint=fingerprint,
                channel_id=channel_id,
                ref=ref,
                severity=chosen_severity,
                state=IncidentState.OPEN,
                first_seen_at_ms=now_ms if before is None else before.first_seen_at_ms,
                last_seen_at_ms=now_ms,
                occurrence_count=1 if before is None else before.occurrence_count + 1,
            )
            after = tx.incidents.open_or_touch(
                incoming,
                details_json=canonical_json_bytes(dict(details)).decode("utf-8"),
            )
            append_audit(
                tx,
                ids=self._ids,
                clock=self._clock,
                aggregate_type="incident",
                aggregate_id=after.id,
                actor=actor,
                action="open_or_touch_incident",
                before=None if before is None else _incident_snapshot(before),
                after=_incident_snapshot(after),
                details={"fingerprint": fingerprint},
                correlation_id=correlation_id,
            )
            return after

    def resolve_incident(
        self,
        incident_id: str,
        *,
        actor: str,
        reason: str,
        correlation_id: str,
    ) -> Incident:
        _validate_audit(actor, correlation_id)
        if not reason.strip():
            raise ValueError("reason is required")
        with self._uow_factory().begin_immediate() as tx:
            before = tx.incidents.get(incident_id)
            if before is None:
                raise DomainError(ErrorCode.NOT_FOUND, "Không tìm thấy sự cố.")
            if before.state is IncidentState.RESOLVED:
                return before
            if not tx.incidents.resolve(
                incident_id,
                actor=actor,
                reason=reason,
                now_ms=self._clock.now_ms(),
            ):
                raise Conflict("Sự cố đã được thay đổi; hãy tải lại.")
            after = tx.incidents.get(incident_id)
            if after is None:
                raise DomainError(ErrorCode.NOT_FOUND, "Không tìm thấy sự cố.")
            append_audit(
                tx,
                ids=self._ids,
                clock=self._clock,
                aggregate_type="incident",
                aggregate_id=after.id,
                actor=actor,
                action="resolve_incident",
                before=_incident_snapshot(before),
                after=_incident_snapshot(after),
                details={"reason": reason},
                correlation_id=correlation_id,
            )
            return after


def _incident_snapshot(incident: Incident) -> dict[str, object]:
    return {
        "id": incident.id,
        "type": incident.type,
        "fingerprint": incident.fingerprint,
        "channel_id": incident.channel_id,
        "ref": incident.ref,
        "severity": incident.severity.value,
        "state": incident.state.value,
        "first_seen_at_ms": incident.first_seen_at_ms,
        "last_seen_at_ms": incident.last_seen_at_ms,
        "occurrence_count": incident.occurrence_count,
    }


def _validate_audit(actor: str, correlation_id: str) -> None:
    if not actor.strip() or not correlation_id.strip():
        raise ValueError("actor and correlation_id are required")
