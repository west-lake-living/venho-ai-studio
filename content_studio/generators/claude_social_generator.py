"""
claude_social_generator.py — Claude-powered content generator for M05 social
post types (facebook_post/instagram_post/threads_post/zalo_post).

Default generator for the Growth Agent's M05 content bridge. The active model
is Claude Opus and can be changed without code through
`CLAUDE_CONTENT_MODEL`. System prompts live in social_prompts.py and are
shared with the retained OpenAI generator, so briefs do not drift during a
provider change.

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

# Use the Opus model enabled for this Anthropic account. An explicit
# deployment-approved model may be supplied through env.
DEFAULT_CLAUDE_CONTENT_MODEL = "claude-opus-5"


def claude_social_generator(
    request: ContentRequest,
    prompt: ContentPromptContract,
    config: Dict[str, Any],
) -> GeneratedDraft:
    """Call Claude API to generate a real social post draft for Ven Ho Hotel.

    Uses prompt.final_prompt (built by M02 -- already carries topic, DNA
    facts, tone, and restrictions) as the user message. Lane/pillar-based
    system prompt selection lives in social_prompts.select_system_prompt.
    """
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic package not installed — run: pip install anthropic") from exc

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")

    system_prompt = select_system_prompt(request)
    user_message = build_user_message(request, prompt.final_prompt)

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=os.environ.get("CLAUDE_CONTENT_MODEL", DEFAULT_CLAUDE_CONTENT_MODEL),
        # 4096 leaves room for a complete JSON social draft, including a
        # possible Anthropic thinking block before the JSON text block.
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    text_block = next(block for block in response.content if block.type == "text")
    raw = text_block.text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    # strict=False: Claude's JSON body strings sometimes contain literal
    # newlines (paragraph breaks) instead of escaped \n -- technically
    # invalid per the JSON spec's control-character rule, but the content is
    # otherwise well-formed and this is Claude's actual observed output
    # shape, not malformed data worth rejecting.
    draft: GeneratedDraft = json.loads(raw, strict=False)

    draft.setdefault("title", request.topic)
    draft.setdefault("hook", "")
    draft.setdefault("body", "")
    draft.setdefault("cta", "")
    draft.setdefault("hashtags", [])

    return draft
