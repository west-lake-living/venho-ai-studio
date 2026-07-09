from __future__ import annotations

import json

from agent_studio.schemas import AgentResponse


def render_response_json(response: AgentResponse) -> str:
    return json.dumps(response.model_dump(mode="json"), ensure_ascii=False, indent=2)
