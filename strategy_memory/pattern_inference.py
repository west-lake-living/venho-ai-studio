from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any


@dataclass(frozen=True)
class StrategyPattern:
    id: str
    pattern: str
    confidence: float
    scope: dict[str, str]
    evidence: list[dict[str, Any]]
    limitations: list[str]
    expires_at: str
    status: str = "pending_approval"


def bayesian_qbsr(successes: int, eligible_reach: int, *, prior_successes: float = 1.0, prior_failures: float = 99.0) -> float:
    if successes < 0 or eligible_reach < 0 or successes > eligible_reach:
        raise ValueError("invalid QBSR inputs")
    posterior_successes = prior_successes + successes
    posterior_trials = prior_successes + prior_failures + eligible_reach
    return round(posterior_successes / posterior_trials, 6)


def infer_strategy_pattern(
    snapshots: list[dict[str, Any]],
    *,
    pattern: str,
    scope: dict[str, str],
    min_sample_size: int = 5,
    expiry_days: int = 90,
) -> dict[str, Any]:
    if len(snapshots) < min_sample_size:
        return {
            "id": f"strategy-{scope.get('pillar', 'unknown')}-{scope.get('platform', 'all')}",
            "pattern": pattern,
            "confidence": 0.0,
            "scope": scope,
            "evidence": snapshots,
            "limitations": [f"sample_size {len(snapshots)} < minimum {min_sample_size}"],
            "expires_at": (date.today() + timedelta(days=expiry_days)).isoformat(),
            "status": "INCONCLUSIVE",
        }
    successes = sum(int(item.get("qualified_booking_signals", 0)) for item in snapshots)
    reach = sum(int(item.get("eligible_reach", 0)) for item in snapshots)
    confidence = bayesian_qbsr(successes, reach)
    memory = StrategyPattern(
        id=f"strategy-{scope.get('pillar', 'unknown')}-{scope.get('platform', 'all')}",
        pattern=pattern,
        confidence=confidence,
        scope=scope,
        evidence=snapshots,
        limitations=["Bayesian-smoothed pilot signal; advisory only until approved"],
        expires_at=(date.today() + timedelta(days=expiry_days)).isoformat(),
    )
    return memory.__dict__


def promote_strategy_memory(memory: dict[str, Any], *, approved_by: str | None = None) -> dict[str, Any]:
    if memory.get("status") == "INCONCLUSIVE":
        raise ValueError("insufficient sample cannot be promoted")
    if not memory.get("evidence") or not memory.get("limitations"):
        raise ValueError("strategy memory requires evidence and limitations")
    if not approved_by:
        raise ValueError("founder approval is required")
    return {**memory, "status": "approved", "approved_by": approved_by}
