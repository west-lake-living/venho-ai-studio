from __future__ import annotations

from typing import Any, Callable

from shared.http import urllib_post

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def collect_tavily_search_stub() -> list[dict]:
    return []


def collect_tavily_search(
    query: str,
    *,
    api_key: str,
    max_results: int = 10,
    http_post: Callable[..., dict[str, Any]] | None = None,
) -> list[dict]:
    """Fetch raw Tavily search results for one query.

    Returns raw R0 entries (id/title/source_uri/snippet/relevance_hint) --
    classification into geographic/thematic/actionability/brand_safety_category
    happens downstream in scan_trends, not here. Feature-flagged off by
    default (trend_radar_enabled); tests always inject a fake http_post.
    """
    if not api_key:
        raise ValueError("Tavily API key is required")
    post = http_post or urllib_post
    payload = post(
        TAVILY_SEARCH_URL,
        json={"api_key": api_key, "query": query, "max_results": max_results},
    )
    results = payload.get("results", [])
    return [
        {
            "id": f"tavily-{result['url']}",
            "title": result.get("title", ""),
            "source_uri": result["url"],
            "snippet": result.get("content", ""),
            "relevance_hint": result.get("score", 0.0),
        }
        for result in results
    ]
