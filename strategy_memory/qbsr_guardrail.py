from __future__ import annotations


def qbsr_rate(*, unique_qualified_booking_signals: int, eligible_reach: int) -> float:
    if eligible_reach <= 0:
        return 0.0
    return round(unique_qualified_booking_signals / eligible_reach, 6)


def evaluate_qbsr_guardrail(*, baseline_rate: float, candidate_rate: float, max_relative_drop: float = 0.0) -> dict:
    minimum_allowed = baseline_rate * (1 - max_relative_drop)
    passed = candidate_rate >= minimum_allowed
    return {
        "metric": "QBSR",
        "baseline_rate": baseline_rate,
        "candidate_rate": candidate_rate,
        "minimum_allowed": round(minimum_allowed, 6),
        "passed": passed,
        "reason": None if passed else "qbsr_guardrail_drop",
    }
