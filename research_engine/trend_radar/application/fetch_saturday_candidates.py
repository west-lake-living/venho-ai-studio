from __future__ import annotations

from typing import Any, Callable, Optional

from research_engine.trend_radar.application.scan_trends import scan_trends
from research_engine.trend_radar.collectors.tavily_search import collect_tavily_search

# Fixed query set (not user-editable via CLI yet -- future work) covering
# the geographic/thematic scope trend_policy.yaml actually scores well
# (westlake/hanoi geographic, travel_stay/food_local/seasonal_weather
# thematic). Kept short: each query is one paid Tavily call.
DEFAULT_QUERIES = [
    "sự kiện Hồ Tây Hà Nội tuần này",
    "mùa hoa Hồ Tây Hà Nội",
    "quán cà phê view Hồ Tây mới",
]


def fetch_and_score_saturday_candidates(
    *,
    tavily_api_key: str,
    trend_policy: dict,
    safety_policy: dict,
    queries: Optional[list[str]] = None,
    collect_fn: Optional[Callable[..., list[dict]]] = None,
    classify_fn: Optional[Callable[[list[dict]], list[dict]]] = None,
) -> list[dict[str, Any]]:
    """Real Tavily search -> Gemini classification -> scan_trends scoring.

    `human_approval: mandatory` in brand_safety.yaml is a hard invariant this
    function does not (and must not) route around: a "needs_human_approval"
    result here is a *proposal*, not a usable topic -- only
    trend_candidate_store.approve() (an explicit operator action) makes one
    eligible for daily_cycle's Saturday rotation. `collect_fn`/`classify_fn`
    are injectable so tests never hit the real Tavily/Gemini APIs.

    Classifier is Gemini Flash, not Claude (switched 2026-08-05 -- cost;
    content generation elsewhere in the codebase is unaffected, this is
    scoped to Trend Radar's classification step only).
    """
    collect_fn = collect_fn or collect_tavily_search
    if classify_fn is None:
        from research_engine.trend_radar.classifiers.gemini_classifier import classify_candidates_from_env
        classify_fn = classify_candidates_from_env

    raw: list[dict] = []
    seen_ids: set[str] = set()
    for query in queries or DEFAULT_QUERIES:
        for item in collect_fn(query, api_key=tavily_api_key):
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                raw.append(item)

    classified = classify_fn(raw)
    return scan_trends(classified, trend_policy, safety_policy)
