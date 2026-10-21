from __future__ import annotations

"""Google News RSS collector -- Trend Radar's primary search source.

Why (2026-10-21): the Tavily queries missed every West Lake cultural event of
early October (dragon-boat race 04-05/10, 900 fireworks on the lake 10/10,
Hanoi Drinks Festival 09-11/10) and returned Vung Tau resorts and US news
instead. The same Vietnamese place queries on Google News RSS returned all of
them, dated, from Vietnamese newsrooms -- free and with no API key.
"""

import hashlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Optional

GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"
_USER_AGENT = "Mozilla/5.0 (compatible; VenHoTrendRadar/1.0)"


def _http_get_text(url: str, *, timeout: float = 20.0) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _split_source(title: str, source_name: str) -> str:
    """Google News appends " - <Newsroom>" to every title."""
    suffix = f" - {source_name}"
    if source_name and title.endswith(suffix):
        return title[: -len(suffix)].strip()
    return re.sub(r"\s+-\s+[^-]{2,60}$", "", title).strip()


def headline_id(title: str) -> str:
    """Stable id from the normalised headline, so the same story re-found by
    another query (or tomorrow's scan) dedupes instead of re-queueing."""
    normalised = " ".join(re.findall(r"\w+", title.lower()))
    return "gnews-" + hashlib.sha1(normalised.encode("utf-8")).hexdigest()[:16]


def collect_google_news(
    query: str,
    *,
    window_days: int = 7,
    max_results: int = 30,
    http_get: Optional[Callable[[str], str]] = None,
    now: Optional[datetime] = None,
    **_: object,
) -> list[dict]:
    """Raw R0 entries for one query, newest first, published within
    `window_days`. Extra keyword args (e.g. a Tavily `api_key` still passed by
    the shared fetch loop) are ignored."""
    params = {"q": f"{query} when:{window_days}d", "hl": "vi", "gl": "VN", "ceid": "VN:vi"}
    url = f"{GOOGLE_NEWS_RSS_URL}?{urllib.parse.urlencode(params)}"
    root = ET.fromstring((http_get or _http_get_text)(url))
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=window_days)

    results: list[dict] = []
    for item in root.iter("item"):
        source_name = (item.findtext("source") or "").strip()
        raw_title = (item.findtext("title") or "").strip()
        title = _split_source(raw_title, source_name)
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        try:
            published = parsedate_to_datetime(item.findtext("pubDate") or "")
        except (TypeError, ValueError):
            published = None
        if published is not None and published.tzinfo is not None and published < cutoff:
            continue
        results.append(
            {
                "id": headline_id(title),
                "title": title,
                "source_uri": link,
                "source_name": source_name,
                "published_at": published.isoformat() if published else None,
                # Never put the publication date in the snippet: scan_trends'
                # stale-date rule reads snippet text and would call every
                # article "past" by its own byline date.
                "snippet": source_name,
                "relevance_hint": 0.0,
                "collector": "google_news",
                "query": query,
            }
        )
        if len(results) >= max_results:
            break
    return results


def collect_news_rss_stub() -> list[dict]:
    return []
