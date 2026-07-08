from __future__ import annotations

import json
from typing import Any

import anthropic

from shared.vision.structured import extract_json
from shared.logging import log


class ClaudeProvider:
    """Text synthesis using Claude (no vision — consolidation only)."""

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        self.client = anthropic.Anthropic()
        self.model = model

    def synthesize(self, system_prompt: str, user_content: str) -> dict[str, Any]:
        """Send text to Claude and return structured JSON dict."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )

        raw = message.content[0].text
        tokens_in = message.usage.input_tokens
        tokens_out = message.usage.output_tokens
        log(f"  Claude synthesis: {tokens_in} in / {tokens_out} out tokens")
        return extract_json(raw)
