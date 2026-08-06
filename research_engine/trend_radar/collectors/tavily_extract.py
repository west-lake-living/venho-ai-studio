"""Read a specific public page Harry named, rather than searching for one.

Why this is separate from `tavily_search` (2026-08-06): search is good at
"what is out there about X" and bad at "what does THIS page say". For the
hotel's own Agoda/Booking review pages and for a named list of nearby
competitors, the URL is already known and search only adds noise -- Harry
supplies the address, this fetches what is at it.

On §7.2: the plan forbids scraping, and means a specific thing by it --
reverse-engineered wrappers driving a personal account's session cookie, and
harvesting competitors' Facebook/Instagram/TikTok. This is neither. It is a
documented search-provider API fetching a page any visitor can open, with no
account, no cookie and no login, at the rate of a handful of URLs a week. The
rule the plan is protecting ("thà thiếu một nguồn còn hơn mất một tài khoản")
is not in play: there is no account to lose.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

from shared.http import urllib_post

TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"

# Extracted pages are whole documents, not search snippets. The cap keeps one
# long review page from crowding out every other source in the extractor's
# window (and from carrying a wall of untrusted text into the prompt).
#
# Raised 6000 -> 12000 (2026-08-06) together with the noise stripping below.
# An OTA listing is 17-40k raw chars of which 60-75% is markdown link and
# image syntax; head-truncating the raw form kept the cookie banner and the
# nav bar and cut off before a single guest review, which is why the first
# real guest_voice run produced 0 proposals from 3 good pages. Stripped, all
# three pages fit under this cap whole.
MAX_CONTENT_CHARS = 12000

_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_BARE_URL_RE = re.compile(r"https?://\S+")


def strip_markdown_noise(text: str) -> str:
    """Drop image/link markup and bare URLs, keeping the visible words.

    Not cosmetic: the removed bytes are what pushed the actual page content
    past the truncation cap, and tracking URLs are pure noise to a fact
    extractor.
    """
    text = _IMAGE_RE.sub("", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _BARE_URL_RE.sub("", text)
    return "\n".join(line for line in (ln.strip() for ln in text.split("\n")) if line)

# "advanced", not the "basic" default (2026-08-06). Basic returns
# `Failed to fetch url` for Agoda -- i.e. for the first page this collector was
# built to read. Advanced renders the page and returns it. Both OTA listings
# are JS-heavy, so basic is not a useful fast path to try first.
EXTRACT_DEPTH = "advanced"


def extract_urls(
    urls: list[str],
    *,
    api_key: str,
    http_post: Optional[Callable[..., dict[str, Any]]] = None,
    max_content_chars: int = MAX_CONTENT_CHARS,
    extract_depth: str = EXTRACT_DEPTH,
) -> list[dict[str, Any]]:
    """Page contents for `urls`, in the same shape the search collector returns.

    Partial results are the norm and not an error: a page that fails to
    extract (paywall, JS-only, timeout) is simply absent, and the ones that
    worked are still worth having.
    """
    if not urls:
        return []
    if not api_key:
        raise ValueError("Tavily API key is required")
    post = http_post or urllib_post
    payload = post(
        TAVILY_EXTRACT_URL,
        json={"api_key": api_key, "urls": urls, "extract_depth": extract_depth},
        timeout=60.0,  # extraction fetches and renders; the 10s default is not enough
    )
    results = []
    for entry in payload.get("results", []):
        url = entry.get("url")
        content = strip_markdown_noise(entry.get("raw_content") or entry.get("content") or "")
        if not url or not content.strip():
            continue
        results.append(
            {
                "id": f"tavily-extract-{url}",
                "title": entry.get("title") or url,
                "source_uri": url,
                "snippet": content[:max_content_chars],
                "relevance_hint": 1.0,  # Harry named this page; it is relevant by construction
            }
        )
    return results
