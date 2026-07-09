from __future__ import annotations

import importlib
import json
from pathlib import Path

from typer.testing import CliRunner

from agent_studio import MODULE_ID
from agent_studio.agent_router import route_agent
from agent_studio.agents import BaseAgent
from agent_studio.automation_bridge import dispatch_to_automation
from agent_studio.cli import app
from agent_studio.context_loader import load_context
from agent_studio.exceptions import (
    ERR_ACTION_BLOCKED,
    ERR_AGENT_NOT_FOUND,
    ERR_INVALID_REQUEST,
    ERR_MISSING_KNOWLEDGE,
    AgentStudioError,
)
from agent_studio.missing_knowledge import detect_missing_knowledge
from agent_studio.module_request_builder import build_module_requests
from agent_studio.persona_resolver import resolve_persona
from agent_studio.renderers import render_response_json, render_response_markdown
from agent_studio.request_validator import validate_agent_request
from agent_studio.risk_classifier import classify_plan_risk
from agent_studio.schemas import Task, TaskPlan
from agent_studio.task_planner import build_task_plan

runner = CliRunner()


def _request(goal: str = "Tạo campaign trải nghiệm mùa hè Hồ Tây") -> dict:
    return {
        "project": "venho_hotel",
        "agent": "marketing_agent",
        "goal": goal,
        "context": {
            "knowledge_refs": ["VENHO_BRAND_DNA", "VENHO_CONTENT_PILLARS", "VENHO_WESTLAKE_DNA"],
            "analytics_refs": ["latest_30d_advisory"],
        },
        "constraints": {"language": "vi", "validation_level": "strict", "max_steps": 5, "allow_external_actions": False},
        "execution_mode": "plan_only",
        "use_mock_engine": True,
    }


def test_agent_studio_imports_and_scaffold_exists() -> None:
    module = importlib.import_module("agent_studio")
    root = Path("agent_studio")

    assert module.MODULE_ID == "M09"
    assert MODULE_ID == "M09"
    assert {"agents", "schemas", "templates", "renderers"} <= {path.name for path in root.iterdir() if path.is_dir()}
    assert Path("config/projects/venho_hotel/agents/agent_policy.yaml").exists()


def test_request_validator_accepts_valid_and_rejects_missing_required_fields() -> None:
    request = validate_agent_request(_request())
    assert request.project == "venho_hotel"
    assert request.constraints.max_steps == 5

    try:
        validate_agent_request({"project": "venho_hotel", "goal": "missing agent"})
    except AgentStudioError as exc:
        assert exc.code == ERR_INVALID_REQUEST
    else:
        raise AssertionError("missing agent must fail validation")


def test_agent_router_and_persona_resolver_use_project_config() -> None:
    assert route_agent("marketing_agent", "venho_hotel") == "marketing_agent"
    persona = resolve_persona("marketing_agent", "venho_hotel")

    assert persona.display_name == "Ven Hồ Hotel Marketing Agent"
    assert "M04" in persona.allowed_modules
    assert "M07" not in persona.allowed_modules

    try:
        route_agent("unknown_agent", "venho_hotel")
    except AgentStudioError as exc:
        assert exc.code == ERR_AGENT_NOT_FOUND
    else:
        raise AssertionError("unknown agent must fail routing")


def test_context_loader_and_missing_knowledge_detector() -> None:
    request = validate_agent_request(_request())
    persona = resolve_persona("marketing_agent", "venho_hotel")
    context = load_context(request)
    missing = detect_missing_knowledge(persona, context)

    assert set(context["knowledge"]) == {"VENHO_BRAND_DNA", "VENHO_CONTENT_PILLARS", "VENHO_WESTLAKE_DNA"}
    assert missing["missing_knowledge"] == []

    broken = context | {"knowledge": {}}
    missing = detect_missing_knowledge(persona, broken)
    assert missing["error_code"] == ERR_MISSING_KNOWLEDGE
    assert "VENHO_BRAND_DNA" in missing["missing_knowledge"]


def test_task_planner_creates_bounded_plan_without_direct_publish() -> None:
    request = validate_agent_request(_request("Đăng campaign tuần này lên Facebook sau khi duyệt"))
    persona = resolve_persona("marketing_agent", "venho_hotel")
    context = load_context(request)
    plan = build_task_plan(request, persona, context)

    assert len(plan.tasks) <= request.constraints.max_steps
    assert any(task.module == "M08_ANALYTICS_FEEDBACK" for task in plan.tasks)
    assert any(task.module == "M05_CONTENT_STUDIO" for task in plan.tasks)
    assert any(task.action == "prepare_manual_gate" for task in plan.tasks)
    assert not any(task.module == "M07_PUBLISHING_GATEWAY" for task in plan.tasks)


def test_risk_classifier_reads_policy_and_blocks_destructive_action() -> None:
    plan = TaskPlan(
        plan_id="plan_test",
        project="venho_hotel",
        agent="marketing_agent",
        goal="delete output",
        tasks=[Task(task_id="task_001", module="M04_AUTOMATION_STUDIO", action="delete_files", risk_level="destructive_action")],
    )

    try:
        classify_plan_risk(plan, "venho_hotel")
    except AgentStudioError as exc:
        assert exc.code == ERR_ACTION_BLOCKED
    else:
        raise AssertionError("destructive action must be blocked")

    normal_plan = TaskPlan(
        plan_id="plan_publish",
        project="venho_hotel",
        agent="marketing_agent",
        goal="publish request",
        tasks=[Task(task_id="task_001", module="M04_AUTOMATION_STUDIO", action="prepare_manual_gate", risk_level="external_impact")],
    )
    classified, risk = classify_plan_risk(normal_plan, "venho_hotel")
    assert classified.tasks[0].approval_required is True
    assert risk.manual_gate_required is True


def test_module_request_builder_routes_everything_through_m04() -> None:
    request = validate_agent_request(_request("Đăng campaign tuần này lên Facebook sau khi duyệt"))
    persona = resolve_persona("marketing_agent", "venho_hotel")
    plan = build_task_plan(request, persona, load_context(request))
    plan, _risk = classify_plan_risk(plan, "venho_hotel")
    package = build_module_requests(plan)

    assert package.target_module == "M04_AUTOMATION_STUDIO"
    assert {module_request.target_module for module_request in package.module_requests} == {"M04_AUTOMATION_STUDIO"}
    assert any(module_request.payload["intended_module"] == "M05_CONTENT_STUDIO" for module_request in package.module_requests)


def test_automation_bridge_respects_approval_gate() -> None:
    request = validate_agent_request(_request("Đăng campaign tuần này lên Facebook sau khi duyệt"))
    persona = resolve_persona("marketing_agent", "venho_hotel")
    plan = build_task_plan(request, persona, load_context(request))
    plan, _risk = classify_plan_risk(plan, "venho_hotel")
    package = build_module_requests(plan)
    result = dispatch_to_automation(package, dry_run=True)

    assert result.status == "APPROVAL_REQUIRED"
    assert result.approval_required is True
    assert "M04 Automation Studio" in result.notes[0]


def test_result_aggregation_renderers_and_brand_display_rule() -> None:
    response = BaseAgent().run(_request("Đăng campaign tuần này lên Facebook sau khi duyệt"))
    markdown = render_response_markdown(response)
    payload = json.loads(render_response_json(response))

    assert response.status == "SUCCESS"
    assert response.risk_assessment.manual_gate_required is True
    assert "Ven Hồ Hotel" in markdown
    assert "Ven Ho Hotel" not in markdown
    assert payload["contract_version"] == "1.0"
    assert payload["plan"]["approval_required"] is True


def test_end_to_end_agent_cli_stays_offline() -> None:
    result = runner.invoke(
        app,
        [
            "--agent",
            "marketing_agent",
            "--project",
            "venho_hotel",
            "--goal",
            "Tạo campaign trải nghiệm mùa hè Hồ Tây",
            "--plan-only",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Agent Studio Response" in result.output
    assert "Ven Hồ Hotel Marketing Agent" in result.output
    assert "M04_AUTOMATION_STUDIO" in result.output
