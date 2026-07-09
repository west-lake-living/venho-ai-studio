from __future__ import annotations

from typing import List, Literal, Optional

from prompt_studio.schemas.base import RequiredDnaItem
from prompt_studio.schemas.prompt_contract import PromptContractBase


class VideoPromptContract(PromptContractBase):
    """Video prompt (§5.2) — visual negative_prompt + optional multi-DNA merge fields.

    character_lock / environment_dna / consistency_rules are populated by the multi-DNA
    video builder (§16 Step 10); left optional here so single-DNA video prompts validate too.
    """

    prompt_type: Literal["video"]
    negative_prompt: str
    character_lock: Optional[List[RequiredDnaItem]] = None
    environment_dna: Optional[List[RequiredDnaItem]] = None
    consistency_rules: Optional[List[str]] = None
