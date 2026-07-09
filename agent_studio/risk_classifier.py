from __future__ import annotations

from pathlib import Path

from agent_studio.exceptions import ERR_ACTION_BLOCKED, AgentStudioError
from agent_studio.schemas import RiskAssessment, TaskPlan
from agent_studio.schemas.risk_assessment import RISK_ORDER
from agent_studio.utils import load_yaml


DEFAULT_POLICY = {
    "risk_approval_map": {
        "read_only": "auto",
        "draft_creation": "auto",
        "internal_file_write": "config_dependent",
        "knowledge_update": "require_approval",
        "external_impact": "require_approval",
        "destructive_action": "blocked",
    }
}


def classify_plan_risk(plan: TaskPlan, project: str, config_root: Path = Path("config/projects")) -> tuple[TaskPlan, RiskAssessment]:
    policy = load_yaml(config_root / project / "agents" / "agent_policy.yaml") or DEFAULT_POLICY
    approval_map = policy.get("risk_approval_map", DEFAULT_POLICY["risk_approval_map"])
    highest = "read_only"
    approvals: list[str] = []
    blocked = False
    updated_tasks = []
    for task in plan.tasks:
        risk = task.risk_level
        if RISK_ORDER.index(risk) > RISK_ORDER.index(highest):
            highest = risk
        rule = approval_map.get(risk, "require_approval")
        approval_required = task.approval_required or rule in {"require_approval", "config_dependent"}
        if rule == "blocked":
            blocked = True
            approval_required = True
        if approval_required:
            approvals.append(task.task_id)
        updated_tasks.append(task.model_copy(update={"approval_required": approval_required}))
    updated_plan = plan.model_copy(update={"tasks": updated_tasks, "approval_required": bool(approvals)})
    assessment = RiskAssessment(highest_risk=highest, manual_gate_required=bool(approvals), blocked=blocked, approvals_required=approvals)
    if blocked:
        raise AgentStudioError(ERR_ACTION_BLOCKED, "Destructive action is blocked by policy", {"plan_id": plan.plan_id})
    return updated_plan, assessment
