"""
gpt_social_generator.py — Real gpt-5.5-powered content generator for M05
social post types (facebook_post/instagram_post/threads_post/zalo_post).

Default real generator_fn as of 2026-08-04 (see
growth_orchestrator.bridges.m05_content_bridge) -- Harry switched off
claude-sonnet-5 because output quality was inconsistent. Same three lane
system prompts as content_studio.generators.claude_social_generator, shared
via social_prompts.py so Harry's briefs never drift between generators.

gpt-5.5 API quirks (see providers/openai_provider.py for the same pattern
used by the image-DNA extraction pipeline): `max_completion_tokens`, not
`max_tokens`; `response_format={"type": "json_object"}` enforces valid JSON
output so no markdown-fence stripping or strict=False JSON parsing is
needed here (unlike the Claude generator).

IMPORTANT: Never call this in pytest. Always pass a mock generator_fn in
tests (see content_studio.builders.social_builder.mock_social_generator).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from prompt_studio.schemas.content_prompt import ContentPromptContract

from content_studio.generators.social_prompts import build_user_message, select_system_prompt
from content_studio.schemas.content_request import ContentRequest

GeneratedDraft = Dict[str, Any]


def gpt_social_generator(
    request: ContentRequest,
    prompt: ContentPromptContract,
    config: Dict[str, Any],
) -> GeneratedDraft:
    """Call OpenAI's gpt-5.5 to generate a real social post draft for Ven Ho Hotel.

    Uses prompt.final_prompt (built by M02 -- already carries topic, DNA
    facts, tone, and restrictions) as the user message. Lane/pillar-based
    system prompt selection lives in social_prompts.select_system_prompt.
    """
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package not installed — run: pip install openai") from exc

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in environment")

    system_prompt = select_system_prompt(request)
    user_message = build_user_message(request, prompt.final_prompt)

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-5.5",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=4096,
    )

    raw = response.choices[0].message.content
    draft: GeneratedDraft = json.loads(raw)

    draft.setdefault("title", request.topic)
    draft.setdefault("hook", "")
    draft.setdefault("body", "")
    draft.setdefault("cta", "")
    draft.setdefault("hashtags", [])

    return draft
