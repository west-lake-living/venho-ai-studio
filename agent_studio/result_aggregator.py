from __future__ import annotations

from agent_studio.schemas import AgentResponse, AutomationPackage, ExecutionResult, RiskAssessment, TaskPlan


def aggregate_result(
    agent_name: str,
    project: str,
    execution_mode: str,
    plan: TaskPlan,
    package: AutomationPackage,
    result: ExecutionResult,
    risk: RiskAssessment,
    knowledge_sources: list[str],
    missing_knowledge: list[str],
    execution_log: list[str],
) -> AgentResponse:
    status = "PARTIAL" if missing_knowledge else "SUCCESS"
    return AgentResponse(
        agent_name=agent_name,
        project=project,
        status=status,
        execution_mode=execution_mode,
        confidence_score=0.88 if not missing_knowledge else 0.55,
        knowledge_sources_used=knowledge_sources,
        plan=plan,
        module_requests=[
            {"target_module": request.target_module, "request_type": request.request_type, "status": request.status, "approval_required": request.approval_required}
            for request in package.module_requests
        ],
        validation_summary={"required": True, "status": "pending" if package.approval_required else "not_started"},
        missing_knowledge=missing_knowledge,
        risk_assessment=risk,
        execution_log=execution_log + result.notes,
        error_code="ERR_MISSING_KNOWLEDGE" if missing_knowledge else None,
    )
