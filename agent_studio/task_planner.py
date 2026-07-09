from __future__ import annotations

from agent_studio.schemas import AgentRequest, Persona, Task, TaskPlan
from agent_studio.utils import stable_id


def build_task_plan(request: AgentRequest, persona: Persona, loaded_context: dict) -> TaskPlan:
    refs = list(dict.fromkeys(persona.required_knowledge + list(request.context.get("knowledge_refs", []))))
    tasks: list[Task] = []
    if request.context.get("analytics_refs") or "analytics_interpretation" in persona.scope or persona.base_agent == "analytics_insight_agent":
        tasks.append(Task(task_id="task_001", module="M08_ANALYTICS_FEEDBACK", action="read_advisory", input_refs=list(request.context.get("analytics_refs", [])), risk_level="read_only"))
    if persona.base_agent in {"content_planning_agent", "research_agent", "documentation_agent"}:
        action = "create_content_request" if persona.base_agent == "content_planning_agent" else f"create_{persona.base_agent.replace('_agent', '')}_plan"
        tasks.append(Task(task_id=f"task_{len(tasks)+1:03d}", module="M05_CONTENT_STUDIO" if persona.base_agent == "content_planning_agent" else "M04_AUTOMATION_STUDIO", action=action, input_refs=refs, risk_level="draft_creation"))
    if persona.base_agent == "visual_planning_agent":
        tasks.append(Task(task_id=f"task_{len(tasks)+1:03d}", module="M06_VIDEO_STUDIO", action="create_visual_or_video_request", input_refs=refs, risk_level="draft_creation"))
        tasks.append(Task(task_id=f"task_{len(tasks)+1:03d}", module="M03_VALIDATOR_STUDIO", action="prepare_validation_request", input_refs=refs, risk_level="read_only"))
    external_words = ("publish", "đăng", "facebook", "instagram", "threads", "google business", "send email", "gửi email")
    if any(word in request.goal.lower() for word in external_words):
        tasks.append(Task(task_id=f"task_{len(tasks)+1:03d}", module="M04_AUTOMATION_STUDIO", action="prepare_manual_gate", input_refs=["content_package"], risk_level="external_impact", approval_required=True))
    if not tasks:
        tasks.append(Task(task_id="task_001", module="M04_AUTOMATION_STUDIO", action="prepare_plan", input_refs=refs, risk_level="draft_creation"))
    return TaskPlan(
        plan_id=stable_id("plan", request.project, request.agent, request.goal),
        project=request.project,
        agent=request.agent,
        goal=request.goal,
        tasks=tasks[: request.constraints.max_steps],
        max_steps=request.constraints.max_steps,
        execution_mode=request.execution_mode,
    )
