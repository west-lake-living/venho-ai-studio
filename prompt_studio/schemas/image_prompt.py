from __future__ import annotations

from typing import Literal

from prompt_studio.schemas.prompt_contract import PromptContractBase


class ImagePromptContract(PromptContractBase):
    """Image prompt (§5.1) — has visual negative_prompt, no target content language concerns."""

    prompt_type: Literal["image"]
    negative_prompt: str
