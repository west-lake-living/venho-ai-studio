from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from agent_studio.exceptions import ERR_PERSONA_INVALID, AgentStudioError
from agent_studio.schemas import Persona
from agent_studio.utils import load_yaml


GENERIC_PERSONAS = {
    "research_agent": {"agent_id": "research_agent", "display_name": "Research Agent", "base_agent": "research_agent", "role": "Research planner", "allowed_modules": ["M01", "M04"], "forbidden_actions": ["claim_unsourced_facts"]},
    "documentation_agent": {"agent_id": "documentation_agent", "display_name": "Documentation Agent", "base_agent": "documentation_agent", "role": "Documentation planner", "allowed_modules": ["M01", "M04"], "forbidden_actions": ["external_publish"]},
    "content_planning_agent": {"agent_id": "content_planning_agent", "display_name": "Content Planning Agent", "base_agent": "content_planning_agent", "role": "Content request planner", "allowed_modules": ["M01", "M02", "M03", "M04", "M05"], "forbidden_actions": ["direct_publish"]},
    "visual_planning_agent": {"agent_id": "visual_planning_agent", "display_name": "Visual Planning Agent", "base_agent": "visual_planning_agent", "role": "Visual request planner", "allowed_modules": ["M01", "M02", "M03", "M04", "M06"], "forbidden_actions": ["direct_image_analysis"]},
    "analytics_insight_agent": {"agent_id": "analytics_insight_agent", "display_name": "Analytics Insight Agent", "base_agent": "analytics_insight_agent", "role": "Analytics advisory interpreter", "allowed_modules": ["M04", "M08"], "forbidden_actions": ["calculate_metrics"]},
}


def resolve_persona(agent_id: str, project: str, config_root: Path = Path("config/projects")) -> Persona:
    data = load_yaml(config_root / project / "agents" / f"{agent_id}.yaml") or GENERIC_PERSONAS.get(agent_id, {})
    if not data:
        raise AgentStudioError(ERR_PERSONA_INVALID, f"Persona config missing for {agent_id}", {"project": project})
    try:
        persona = Persona.model_validate(data)
    except ValidationError as exc:
        raise AgentStudioError(ERR_PERSONA_INVALID, "Persona config is invalid", {"errors": exc.errors()}) from exc
    if not persona.allowed_modules or "M04" not in persona.allowed_modules:
        raise AgentStudioError(ERR_PERSONA_INVALID, "Persona must allow M04 Automation Studio", {"agent": agent_id})
    return persona
