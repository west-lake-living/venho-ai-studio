from __future__ import annotations

from agent_studio.schemas import AutomationPackage, ExecutionResult
from agent_studio.utils import stable_id


def dispatch_to_automation(package: AutomationPackage, dry_run: bool = True) -> ExecutionResult:
    status = "APPROVAL_REQUIRED" if package.approval_required else ("DRY_RUN" if dry_run else "PREPARED")
    notes = ["M09 packaged all tasks through M04 Automation Studio"]
    if package.approval_required:
        notes.append("Manual gate required before any external impact action")
    return ExecutionResult(
        status=status,
        run_id=stable_id("run", package.project, package.plan_id, status),
        project=package.project,
        plan_id=package.plan_id,
        approval_required=package.approval_required,
        module_results=[request.model_dump() for request in package.module_requests],
        notes=notes,
    )
