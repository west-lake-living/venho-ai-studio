from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from automation_studio.errors import WorkflowConfigError
from automation_studio.workflow_loader import Workflow


@dataclass(frozen=True)
class SchedulerPlan:
    enabled: bool
    trigger_type: str
    message: str
    config: dict[str, Any]


def parse_scheduler_plan(workflow: Workflow) -> SchedulerPlan:
    """Parse scheduler config without enabling background execution in MVP."""
    trigger = workflow.trigger or {"type": "manual"}
    trigger_type = trigger.get("type", "manual")
    if trigger_type == "manual":
        return SchedulerPlan(False, trigger_type, "manual trigger only", trigger)
    if trigger_type == "schedule":
        if not trigger.get("cron"):
            raise WorkflowConfigError(f"Workflow '{workflow.workflow_id}' schedule trigger requires 'cron'")
        return SchedulerPlan(False, trigger_type, "schedule parsed but disabled in MVP", trigger)
    if trigger_type == "folder_watch":
        if not trigger.get("path"):
            raise WorkflowConfigError(f"Workflow '{workflow.workflow_id}' folder_watch trigger requires 'path'")
        return SchedulerPlan(False, trigger_type, "folder watch parsed but disabled in MVP", trigger)
    raise WorkflowConfigError(f"Workflow '{workflow.workflow_id}' has unsupported trigger type: {trigger_type}")

