"""Approved research facts -> Wednesday's local_discovery topic candidates.

Why (2026-08-13): the research pipeline (research_engine/) already collects
and Harry already approves real local facts -- cafes, pagodas, running
exhibitions -- into ProposedFactStore, but nothing downstream ever read
`status == "approved"` rows back into a post. Every Wed/Fri/Mon brief's
`proof_points` was hardcoded to `[]` in daily_cycle._build_creative_brief.

Deliberately reads ONLY `status == "approved"` (Harry's call, 2026-08-13):
`pending_approval` facts are unverified extractor output and must never reach
a post a guest will read. `rejected` facts are excluded by construction.

Best-effort like _weather_context_for_saturday: a broken/missing fact store
must never block the Wednesday pipeline, which ran on the curated topic list
alone before this existed.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from shared.storage.proposed_fact_store import APPROVED, ProposedFactStore

# DD/MM/YYYY or "DD/MM/YYYY - DD/MM/YYYY" as written by the local_events
# extractor (see config/projects/venho_hotel/research/research_questions.yaml).
_DATE_RANGE = re.compile(r"(\d{2}/\d{2}/\d{4})(?:\s*-\s*(\d{2}/\d{2}/\d{4}))?")


def _event_still_running(value: str, on_date: date) -> bool:
    """True when an event's value string has no end date, or ends on/after
    `on_date`. An unparseable value is treated as still-running rather than
    silently dropped -- a malformed date must not swallow a real fact."""
    match = _DATE_RANGE.search(str(value))
    if not match:
        return True
    end_raw = match.group(2) or match.group(1)
    try:
        end = datetime.strptime(end_raw, "%d/%m/%Y").date()
    except ValueError:
        return True
    return end >= on_date


def approved_local_facts(
    project: str,
    data_root: Path,
    *,
    domains: list[str],
    slot_date: date,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Approved facts from `domains`, expired local_events filtered out.

    Each item: {"fact_key", "value", "domain", "text"} where `text` is a
    ready-to-quote Vietnamese-safe summary line built from the fact's own
    `rationale` (already Vietnamese prose from the extractor).
    """
    if not domains:
        return []
    try:
        facts = ProposedFactStore(project, data_root=data_root).list_items(status=APPROVED)
    except Exception:  # noqa: BLE001 - a broken fact store must never block Wednesday's pipeline
        return []

    picked: list[dict[str, Any]] = []
    for fact in facts:
        if fact.get("domain") not in domains:
            continue
        if fact.get("domain") == "local_events" and not _event_still_running(fact.get("value", ""), slot_date):
            continue
        picked.append(
            {
                "fact_key": fact.get("fact_key", fact.get("id", "")),
                "value": fact.get("value", ""),
                "domain": fact.get("domain", ""),
                "text": fact.get("rationale") or f"{fact.get('fact_key', '')}: {fact.get('value', '')}",
            }
        )
        if len(picked) >= limit:
            break
    return picked


# Extractor rationale lines open with the research source index ("Nguồn 3
# giới thiệu ...", "Nguồn 0 đề xuất ..."). That is provenance, not copy: it
# reached the Dashboard as the post's topic and the writer as a proof point
# (2026-10-21 audit). Strip "Nguồn <n> <verb>" before reusing the line.
_SOURCE_PREFIX = re.compile(
    r"^\s*Nguồn\s+\d+\s+(?:(?:giới thiệu|đề xuất|xác định|khẳng định|chỉ ra rằng|chỉ ra|cho biết|ghi nhận|nhắc đến|nêu)\s+)?",
    re.IGNORECASE,
)

# A place covered (posted, queued, or turned down by Harry) inside this window
# is not proposed again -- research or curated alike.
PLACE_COOLDOWN_DAYS = 90


def clean_rationale(text: str) -> str:
    cleaned = _SOURCE_PREFIX.sub("", str(text or "")).strip()
    return cleaned[:1].upper() + cleaned[1:] if cleaned else cleaned


def _tokens(text: str) -> list[str]:
    folded = unicodedata.normalize("NFD", str(text or "").replace("đ", "d").replace("Đ", "D"))
    folded = "".join(ch for ch in folded if unicodedata.category(ch) != "Mn").lower()
    return re.findall(r"[a-z0-9]+", folded)


def place_key(fact: dict[str, Any]) -> tuple[str, ...]:
    """Accent-free token key naming the place/event a fact is about.

    `value` holds the place name for local_intel facts ("Chợ Hoa Quảng Bá
    (236 Đường Âu Cơ, ...)") -- the part before "(" is the name. Event facts
    carry a date range as value, so their key comes from the rationale's
    first words instead."""
    value = str(fact.get("value", ""))
    name = value.split("(", 1)[0]
    if re.search(r"[A-Za-zÀ-ỹ]", name):
        return tuple(_tokens(name))
    return tuple(_tokens(clean_rationale(fact.get("text") or fact.get("rationale", "")))[:6])


def text_mentions_place(text: str, key: tuple[str, ...]) -> bool:
    """True when every token of `key` appears in `text` (accent-insensitive),
    so "cho hoa Quang Ba luc tinh mo" and "Nguồn 3 giới thiệu Chợ Hoa Quảng
    Bá ..." both match the key of Chợ Hoa Quảng Bá."""
    return bool(key) and set(key) <= set(_tokens(text))


def recently_covered_places(
    keys: list[tuple[str, ...]],
    publications: list[dict[str, Any]],
    *,
    today: date,
    cooldown_days: int = PLACE_COOLDOWN_DAYS,
) -> set[tuple[str, ...]]:
    """Keys whose place appears in any publication topic created within
    `cooldown_days` -- every status counts: published means "said it",
    queued means "about to say it", rejected/cancelled means Harry said no.

    Why (2026-10-21): Chợ Hoa Quảng Bá went out 19/08, 26/08 and 23/09, was
    rejected as a repeat 07/10, and was approved again for 21/10. The exact-
    text cooldown did see it -- but all 5 approved local_intel facts were in
    cooldown, so topic_selector's least-recently-used fallback re-picked it."""
    cutoff = today - timedelta(days=cooldown_days)
    covered: set[tuple[str, ...]] = set()
    for pub in publications:
        created = str(pub.get("created_at") or "")
        try:
            if datetime.fromisoformat(created).date() < cutoff:
                continue
        except ValueError:
            continue
        topic = str(pub.get("topic") or "")
        for key in keys:
            if key not in covered and text_mentions_place(topic, key):
                covered.add(key)
    return covered


def local_intel_topic_entries(
    project: str,
    data_root: Path,
    *,
    domains: list[str],
    pillar: str,
    slot_date: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Shapes approved_local_facts() into the same topic-entry shape
    topic_selector expects from content_pillars.yaml -- one entry per fact.

    `topic` is the place name (fact value) when there is one, otherwise the
    cleaned rationale; `proof_points` carries the cleaned rationale so the
    brief still cites the real fact. `place_key` lets the caller drop places
    covered recently.

    No `dna_subject` here on purpose: the lane's scenario (picked
    independently, see daily_cycle._pick_scenario) decides the image
    subject, not the topic text.
    """
    facts = approved_local_facts(project, data_root, domains=domains, slot_date=slot_date or date.today())
    entries = []
    for fact in facts:
        proof_text = clean_rationale(fact["text"]) or fact["text"]
        name = str(fact.get("value", "")).strip()
        has_name = bool(re.search(r"[A-Za-zÀ-ỹ]", name.split("(", 1)[0]))
        entries.append(
            {
                "pillar": pillar,
                "topic": name if has_name else proof_text,
                "research_backed": True,
                "place_key": list(place_key(fact)),
                "proof_points": [{"text": proof_text, "fact_key": fact["fact_key"]}],
            }
        )
    return entries
