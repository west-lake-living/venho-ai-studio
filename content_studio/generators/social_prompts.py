"""Master prompt and lane-specific rules for M05 social content generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from content_studio.schemas.content_request import ContentRequest

SATURDAY_LANE = "saturday_trend"
WEST_LAKE_DNA_SUBJECT = "westlake"
_MASTER_PROMPT_PATH = Path(__file__).with_name("prompts") / "venho_content_generator_master_prompt.md"


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

SYSTEM_PROMPT = f"{MASTER_SYSTEM_PROMPT}\n\n{_AUTOMATION_OUTPUT_CONTRACT}"
WEEKEND_EVENTS_SYSTEM_PROMPT = f"{MASTER_SYSTEM_PROMPT}\n\n{_WEEKEND_EVENTS_RULES}\n\n{_AUTOMATION_OUTPUT_CONTRACT}"
WEST_LAKE_SYSTEM_PROMPT = f"{MASTER_SYSTEM_PROMPT}\n\n{_WEST_LAKE_PILLAR_RULES}\n\n{_AUTOMATION_OUTPUT_CONTRACT}"


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


def select_system_prompt(request: ContentRequest) -> str:
    if request.lane == SATURDAY_LANE:
        return WEEKEND_EVENTS_SYSTEM_PROMPT
    if request.dna_subject == WEST_LAKE_DNA_SUBJECT:
        return WEST_LAKE_SYSTEM_PROMPT
    return SYSTEM_PROMPT


def build_user_message(request: ContentRequest, final_prompt: str) -> str:
    if request.lane == SATURDAY_LANE:
        return f"{final_prompt}\n\n{format_verified_events(request.verified_events)}"
    return final_prompt
