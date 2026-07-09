from __future__ import annotations

from agent_studio.schemas import AgentResponse


def render_response_markdown(response: AgentResponse) -> str:
    plan = response.plan
    lines = [
        "# Agent Studio Response",
        "",
        f"- Agent: {response.agent_name}",
        f"- Project: {response.project}",
        f"- Status: {response.status}",
        f"- Execution mode: {response.execution_mode}",
        f"- Approval required: {response.risk_assessment.manual_gate_required}",
        "",
        "## Plan",
    ]
    if plan:
        lines.extend([f"- Plan ID: {plan.plan_id}", f"- Goal: {plan.goal}", f"- Max steps: {plan.max_steps}", ""])
        for task in plan.tasks:
            lines.append(f"- {task.task_id}: {task.module} / {task.action} / risk={task.risk_level} / approval={task.approval_required}")
    lines.extend(["", "## Module Requests"])
    for request in response.module_requests:
        lines.append(f"- {request['target_module']} / {request['request_type']} / {request['status']}")
    lines.extend(["", "## Knowledge", f"- Used: {', '.join(response.knowledge_sources_used) or 'none'}", f"- Missing: {', '.join(response.missing_knowledge) or 'none'}"])
    lines.extend(["", "## Execution Log"])
    lines.extend(f"- {entry}" for entry in response.execution_log)
    return "\n".join(lines) + "\n"
