from __future__ import annotations

from pathlib import Path
from typing import Any

from openai import OpenAI

from shared.vision.image_loader import image_to_base64
from shared.vision.structured import extract_json
from shared.logging import log


class OpenAIVisionProvider:
    """Single-image vision analysis using OpenAI gpt-4o."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0.0) -> None:
        self.client = OpenAI()
        self.model = model
        self.temperature = temperature

    def analyze(self, image_path: Path, system_prompt: str) -> dict[str, Any]:
        """Analyze a single image and return structured dict."""
        b64, media_type = image_to_base64(image_path)

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=4096,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{b64}",
                                "detail": "high",
                            },
                        },
                        {
                            "type": "text",
                            "text": "Analyze this image and return JSON only.",
                        },
                    ],
                },
            ],
        )

        raw = response.choices[0].message.content or ""
        tokens_in = response.usage.prompt_tokens if response.usage else 0
        tokens_out = response.usage.completion_tokens if response.usage else 0
        log(f"  OpenAI vision: {tokens_in} in / {tokens_out} out tokens")
        return extract_json(raw)
