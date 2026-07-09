from __future__ import annotations


ERR_INVALID_REQUEST = "ERR_INVALID_REQUEST"
ERR_AGENT_NOT_FOUND = "ERR_AGENT_NOT_FOUND"
ERR_PERSONA_INVALID = "ERR_PERSONA_INVALID"
ERR_MISSING_KNOWLEDGE = "ERR_MISSING_KNOWLEDGE"
ERR_ACTION_BLOCKED = "ERR_ACTION_BLOCKED"


class AgentStudioError(Exception):
    def __init__(self, code: str, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict:
        return {"error_code": self.code, "message": self.message, "details": self.details}
from typing import Optional
