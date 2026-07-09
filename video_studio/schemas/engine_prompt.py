from __future__ import annotations

from pydantic import BaseModel


class EnginePrompt(BaseModel):
    engine: str
    prompt: str
    language: str = "en"

