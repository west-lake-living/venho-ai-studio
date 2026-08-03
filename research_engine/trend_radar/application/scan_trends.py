from __future__ import annotations

from research_engine.trend_radar.application.score_relevance import score_relevance
from research_engine.trend_radar.domain.brand_safety import BrandSafetyGate


def scan_trends(candidates: list[dict], trend_policy: dict, safety_policy: dict) -> list[dict]:
    gate = BrandSafetyGate(safety_policy)
    results = []
    for candidate in candidates:
        allowed, reason = gate.evaluate(candidate.get("brand_safety_category", ""), candidate.get("intersections", []))
        score = score_relevance(candidate, trend_policy)
        status = "needs_human_approval" if allowed and score >= trend_policy.get("min_score_to_saturday_lane", 0.6) else "rejected"
        results.append({**candidate, "relevance_score": score, "status": status, "rejection_reason": None if status != "rejected" else reason})
    return results
