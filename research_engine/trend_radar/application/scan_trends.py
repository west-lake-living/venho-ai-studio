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


def _days_from(value: object, today: date) -> Optional[int]:
    try:
        return (date.fromisoformat(str(value)) - today).days if value else None
    except ValueError:
        return None


def scan_trends(
    candidates: list[dict],
    trend_policy: dict,
    safety_policy: dict,
    *,
    today: Optional[date] = None,
    fast_lane_policy: Optional[dict] = None,
) -> list[dict]:
    """Gate + score + order candidates.

    West Lake events (2026-10-21): an event the classifier places in the
    West Lake area is scored as `westlake` geography and never falls below
    the Saturday-lane threshold on thematic/actionability alone -- the brand
    is "living beside West Lake today", so a festival on the lake is on-brand
    even when the classifier calls it "adjacent". Brand safety and the
    required-intersection gate still apply unchanged. Events whose end date
    has passed are rejected outright. A West Lake event that is still ahead
    within the fast-lane window gets `fast_lane: True` and sorts first.
    """
    gate = BrandSafetyGate(safety_policy)
    today = today or date.today()
    window = fast_lane_policy or {}
    min_ahead = int(window.get("min_days_ahead", 3))
    max_ahead = int(window.get("max_days_ahead", 10))
    threshold = trend_policy.get("min_score_to_saturday_lane", 0.6)

    results = []
    for candidate in candidates:
        westlake_event = bool(candidate.get("is_event") and candidate.get("westlake_area"))
        if candidate.get("westlake_area"):
            candidate = {**candidate, "geographic": "westlake"}
        allowed, reason = gate.evaluate(candidate.get("brand_safety_category", ""), candidate.get("intersections", []))
        days_to_end = _days_from(candidate.get("event_end"), today)
        if allowed and candidate.get("is_event") and days_to_end is not None and days_to_end < 0:
            allowed, reason = False, "event_passed"
        # A dated event is judged by its end date alone; text dates in the
        # headline ("chào mừng 10/10" on a November concert) are noise then.
        dated_event = bool(candidate.get("is_event") and days_to_end is not None)
        if allowed and not dated_event and _is_stale(candidate, today):
            allowed, reason = False, "stale_dated"
        score = score_relevance(candidate, trend_policy)
        if allowed and westlake_event:
            score = max(score, threshold)
        if allowed and score < threshold:
            reason = "below_min_score"
        status = "needs_human_approval" if allowed and score >= threshold else "rejected"
        days_to_start = _days_from(candidate.get("event_start"), today)
        fast_lane = bool(
            status == "needs_human_approval"
            and westlake_event
            and days_to_start is not None
            and days_to_start <= max_ahead
            and days_to_end is not None
            and days_to_end >= min_ahead
        )
        results.append(
            {
                **candidate,
                "relevance_score": score,
                "status": status,
                "rejection_reason": None if status != "rejected" else reason,
                "fast_lane": fast_lane,
            }
        )
    results.sort(key=lambda c: (not c["fast_lane"], c["status"] != "needs_human_approval", -c["relevance_score"]))
    return results
