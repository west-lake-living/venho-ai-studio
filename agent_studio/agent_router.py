from __future__ import annotations

from pathlib import Path

from agent_studio.exceptions import ERR_AGENT_NOT_FOUND, AgentStudioError


GENERIC_AGENTS = {
    "research_agent": "research_agent",
    "documentation_agent": "documentation_agent",
    "content_planning_agent": "content_planning_agent",
    "visual_planning_agent": "visual_planning_agent",
    "analytics_insight_agent": "analytics_insight_agent",
}


def route_agent(agent_id: str, project: str, config_root: Path = Path("config/projects")) -> str:
    project_agent = config_root / project / "agents" / f"{agent_id}.yaml"
    if project_agent.exists():
        return agent_id
    if agent_id in GENERIC_AGENTS:
        return agent_id
    raise AgentStudioError(ERR_AGENT_NOT_FOUND, f"Agent not found: {agent_id}", {"project": project})
