from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from content_studio.content_context import DEFAULT_CONFIG_ROOT, DEFAULT_DATA_ROOT
from content_studio.content_engine import generate_content
from content_studio.schemas.content_request import ContentRequest
from knowledge_studio.facts.fact_resolver import FactResolver

# Facts a hotel-info blog post can honestly cite. This is a whitelist, not
# "every fact in the store" -- DoD #12 requires every published claim to
# trace to an approved R3 Knowledge Fact, so only keys explicitly known to be
# blog-appropriate are ever considered, and FactResolver.resolve() is the
# real gate: an unapproved or expired fact_key silently drops out below
# rather than being fabricated.
BLOG_FACT_KEYS = ["hotel.room_count", "hotel.address", "hotel.website", "review.agoda_overall"]

_FACT_CLAUSES_VI = {
    "hotel.room_count": "{value} phòng",
    "hotel.address": "toạ lạc tại {value}",
    "hotel.website": "thông tin đặt phòng tại {value}",
    "review.agoda_overall": "đánh giá {value} trên Agoda",
}


def _resolve_blog_facts(resolver: FactResolver) -> list[dict[str, Any]]:
    resolved = []
    for key in BLOG_FACT_KEYS:
        fact = resolver.resolve(key)
        if fact:
            resolved.append({**fact, "fact_key": key})
    return resolved


def _facts_paragraph(facts: list[dict[str, Any]]) -> str:
    if not facts:
        return ""
    clauses = [_FACT_CLAUSES_VI[fact["fact_key"]].format(value=fact["value"]) for fact in facts]
    return "Ven Ho Hotel " + ", ".join(clauses) + "."


def run_blog_pipeline(
    topic: str,
    *,
    keyword: Optional[str] = None,
    dna_subject: str = "westlake",
    project: str = "venho_hotel",
    config_root: Path = DEFAULT_CONFIG_ROOT,
    data_root: Path = DEFAULT_DATA_ROOT,
    fact_resolver: Optional[FactResolver] = None,
) -> dict[str, Any]:
    """Generate one blog/SEO draft grounded in Research OS approved facts.

    DoD #11: "Blog SEO chạy được từ cùng kho research" (blog SEO runs from
    the same research repository as everything else). content_studio's
    build_blog_draft() on its own only cites DNA visual facts (water color,
    light quality, ...) -- it has no path to knowledge_studio.facts (the
    Research OS approved-fact store). This is the growth_orchestrator-level
    bridge that adds one: it resolves BLOG_FACT_KEYS through FactResolver
    (the same approved+in-window gate the rest of the system uses) and
    appends a grounded-facts paragraph built only from what actually
    resolved -- nothing here invents a claim content_studio didn't already
    validate or FactResolver didn't already approve.

    Wiring boundary kept intentionally narrow: this does not modify
    content_studio (still owned by M02/M05), does not call M03 validation of
    the appended facts paragraph (see limitation below), and does not touch
    the daily_cycle cadence -- there is no scheduled "blog day" in
    cadence_policy.yaml yet, so this is a manually-invoked pipeline (CLI:
    `venho-growth blog`) until Harry decides blog cadence/placement.
    """
    resolver = fact_resolver or FactResolver(project=project, data_root=data_root)
    facts = _resolve_blog_facts(resolver)

    request = ContentRequest(
        project=project,
        content_type="blog",
        topic=topic,
        keyword=keyword,
        target_audience="Vietnamese leisure guests researching West Lake stays",
        content_pillar="thuong_hieu",
        tone="warm, clear, trustworthy",
        target_language="vi",
        cta_type="booking_soft",
        subject=dna_subject,
    )
    result = generate_content(request, config_root=config_root, data_root=data_root, validate=True)
    output = result.output

    facts_paragraph = _facts_paragraph(facts)
    body = f"{output.body}\n\n{facts_paragraph}" if facts_paragraph else output.body

    return {
        "title": output.title,
        "body": body,
        "cta": output.cta,
        "facts_cited": [fact["fact_key"] for fact in facts],
        "fact_source_rs_ids": [fact.get("source_rs_id") for fact in facts],
        "markdown_path": str(result.markdown_path),
        "json_path": str(result.json_path),
    }
