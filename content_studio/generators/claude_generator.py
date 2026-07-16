"""
claude_generator.py — Real Claude-powered content generator for M05 longform types.

Uses the final_prompt from M02 ContentPromptContract, calls Claude API at temperature=0,
and returns a GeneratedDraft dict consumed by longform builders.

IMPORTANT: Never call this in pytest. Always pass a mock generator_fn in tests.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from prompt_studio.schemas.content_prompt import ContentPromptContract

from content_studio.schemas.content_request import ContentRequest

GeneratedDraft = Dict[str, Any]

# JSON schemas Claude must follow, keyed by content_type
_SCHEMAS: Dict[str, str] = {
    "blog": """{
  "title": "string — short Vietnamese title (5–8 words)",
  "hook": "string — opening sentence, Vietnamese",
  "body": "string — full article body, Vietnamese",
  "cta": "string — soft call-to-action sentence, Vietnamese",
  "seo_title": "string — SEO-optimised title (≤60 chars)",
  "meta_description": "string — meta description (≤155 chars)",
  "slug": "string — URL slug, lowercase, hyphens",
  "outline": ["string", "..."],
  "faq": [{"question": "string", "answer": "string"}]
}""",
    "website": """{
  "title": "string — page/section title",
  "hook": "string — hero headline",
  "body": "string — about/description copy",
  "cta": "string — CTA block text",
  "hero": "string — hero headline",
  "about": "string — about section copy",
  "room_description": "string — room section copy",
  "location": "string — location blurb",
  "cta_block": "string — CTA block"
}""",
    "ota": """{
  "title": "string — listing title (≤70 chars)",
  "hook": "string — short teaser",
  "body": "string — long OTA description",
  "cta": "string — booking CTA",
  "short_description": "string — ≤160 chars for OTA summary",
  "long_description": "string — full OTA body text",
  "facilities_highlight": ["string", "..."],
  "location_highlight": "string — location blurb",
  "guest_fit_messaging": "string — who this is for"
}""",
    "faq": """{
  "title": "string",
  "hook": "string — intro sentence",
  "body": "string — summary paragraph",
  "cta": "string — closing CTA",
  "items": [
    {
      "question": "string",
      "short_answer": "string — ≤2 sentences",
      "long_answer": "string — extended answer",
      "related_cta": "string"
    }
  ]
}""",
    "email": """{
  "title": "string — internal title",
  "hook": "string — preview text",
  "body": "string — email body",
  "cta": "string — email CTA",
  "subject_options": ["string", "string"],
  "preview_text": "string — ≤90 chars",
  "follow_up_variation": "string — alternative follow-up line"
}""",
}


def _system_prompt(content_type: str) -> str:
    schema = _SCHEMAS.get(content_type, _SCHEMAS["blog"])
    return (
        "You are a professional content writer for Ven Ho Hotel — "
        "a boutique 12-room hotel at West Lake (Ho Tay), Hanoi, Vietnam.\n\n"
        "Return ONLY a single valid JSON object matching the schema below. "
        "No markdown code fences, no explanation, no text outside the JSON.\n\n"
        f"Required JSON schema:\n{schema}"
    )


def claude_longform_generator(
    request: ContentRequest,
    prompt: ContentPromptContract,
    config: Dict[str, Any],
) -> GeneratedDraft:
    """Call Claude API to generate real longform content.

    Uses prompt.final_prompt (built by M02) as the user message.
    temperature=0 — deterministic output aligned with brand DNA.
    """
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic package not installed — run: pip install anthropic") from exc

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=2048,
        temperature=0,
        system=_system_prompt(request.content_type),
        messages=[{"role": "user", "content": prompt.final_prompt}],
    )

    raw = response.content[0].text.strip()
    # Strip markdown fence if model adds one despite instructions
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    draft: GeneratedDraft = json.loads(raw)

    # Ensure required keys exist with sensible fallbacks
    draft.setdefault("title", request.topic)
    draft.setdefault("hook", "")
    draft.setdefault("body", "")
    draft.setdefault("cta", "")

    return draft
