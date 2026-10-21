from __future__ import annotations

"""Headline collector for official listing pages (e.g. the Tây Hồ ward
portal's culture section) that publish no RSS feed.

Deliberately dumb: anchors whose href starts with the configured path prefix
and whose text is long enough to be a headline. Classification, dating and
geography are the classifier's job, same as for news results.
"""

import html
import re
import urllib.parse
from typing import Callable, Optional

from research_engine.trend_radar.collectors.news_rss import _http_get_text, headline_id

_ANCHOR = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
# Listing pages repeat a headline with a trailing timestamp ("... 21:00 19/10/2026").
_TRAILING_TIME = re.compile(r"\s+(\d{1,2}:\d{2}\s+)?\d{1,2}/\d{1,2}/\d{4}$|\s+\d+\s+giờ trước$")


def collect_official_page(
    url: str,
    *,
    path_prefix: str,
    source_name: str,
    max_results: int = 20,
    min_title_chars: int = 30,
    http_get: Optional[Callable[[str], str]] = None,
) -> list[dict]:
    page = (http_get or _http_get_text)(url)
    seen: set[str] = set()
    results: list[dict] = []
    for href, inner in _ANCHOR.findall(page):
        if not href.startswith(path_prefix):
            continue
        title = html.unescape(" ".join(re.sub(r"<[^>]+>", " ", inner).split()))
        title = _TRAILING_TIME.sub("", title).strip()
        if len(title) < min_title_chars or title in seen:
            continue
        seen.add(title)
        results.append(
            {
                "id": headline_id(title),
                "title": title,
                "source_uri": urllib.parse.urljoin(url, href),
                "source_name": source_name,
                "published_at": None,
                "snippet": source_name,
                "relevance_hint": 0.0,
                "collector": "official_page",
            }
        )
        if len(results) >= max_results:
            break
    return results
