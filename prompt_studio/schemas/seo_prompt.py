from __future__ import annotations

from typing import List, Literal

from prompt_studio.schemas.prompt_contract import PromptContractBase


class SeoPromptContract(PromptContractBase):
    """SEO prompt (§5.4) — same shape as content prompt plus keyword intent."""

    prompt_type: Literal["seo"]
    restrictions: List[str]
    keyword_intent: str
