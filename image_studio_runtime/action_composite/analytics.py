from __future__ import annotations

from collections import Counter
from typing import Iterable, Dict, Any

from .orchestration import AuditTrail, CostLedger


def build_analytics(trails: Iterable[AuditTrail], ledger: CostLedger) -> Dict[str, Any]:
    trails = list(trails)
    states = Counter(event.state for trail in trails for event in trail.events)
    approved = sum(1 for trail in trails if trail.latest and trail.latest.state == "FINALIZE")
    return {
        "jobs": len(trails),
        "approved_jobs": approved,
        "approval_rate": round(approved / len(trails), 4) if trails else 0.0,
        "state_counts": dict(states),
        "cost": ledger.snapshot(),
    }
