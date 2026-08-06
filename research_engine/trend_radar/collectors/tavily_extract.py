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

from typing import Any, Callable, Optional

from shared.http import urllib_post

TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"

# Extracted pages are whole documents, not search snippets. The cap keeps one
# long review page from crowding out every other source in the extractor's
# window (and from carrying a wall of untrusted text into the prompt).
MAX_CONTENT_CHARS = 6000


def extract_urls(
    urls: list[str],
    *,
    api_key: str,
    http_post: Optional[Callable[..., dict[str, Any]]] = None,
    max_content_chars: int = MAX_CONTENT_CHARS,
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
        json={"api_key": api_key, "urls": urls},
        timeout=60.0,  # extraction fetches and renders; the 10s default is not enough
    )
    results = []
    for entry in payload.get("results", []):
        url = entry.get("url")
        content = entry.get("raw_content") or entry.get("content") or ""
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
