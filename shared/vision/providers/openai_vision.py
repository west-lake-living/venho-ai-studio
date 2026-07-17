from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from openai import OpenAI

from shared.vision.image_loader import image_to_base64
from shared.vision.structured import extract_json
from shared.logging import log


class OpenAIVisionProvider:
    """Single- and multi-image vision analysis using OpenAI gpt-4o."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0.0) -> None:
        self.client = OpenAI()
        self.model = model
        self.temperature = temperature

    def analyze(self, image_path: Path, system_prompt: str) -> dict[str, Any]:
        """Analyze a single image and return structured dict."""
        return self.analyze_many(
            [image_path], system_prompt, text_prompt="Analyze this image and return JSON only."
        )

    def analyze_many(
        self,
        image_paths: Sequence[Path],
        system_prompt: str,
        text_prompt: str = "Analyze these images and return JSON only.",
    ) -> dict[str, Any]:
        """Analyze one or more images in a single call and return structured dict.

        Image order is preserved in the message content — the caller's prompt
        is responsible for telling the model what each image position means
        (e.g. "image 1 is the candidate, images 2+ are approved references").
        """
        image_blocks = []
        for image_path in image_paths:
            b64, media_type = image_to_base64(image_path)
            image_blocks.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{b64}",
                    "detail": "high",
                },
            })

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
                        *image_blocks,
                        {"type": "text", "text": text_prompt},
                    ],
                },
            ],
        )

        raw = response.choices[0].message.content or ""
        tokens_in = response.usage.prompt_tokens if response.usage else 0
        tokens_out = response.usage.completion_tokens if response.usage else 0
        log(f"  OpenAI vision: {len(image_paths)} image(s), {tokens_in} in / {tokens_out} out tokens")
        return extract_json(raw)
