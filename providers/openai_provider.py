import os
import json
import base64
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

from providers.base_provider import BaseImageProvider
from core.logger import log

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")


def _encode_image(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def _media_type(path: Path) -> str:
    ext = path.suffix.lower()
    mapping = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    return mapping.get(ext, "image/jpeg")


def _load_extraction_prompt() -> str:
    prompt_path = BASE_DIR / "prompts" / "visual_dna_extraction_prompt.md"
    return prompt_path.read_text(encoding="utf-8")


class OpenAIProvider(BaseImageProvider):
    def __init__(self, model: str = "gpt-4o"):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY chưa được cấu hình trong .env")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def analyze_batch(self, images: list[Path], category: str) -> dict:
        log(f"OpenAI phân tích {len(images)} ảnh (category={category})...")

        system_prompt = _load_extraction_prompt()

        content = [
            {
                "type": "text",
                "text": f"Category: {category}\nPhân tích {len(images)} ảnh sau và trích xuất Visual DNA theo schema yêu cầu.",
            }
        ]
        for img_path in images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{_media_type(img_path)};base64,{_encode_image(img_path)}",
                    "detail": "high",
                },
            })

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            response_format={"type": "json_object"},
            max_tokens=4096,
        )

        raw_text = response.choices[0].message.content
        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"OpenAI trả về JSON không hợp lệ: {e}\n---\n{raw_text[:500]}")

        log(f"  → Batch OK (tokens: {response.usage.total_tokens})")
        time.sleep(1)
        return result
