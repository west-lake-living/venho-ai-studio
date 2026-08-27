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
import random
import time
from typing import Any, Dict

from prompt_studio.schemas.content_prompt import ContentPromptContract

from content_studio.generators.social_prompts import build_user_message, select_system_prompt
from content_studio.schemas.content_request import ContentRequest

GeneratedDraft = Dict[str, Any]

# Use the Opus model enabled for this Anthropic account. An explicit
# deployment-approved model may be supplied through env.
DEFAULT_CLAUDE_CONTENT_MODEL = "claude-opus-5"


def _is_anthropic_overloaded(exc: Exception) -> bool:
    """Anthropic uses HTTP 529 for temporary account/model overload."""
    return getattr(exc, "status_code", None) == 529 or "overloaded" in str(exc).lower()


def _is_retryable_anthropic_error(exc: Exception) -> bool:
    """Return true only for provider/transport failures safe to replay.

    Each generated draft has its own call to this helper, so retrying here is
    a per-content queue: a busy Claude request waits and retries in place,
    while malformed prompts, authentication and schema errors fail fast for
    the normal replacement flow.
    """
    status_code = getattr(exc, "status_code", None)
    if status_code in {408, 429, 500, 502, 503, 504, 529}:
        return True
    message = str(exc).lower()
    return any(token in message for token in ("overloaded", "timeout", "timed out", "connection", "temporarily unavailable"))


def _retry_delay_seconds(exc: Exception, attempt: int) -> float:
    """Exponential delay with bounded jitter, respecting Retry-After when sent."""
    base = max(0.1, float(os.environ.get("ANTHROPIC_RETRY_BASE_SECONDS") or "2"))
    cap = max(base, float(os.environ.get("ANTHROPIC_RETRY_MAX_SECONDS") or "30"))
    retry_after = getattr(exc, "retry_after", None)
    headers = getattr(exc, "headers", None) or getattr(getattr(exc, "response", None), "headers", None) or {}
    retry_after = retry_after or headers.get("retry-after") or headers.get("Retry-After")
    try:
        delay = min(cap, max(0.0, float(retry_after))) if retry_after is not None else min(cap, base * (2**attempt))
    except (TypeError, ValueError):
        delay = min(cap, base * (2**attempt))
    # A small bounded jitter prevents every FB/IG generation from retrying at
    # exactly the same second after an Anthropic capacity incident.
    return delay + random.uniform(0.0, min(1.0, delay * 0.25))


def create_anthropic_message(client: Any, **kwargs: Any) -> Any:
    """Retry each content request independently for transient provider errors."""
    attempts = max(1, int(os.environ.get("ANTHROPIC_RETRY_ATTEMPTS") or "5"))
    for attempt in range(attempts):
        try:
            return client.messages.create(**kwargs)
        except Exception as exc:
            if not _is_retryable_anthropic_error(exc) or attempt == attempts - 1:
                raise
            time.sleep(_retry_delay_seconds(exc, attempt))


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

    timeout = float(os.environ.get("ANTHROPIC_TIMEOUT_SECONDS") or "120")
    try:
        client = Anthropic(api_key=api_key, timeout=timeout)
    except TypeError:  # test doubles / older SDKs without timeout support
        client = Anthropic(api_key=api_key)
    response = create_anthropic_message(
        client,
        # os.environ.get's default only fires when the key is absent -- a repo
        # variable set to "" (as CLAUDE_CONTENT_MODEL was in CI) still passes
        # an empty model string straight to Anthropic and 400s. `or` catches
        # both "unset" and "set but empty".
        model=os.environ.get("CLAUDE_CONTENT_MODEL") or DEFAULT_CLAUDE_CONTENT_MODEL,
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
