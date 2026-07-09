from __future__ import annotations

from pathlib import Path

from agent_studio.agent_router import route_agent
from agent_studio.automation_bridge import dispatch_to_automation
from agent_studio.context_loader import load_context
from agent_studio.execution_log import ExecutionLog
from agent_studio.missing_knowledge import detect_missing_knowledge
from agent_studio.module_request_builder import build_module_requests
from agent_studio.persona_resolver import resolve_persona
from agent_studio.request_validator import validate_agent_request
from agent_studio.result_aggregator import aggregate_result
from agent_studio.risk_classifier import classify_plan_risk
from agent_studio.schemas import AgentResponse
from agent_studio.task_planner import build_task_plan


class BaseAgent:
    def __init__(self, config_root: Path = Path("config/projects"), data_root: Path = Path("data")) -> None:
        self.config_root = config_root
        self.data_root = data_root

    def run(self, request_data: dict, persist: bool = False) -> AgentResponse:
        log = ExecutionLog()
        request = validate_agent_request(request_data)
        log.add("Request validated")
        routed_agent = route_agent(request.agent, request.project, self.config_root)
        log.add(f"Router dispatched to {routed_agent}")
        persona = resolve_persona(routed_agent, request.project, self.config_root)
        log.add(f"Persona resolved: {persona.agent_id}")
        context = load_context(request, self.data_root, self.config_root)
        log.add("Context loaded")
        missing = detect_missing_knowledge(persona, context)
        plan = build_task_plan(request, persona, context)
        log.add("Task plan generated")
        plan, risk = classify_plan_risk(plan, request.project, self.config_root)
        log.add("Risk classified")
        package = build_module_requests(plan)
        log.add("Module requests packaged for M04")
        result = dispatch_to_automation(package, dry_run=request.execution_mode != "execute")
        log.add("Automation bridge returned mock execution result")
        if persist:
            log.save(request.project, plan.plan_id, Path("data/projects"))
        return aggregate_result(
            agent_name=persona.display_name,
            project=request.project,
            execution_mode=request.execution_mode,
            plan=plan,
            package=package,
            result=result,
            risk=risk,
            knowledge_sources=list(context.get("knowledge", {}).keys()),
            missing_knowledge=missing["missing_knowledge"],
            execution_log=log.entries,
        )
