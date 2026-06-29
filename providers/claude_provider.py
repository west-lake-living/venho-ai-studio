import os
import json
from pathlib import Path
from dotenv import load_dotenv
import anthropic

from providers.base_provider import BaseTextProvider
from core.logger import log

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")


def _load_merge_prompt() -> str:
    prompt_path = BASE_DIR / "prompts" / "knowledge_merge_prompt.md"
    return prompt_path.read_text(encoding="utf-8")


class ClaudeProvider(BaseTextProvider):
    def __init__(self, model: str = "claude-sonnet-4-6"):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY chưa được cấu hình trong .env")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def merge_knowledge(self, batch_results: list[dict], category: str) -> dict:
        log(f"Claude tổng hợp {len(batch_results)} batch (category={category})...")

        system_prompt = _load_merge_prompt()

        batch_json = json.dumps(batch_results, ensure_ascii=False, indent=2)
        user_message = (
            f"Category: {category}\n"
            f"Số batch: {len(batch_results)}\n\n"
            f"Batch results:\n```json\n{batch_json}\n```\n\n"
            f"Tổng hợp thành một Visual DNA cuối cùng theo schema yêu cầu."
        )

        message = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = message.content[0].text

        # Extract JSON nếu Claude wrap trong markdown code block
        if "```json" in raw_text:
            start = raw_text.index("```json") + 7
            end = raw_text.index("```", start)
            raw_text = raw_text[start:end].strip()
        elif "```" in raw_text:
            start = raw_text.index("```") + 3
            end = raw_text.index("```", start)
            raw_text = raw_text[start:end].strip()

        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Claude trả về JSON không hợp lệ: {e}\n---\n{raw_text[:500]}")

        log(f"  → Merge OK (input_tokens: {message.usage.input_tokens}, output_tokens: {message.usage.output_tokens})")
        return result
