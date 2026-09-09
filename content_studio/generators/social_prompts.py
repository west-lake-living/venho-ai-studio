"""Master prompt and lane-specific rules for M05 social content generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from content_studio.schemas.content_request import ContentRequest

SATURDAY_LANE = "saturday_trend"
WEST_LAKE_DNA_SUBJECT = "westlake"
_MASTER_PROMPT_PATH = Path(__file__).with_name("prompts") / "venho_content_generator_master_prompt.md"
_REWRITE_PROMPT_PATH = Path(__file__).with_name("prompts") / "rewrite_vi.md"


def _load_master_prompt() -> str:
    """Load the versioned, user-approved brand system prompt exactly once."""
    return _MASTER_PROMPT_PATH.read_text(encoding="utf-8").strip()


MASTER_SYSTEM_PROMPT = _load_master_prompt()

# The master prompt's §21 asks for a human-facing, multi-platform report.
# M05 is a structured production API: this final contract intentionally wins
# so downstream validation, approval and publishing continue to receive JSON.
_AUTOMATION_OUTPUT_CONTRACT = """

# M05 AUTOMATION OUTPUT CONTRACT — HIGHEST PRIORITY

Apply the master prompt above as your complete strategy, brand voice, factual
integrity and quality standard. Think through its Content Intelligence and
Final Editor Pass privately. Do not output the internal reasoning, strategy
report, markdown headings, quality checklist, or multiple platform versions.

Create the one post requested in the user message, adapted to its requested
platform and grounded only in its supplied facts, image facts, and verified
events. If the supplied facts conflict with the master prompt's generic brand
context, supplied facts win. Never invent a fact.

Return ONLY one valid JSON object. No markdown fence and no text outside JSON:
{
  "title": "string — Vietnamese title",
  "title_options": ["string", "string", "string"],
  "hook": "string — Vietnamese opening hook",
  "body": "string — Vietnamese body only; do not repeat hook or CTA",
  "cta": "string — Vietnamese call to action",
  "hashtags": ["#string"]
}
""".strip()

_WEEKEND_EVENTS_RULES = """

# SATURDAY VERIFIED-EVENTS RULES

For this Saturday trend lane, use only events in “Thông tin sự kiện đã xác
thực” in the user message. Do not invent event names, dates, locations,
descriptions or links. If that list is empty, write a general, factual West
Lake weekend-lifestyle post instead. Keep Ven Hồ Hotel a subtle, natural stop
in the journey.
""".strip()

_WEST_LAKE_PILLAR_RULES = """

# WEST LAKE PILLAR RULES

Make Hồ Tây/Hà Nội the primary character. Integrate Ven Hồ Hotel naturally as
a quiet place to begin or return to, never as a hard-sell advertisement.
""".strip()

# 2026-08-13 diversity fix: Wednesday's local_discovery lane names a real
# quán/địa điểm/sự kiện instead of writing another generic "Hồ Tây" post.
# Mirrors _WEEKEND_EVENTS_RULES's "only what's supplied, never invented"
# shape -- same discipline, different data source (approved research facts
# instead of verified events).
_LOCAL_DISCOVERY_RULES = """

# LOCAL DISCOVERY RULES

Name only the places/events listed in “Dữ liệu địa phương đã xác thực” in the
user message -- do not invent a café, shop, pagoda, or event name, address,
or date that isn't there. If that list is empty, write a general introduction
to the Tây Hồ neighbourhood instead, with no invented proper nouns. Keep Ven
Hồ Hotel a natural, nearby base for the reader to return to, never the
headline.
""".strip()

# Chốt bộ từ khoá SEO cụ thể Harry yêu cầu (2026-08-13) -- §11 SEO STRATEGY
# of the master prompt already states the "natural, no stuffing" philosophy;
# this only names which keywords count so every generated post actually
# carries at least one, instead of the master prompt's generic semantic
# guidance alone.
_SEO_KEYWORDS_BLOCK = """

# SOCIAL SEO KEYWORDS (chèn tự nhiên, không nhồi nhét)

Weave at least one of these naturally into the post wherever it fits the
sentence (never force all of them into one post): "Ven Hồ Hotel", "khách sạn
view Hồ Tây", "Nguyễn Đình Thi", "hoàng hôn Hồ Tây".
""".strip()

# These blocks are assembled with plain string concatenation (see the
# _theme_angle_block / _rewrite_block / ... helpers below), never str.format,
# so operator-editable Vietnamese copy and the external rewrite_vi.md file are
# free to contain "{" / "}" without breaking prompt assembly.
_THEME_ANGLE_HEADER = """
# WEEKLY THEME ANGLE — chất liệu bắt buộc

Đây là góc của bài trong mạch tuần. Dùng ít nhất 3 chi tiết trong
`concrete_details` nếu chúng phù hợp với câu chuyện. Không biến BeatItem thành
factual claim: chỉ khẳng định số liệu/mốc tiến độ khi có fact R3 active.
""".strip()


def _load_rewrite_prompt() -> str:
    """Load the versioned rewrite instruction block once, like the master prompt."""
    return _REWRITE_PROMPT_PATH.read_text(encoding="utf-8").strip()


_REWRITE_PROMPT_TEXT = _load_rewrite_prompt()

_DIVERSITY_HEADER = """
# CHỐNG LẶP TRONG TUẦN

Không dùng lại câu mở hoặc cụm đặc trưng dưới đây:
""".strip()

_VOICE_EXEMPLARS_HEADER = """
# VOICE CORPUS — tham khảo nhịp người thật

Các đoạn dưới đây do người vận hành cung cấp. Học nhịp câu và mức độ cụ thể,
không sao chép câu chữ hay đưa thêm factual claim từ các mẫu:
""".strip()


def _theme_angle_block(angle: Dict[str, Any]) -> str:
    details = ", ".join(str(item) for item in angle.get("concrete_details", []))
    cannot = "; ".join(str(item) for item in angle.get("what_we_cannot_claim", []))
    return "\n".join([
        _THEME_ANGLE_HEADER,
        "",
        f"angle_type: {angle.get('angle_type', '')}",
        f"spine: {angle.get('premise', '')}",
        f"concrete_details: {details}",
        f"guest_question: {angle.get('guest_question', '')}",
        f"what_we_can_say: {angle.get('what_we_can_say', '')}",
        f"what_we_cannot_claim: {cannot}",
    ])


def _rewrite_block(rewrite_round: int, feedback: List[Dict[str, Any]]) -> str:
    violations = "; ".join(
        f"{item.get('rule_id', '')}: {item.get('message', '')} — {item.get('suggestion', '')}"
        for item in feedback
    )
    return "\n".join([
        _REWRITE_PROMPT_TEXT,
        "",
        f"rewrite_round: {rewrite_round}",
        f"violations: {violations}",
    ])


def _diversity_block(banned_openers: List[str], banned_phrases: List[str]) -> str:
    return "\n".join([
        _DIVERSITY_HEADER,
        f"- Câu mở đã dùng: {'; '.join(banned_openers)}",
        f"- Cụm đã dùng: {'; '.join(banned_phrases)}",
    ])


def _voice_exemplars_block(exemplars: List[str]) -> str:
    return _VOICE_EXEMPLARS_HEADER + "\n" + "\n\n---\n\n".join(exemplars)

SYSTEM_PROMPT = f"{MASTER_SYSTEM_PROMPT}\n\n{_SEO_KEYWORDS_BLOCK}\n\n{_AUTOMATION_OUTPUT_CONTRACT}"
WEEKEND_EVENTS_SYSTEM_PROMPT = f"{MASTER_SYSTEM_PROMPT}\n\n{_WEEKEND_EVENTS_RULES}\n\n{_SEO_KEYWORDS_BLOCK}\n\n{_AUTOMATION_OUTPUT_CONTRACT}"
WEST_LAKE_SYSTEM_PROMPT = f"{MASTER_SYSTEM_PROMPT}\n\n{_WEST_LAKE_PILLAR_RULES}\n\n{_SEO_KEYWORDS_BLOCK}\n\n{_AUTOMATION_OUTPUT_CONTRACT}"
LOCAL_DISCOVERY_SYSTEM_PROMPT = f"{MASTER_SYSTEM_PROMPT}\n\n{_LOCAL_DISCOVERY_RULES}\n\n{_SEO_KEYWORDS_BLOCK}\n\n{_AUTOMATION_OUTPUT_CONTRACT}"


def format_verified_events(events: List[Dict[str, Any]]) -> str:
    if not events:
        return "Thông tin sự kiện đã xác thực: (không có sự kiện nào được xác thực cho cuối tuần này)"
    lines = ["Thông tin sự kiện đã xác thực:"]
    for event in events:
        window = event["start_date"] if event["start_date"] == event["end_date"] else f"{event['start_date']} - {event['end_date']}"
        lines.append(
            f"- {event['name']} – {window} – {event.get('location', '')} – "
            f"{event.get('description', '')} – {event.get('source_link', '')}"
        )
    return "\n".join(lines)


def format_research_facts(facts: List[Dict[str, Any]]) -> str:
    """Wednesday's approved-fact counterpart to format_verified_events --
    same "state only what's supplied" contract, different source (approved
    ProposedFactStore rows via growth_orchestrator.application.local_intel,
    not the weekend_events.json list)."""
    if not facts:
        return "Dữ liệu địa phương đã xác thực: (chưa có dữ liệu nào được duyệt cho khu vực này)"
    lines = ["Dữ liệu địa phương đã xác thực:"]
    for fact in facts:
        text = fact.get("text") or f"{fact.get('fact_key', '')}: {fact.get('value', '')}"
        lines.append(f"- {text}")
    return "\n".join(lines)


def format_recent_topics(topics: List[str]) -> str:
    """The cheapest diversity lever available: naming the last few posts so
    the model actively avoids repeating their angle, opening line, or hook
    -- costs nothing extra to call, unlike sourcing a new fact or event."""
    if not topics:
        return ""
    lines = ["\n\nCác bài gần đây — tránh lặp lại góc nhìn, câu mở đầu, hoặc chi tiết đã dùng:"]
    lines += [f"- {topic}" for topic in topics]
    return "\n".join(lines)


def select_system_prompt(request: ContentRequest) -> str:
    if request.lane == SATURDAY_LANE or request.prompt_rules == "weekend_events":
        return WEEKEND_EVENTS_SYSTEM_PROMPT
    if request.prompt_rules == "local_discovery":
        return LOCAL_DISCOVERY_SYSTEM_PROMPT
    if request.prompt_rules == "west_lake_life" or request.dna_subject == WEST_LAKE_DNA_SUBJECT:
        return WEST_LAKE_SYSTEM_PROMPT
    return SYSTEM_PROMPT


def build_user_message(request: ContentRequest, final_prompt: str) -> str:
    parts = [final_prompt]
    if request.theme_angle:
        parts.append(_theme_angle_block(request.theme_angle))
    if request.rewrite_feedback:
        parts.append(_rewrite_block(request.rewrite_round, request.rewrite_feedback))
    if request.banned_openers or request.banned_phrases:
        parts.append(_diversity_block(request.banned_openers, request.banned_phrases))
    if request.voice_exemplars:
        parts.append(_voice_exemplars_block(request.voice_exemplars))
    if request.lane == SATURDAY_LANE:
        parts.append(format_verified_events(request.verified_events))
    if request.prompt_rules == "local_discovery":
        parts.append(format_research_facts(request.research_facts))
    recent = format_recent_topics(request.recent_topics)
    if recent:
        parts.append(recent)
    return "\n\n".join(parts)
