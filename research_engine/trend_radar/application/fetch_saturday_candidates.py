from __future__ import annotations

from datetime import date
from typing import Any, Callable, Optional

from research_engine.trend_radar.application.event_clusters import cluster_events
from research_engine.trend_radar.application.scan_trends import scan_trends
from research_engine.trend_radar.collectors.news_rss import collect_google_news
from research_engine.trend_radar.collectors.official_pages import collect_official_page

# Fallback when trend_sources.yaml is missing; the YAML is the real list.
DEFAULT_QUERIES = [
    '"Hồ Tây" lễ hội',
    '"Hồ Tây" sự kiện',
    '"Hồ Tây" pháo hoa',
    '"phủ Tây Hồ"',
]


def fetch_and_score_saturday_candidates(
    *,
    tavily_api_key: str = "",
    trend_policy: dict,
    safety_policy: dict,
    sources_config: Optional[dict] = None,
    queries: Optional[list[str]] = None,
    collect_fn: Optional[Callable[..., list[dict]]] = None,
    page_collect_fn: Optional[Callable[..., list[dict]]] = None,
    classify_fn: Optional[Callable[[list[dict]], list[dict]]] = None,
    today: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Google News RSS (+ official listing pages) -> Gemini classification
    -> event clustering -> scan_trends scoring.

    Search engine switched from Tavily to Google News RSS on 2026-10-21 (see
    collectors/news_rss.py); `tavily_api_key` is still accepted so an
    injected Tavily `collect_fn` keeps working. One failing query or page is
    skipped, never fatal -- the other sources still produce a scan.

    `human_approval: mandatory` in brand_safety.yaml is a hard invariant this
    function does not (and must not) route around: a "needs_human_approval"
    result here is a *proposal*, not a usable topic -- only
    trend_candidate_store.approve() (an explicit operator action) makes one
    eligible. `collect_fn`/`page_collect_fn`/`classify_fn` are injectable so
    tests never hit the network or Gemini.
    """
    config = sources_config or {}
    news_config = config.get("google_news") or {}
    collect_fn = collect_fn or collect_google_news
    if classify_fn is None:
        from research_engine.trend_radar.classifiers.gemini_classifier import classify_candidates_from_env
        classify_fn = classify_candidates_from_env

    raw: list[dict] = []
    seen_ids: set[str] = set()

    def _add(items: list[dict]) -> None:
        for item in items:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                raw.append(item)

    for query in queries or news_config.get("queries") or DEFAULT_QUERIES:
        try:
            _add(
                collect_fn(
                    query,
                    api_key=tavily_api_key,
                    window_days=news_config.get("window_days", 7),
                    max_results=news_config.get("max_results_per_query", 30),
                )
            )
        except Exception:  # noqa: BLE001 - one bad query must not sink the scan
            continue

    page_collect_fn = page_collect_fn or collect_official_page
    for page in config.get("official_pages") or []:
        try:
            _add(page_collect_fn(page["url"], path_prefix=page["path_prefix"], source_name=page.get("source_name", "")))
        except Exception:  # noqa: BLE001 - same as above
            continue

    classified = classify_fn(raw)
    return scan_trends(
        cluster_events(classified),
        trend_policy,
        safety_policy,
        today=today,
        fast_lane_policy=config.get("fast_lane"),
    )
