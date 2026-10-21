from __future__ import annotations

"""Collapse many articles about one event into one Trend Radar candidate.

Why (2026-10-21): the 10/10 fireworks on West Lake came back as ~40 separate
headlines across 13 queries. One candidate per headline would bury Harry's
queue the same way 95 Tavily rows did; one candidate per event, carrying its
source list, is one decision.
"""

import hashlib
import re
import unicodedata
from datetime import date, timedelta
from typing import Any, Optional

# Words every West Lake event headline shares -- left in, they make any two
# events look alike.
_GENERIC_TOKENS = {
    "ho", "tay", "ha", "noi", "su", "kien", "le", "hoi", "nam", "ngay", "tai", "tren", "dip", "chao",
    "mung", "cua", "va", "cac", "nhieu", "voi", "to", "chuc", "thu", "do", "mat", "nuoc", "toi", "nay",
    "khai", "mac", "dien", "ra", "se", "du", "nguoi", "dan", "the", "nhung", "cho", "o", "ky", "niem",
    "2025", "2026", "2027",
}


def _folded_words(text: str) -> list[str]:
    folded = unicodedata.normalize("NFD", str(text or "").replace("đ", "d").replace("Đ", "D"))
    folded = "".join(ch for ch in folded if unicodedata.category(ch) != "Mn").lower()
    return re.findall(r"[a-z0-9]+", folded)


def name_tokens(text: str) -> set[str]:
    return {token for token in _folded_words(text) if token not in _GENERIC_TOKENS and len(token) > 1}


def name_bigrams(text: str) -> set[str]:
    """Adjacent word pairs, both meaningful. Accent folding makes "hòa" and
    "hoa" one token, so "hòa nhạc" and "pháo hoa" share a unigram -- but
    never a bigram."""
    words = _folded_words(text)
    return {
        f"{a} {b}"
        for a, b in zip(words, words[1:])
        if a not in _GENERIC_TOKENS and b not in _GENERIC_TOKENS and not a.isdigit() and not b.isdigit()
    }


def _as_date(value: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def same_event(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if not (a.get("is_event") and b.get("is_event")):
        return False
    start_a, start_b = _as_date(a.get("event_start")), _as_date(b.get("event_start"))
    if start_a and start_b:
        if abs(start_a - start_b) > timedelta(days=1):
            return False
        threshold = None
    elif start_a or start_b:
        return False
    else:
        threshold = 0.6
    name_a = a.get("event_name") or a.get("title")
    name_b = b.get("event_name") or b.get("title")
    if threshold is None:
        # Same day: one shared meaningful word pair ("phao hoa", "thuyen rong")
        # is enough. Newsrooms name one show "Bắn 900 giàn pháo hoa chào
        # mừng..." and "Pháo hoa kết hợp âm nhạc tại Hồ Tây"; word-set
        # similarity split the 10/10 fireworks into 3 candidates.
        return bool(name_bigrams(name_a) & name_bigrams(name_b))
    tokens_a, tokens_b = name_tokens(name_a), name_tokens(name_b)
    if not tokens_a or not tokens_b:
        return False
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b) >= threshold


def matches_cluster(cluster: dict[str, Any], candidate: dict[str, Any]) -> bool:
    """same_event against any name the cluster has absorbed, not just its
    first article's -- report 3 may only resemble report 2."""
    if same_event(cluster, candidate):
        return True
    return any(same_event({**cluster, "event_name": alias}, candidate) for alias in cluster.get("event_aliases", []))


def event_id(candidate: dict[str, Any]) -> str:
    key = " ".join(sorted(name_tokens(candidate.get("event_name") or candidate.get("title"))))
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    return f"event-{candidate.get('event_start') or 'undated'}-{digest}"


def source_ref(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": candidate.get("title", ""),
        "source_uri": candidate.get("source_uri", ""),
        "source_name": candidate.get("source_name", ""),
        "published_at": candidate.get("published_at"),
    }


def add_sources(target: dict[str, Any], refs: list[dict[str, Any]]) -> int:
    """Append unseen source refs (by title) to `target`; returns how many."""
    sources = target.setdefault("sources", [source_ref(target)])
    known = {ref.get("title") for ref in sources}
    added = 0
    for ref in refs:
        if ref.get("title") and ref["title"] not in known:
            sources.append(ref)
            known.add(ref["title"])
            added += 1
    target["source_count"] = len(sources)
    return added


def cluster_events(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge event candidates describing the same event; non-events pass
    through untouched. The cluster keeps the first article's classification,
    gets a stable `event-<start>-<hash>` id (so tomorrow's scan dedupes onto
    it) and lists every article in `sources`."""
    clusters: list[dict[str, Any]] = []
    for candidate in candidates:
        if not candidate.get("is_event"):
            clusters.append(candidate)
            continue
        match = next((c for c in clusters if matches_cluster(c, candidate)), None)
        if match is None:
            cluster = {**candidate, "id": event_id(candidate), "sources": [source_ref(candidate)], "source_count": 1}
            clusters.append(cluster)
        else:
            add_sources(match, [source_ref(candidate)])
            alias = candidate.get("event_name")
            if alias and alias != match.get("event_name") and alias not in match.setdefault("event_aliases", []):
                match["event_aliases"].append(alias)
            # A later article often carries the dates/venue an early teaser lacked.
            for key in ("venue", "event_end"):
                if not match.get(key) and candidate.get(key):
                    match[key] = candidate[key]
    return clusters
