from __future__ import annotations

from typing import Any

# Priority order per master plan v3.1 section 9.5. Type 4 (feature story) is
# the mandatory fallback -- it must always be available so the Saturday slot
# is never forced to run empty or bend brand safety to chase a trend.
_PRIORITY_ORDER = [
    "seasonal_nature",
    "cultural_event",
    "lifestyle_trend",
    "feature_story",
]


def _is_eligible(candidate: dict[str, Any]) -> bool:
    if candidate.get("type") == "cultural_event":
        return bool(candidate.get("verified_by_human"))
    return True


def select_special_lane_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick the special-lane (Saturday) candidate for a given week.

    TR-D3: never auto-approved -- the caller is responsible for still routing
    the selected candidate through CreativeBrief -> M03 -> human approval.
    This function only decides *which* candidate is proposed.
    """
    by_type = {candidate["type"]: candidate for candidate in candidates if _is_eligible(candidate)}
    for lane_type in _PRIORITY_ORDER:
        if lane_type in by_type:
            return {**by_type[lane_type], "selected_reason": lane_type}
    raise ValueError("No eligible special-lane candidate; a feature_story (type 4) fallback must always be supplied")


def special_lane_timeline_state(*, day: str, digest_ready: bool, approved: bool) -> str:
    """T3->T7 cutoff state machine (v3.1 9.5).

    Vietnamese weekday numbering: T3=Tuesday scan, T4=Wednesday digest,
    T5=Thursday generate+validate, T6=Friday review with a hard 20:00
    cutoff, T7=Saturday publish. An un-approved candidate past the Friday
    20:00 cutoff falls back to evergreen rather than slipping into a
    rushed Saturday-morning approval.
    """
    if day == "tuesday":
        return "scanning"
    if day == "wednesday":
        return "digest_ready" if digest_ready else "scanning"
    if day == "thursday":
        return "generating"
    if day == "friday_before_cutoff":
        return "ready_for_saturday_dispatch" if approved else "awaiting_approval"
    if day == "friday_after_cutoff":
        return "ready_for_saturday_dispatch" if approved else "fallback_evergreen"
    if day == "saturday":
        return "dispatched" if approved else "fallback_evergreen"
    raise ValueError(f"Unknown special-lane timeline day: {day}")
