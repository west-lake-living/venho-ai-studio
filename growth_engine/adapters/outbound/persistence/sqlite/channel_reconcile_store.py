from __future__ import annotations

import json
from typing import Any, Callable, Sequence

from growth_engine.application.ops.channel_reconcile import ChannelReconcileResult
from growth_engine.domain.ops.incident import (
    Incident,
    IncidentSeverity,
    IncidentState,
    incident_fingerprint,
)


_ALERT_STATUSES = frozenset({"MISSING", "DELETED", "PLACEHOLDER", "UNAVAILABLE"})


class SqliteChannelReconcileStore:
    """Persist reconciliation alerts through the shared SQLite UoW."""

    def __init__(self, uow_factory: Callable[[], Any], ids: Any) -> None:
        self._uow_factory = uow_factory
        self._ids = ids

    def record_new_alerts(
        self, results: Sequence[ChannelReconcileResult], *, now_ms: int
    ) -> tuple[ChannelReconcileResult, ...]:
        emitted: list[ChannelReconcileResult] = []
        with self._uow_factory().begin_immediate() as tx:
            for result in results:
                status = result.status.value
                if status not in _ALERT_STATUSES:
                    continue
                incident_type = f"CHANNEL_RECONCILE_{status}"
                fingerprint = incident_fingerprint(
                    incident_type, result.channel_id, result.slot_id
                )
                current = tx.incidents.get_open_by_fingerprint(fingerprint)
                severity = (
                    IncidentSeverity.HIGH
                    if status in {"MISSING", "DELETED"}
                    else IncidentSeverity.WARNING
                )
                incident = Incident(
                    id=self._ids.new_id(),
                    type=incident_type,
                    fingerprint=fingerprint,
                    channel_id=result.channel_id,
                    ref=result.slot_id,
                    severity=severity,
                    state=IncidentState.OPEN,
                    first_seen_at_ms=now_ms,
                    last_seen_at_ms=now_ms,
                )
                tx.incidents.open_or_touch(
                    incident,
                    details_json=json.dumps(
                        {
                            "slot_id": result.slot_id,
                            "status": status,
                            "post_id": result.post_id,
                            "permalink": result.permalink,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                )
                if current is None:
                    emitted.append(result)
        return tuple(emitted)
