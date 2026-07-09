from __future__ import annotations

from typing import Union

from pydantic import ValidationError

from agent_studio.exceptions import ERR_INVALID_REQUEST, AgentStudioError
from agent_studio.schemas import AgentRequest


def validate_agent_request(data: Union[dict, AgentRequest]) -> AgentRequest:
    if isinstance(data, AgentRequest):
        return data
    try:
        return AgentRequest.model_validate(data)
    except ValidationError as exc:
        raise AgentStudioError(ERR_INVALID_REQUEST, "Agent request is invalid", {"errors": exc.errors()}) from exc
