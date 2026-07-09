from __future__ import annotations

from agent_studio.schemas import AutomationPackage, ModuleRequest, TaskPlan
from agent_studio.utils import stable_id


def build_module_requests(plan: TaskPlan) -> AutomationPackage:
    requests = []
    for task in plan.tasks:
        target_module = "M04_AUTOMATION_STUDIO"
        request = ModuleRequest(
            request_id=stable_id("mreq", plan.plan_id, task.task_id, task.action),
            project=plan.project,
            target_module=target_module,
            request_type=task.action,
            source_task_id=task.task_id,
            payload={
                "intended_module": task.module,
                "action": task.action,
                "input_refs": task.input_refs,
                "goal": plan.goal,
            },
            approval_required=task.approval_required,
        )
        requests.append(request)
    return AutomationPackage(project=plan.project, plan_id=plan.plan_id, execution_mode=plan.execution_mode, module_requests=requests, approval_required=plan.approval_required)
