from __future__ import annotations

from typing import List, Literal

from prompt_studio.schemas.prompt_contract import PromptContractBase


class ContentPromptContract(PromptContractBase):
    """Content prompt (§5.3) — no visual negative_prompt; tone/claim restrictions instead.

    target_language (already required on the base contract) drives the language the AI
    must WRITE the content in; the instructions themselves stay English (§10).
    """

    prompt_type: Literal["content"]
    restrictions: List[str]
