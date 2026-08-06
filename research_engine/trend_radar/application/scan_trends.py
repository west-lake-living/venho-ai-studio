from __future__ import annotations

from datetime import date
from typing import Optional

from research_engine.application.extract_facts import is_stale_dated
from research_engine.trend_radar.application.score_relevance import score_relevance
from research_engine.trend_radar.domain.brand_safety import BrandSafetyGate


def _is_stale(candidate: dict, today: date) -> bool:
    """True when the candidate's own text names dates and all of them are past.

    Same rule the fact extractor uses, applied one stage earlier (2026-08-07).
    It was only ever wired into `local_events` fact proposals, so the Trend
    Radar queue filled up with the Lotus Festival of June 2026, a Mid-Autumn
    listing from 2024 and a news index whose newest headline was 2021 -- all
    scored, all brand-safe, all waiting on Harry to reject by hand every week.

    Reading the snippet as well as the title is deliberate: a title rarely
    dates itself. The cost is that one future date anywhere in a long snippet
    keeps the whole candidate, which is the direction to err in -- a live
    event wrongly dropped never reaches the human queue at all, while a stale
    one that slips through is still one click from gone.
    """
    text = f"{candidate.get('title', '')}\n{candidate.get('snippet', '')}"
    return is_stale_dated(text, today=today)


def scan_trends(
    candidates: list[dict], trend_policy: dict, safety_policy: dict, *, today: Optional[date] = None
) -> list[dict]:
    gate = BrandSafetyGate(safety_policy)
    today = today or date.today()
    results = []
    for candidate in candidates:
        allowed, reason = gate.evaluate(candidate.get("brand_safety_category", ""), candidate.get("intersections", []))
        if allowed and _is_stale(candidate, today):
            allowed, reason = False, "stale_dated"
        score = score_relevance(candidate, trend_policy)
        status = "needs_human_approval" if allowed and score >= trend_policy.get("min_score_to_saturday_lane", 0.6) else "rejected"
        results.append({**candidate, "relevance_score": score, "status": status, "rejection_reason": None if status != "rejected" else reason})
    return results
