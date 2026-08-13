from __future__ import annotations

from pathlib import Path
from shutil import copyfile

from growth_orchestrator.application.budget_gate import BudgetGate
from growth_orchestrator.application.daily_cycle import DEFAULT_PLATFORMS, run_daily_cycle
from growth_orchestrator.bridges.m05_content_bridge import M05ContentBridge
from content_studio.builders.social_builder import mock_social_generator
from shared.budget.ledger import BudgetLedger, BudgetPolicy


def _tmp_data_root(tmp_path: Path) -> Path:
    root = tmp_path / "data" / "projects"
    knowledge_dir = root / "venho_hotel" / "knowledge"
    knowledge_dir.mkdir(parents=True)
    # VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json (no suffix) no longer exists on
    # disk -- see the identical fix in tests/test_growth_daily_cycle.py.
    for name in [
        "VENHO_HOTEL_WESTLAKE_DNA.json",
        "VENHO_HOTEL_LAKE_VIEW_ROOM_1_DNA.json",
        "VENHO_HOTEL_LAKE_VIEW_ROOM_2_DNA.json",
        "VENHO_HOTEL_OUTSIDE_DNA.json",
        "VENHO_HOTEL_LOBBY_DNA.json",
    ]:
        copyfile(Path("data/projects/venho_hotel/knowledge") / name, knowledge_dir / name)
    return root


class _AlwaysApproveValidatorBridge:
    def validate_package(self, brief: dict, copy_candidate: dict) -> dict:
        return {"verdict": "READY_FOR_REVIEW", "reports": []}


def test_budget_gate_blocks_reservation_once_cap_is_reached(tmp_path: Path) -> None:
    ledger = BudgetLedger(db_path=tmp_path / "growth.db")
    policy = BudgetPolicy(monthly_cap_minor=1000, alert_thresholds=[0.7, 0.85, 1.0])
    gate = BudgetGate(ledger=ledger, policy=policy, costs={"text_generation_minor": 400})

    ok1, _ = gate.try_reserve("text_generation_minor", "r1")
    ok2, _ = gate.try_reserve("text_generation_minor", "r2")
    ok3, evaluation = gate.try_reserve("text_generation_minor", "r3")  # 3 x 400 = 1200 > 1000 cap

    assert ok1 is True
    assert ok2 is True
    assert ok3 is False
    assert evaluation["blocked"] is True


def test_budget_gate_release_frees_the_reservation_for_a_retry(tmp_path: Path) -> None:
    ledger = BudgetLedger(db_path=tmp_path / "growth.db")
    policy = BudgetPolicy(monthly_cap_minor=500, alert_thresholds=[0.7, 0.85, 1.0])
    gate = BudgetGate(ledger=ledger, policy=policy, costs={"text_generation_minor": 400})

    ok1, _ = gate.try_reserve("text_generation_minor", "r1")
    assert ok1 is True  # 400/500 = 0.8, not yet at cap
    gate.release("r1", "text_generation_minor")  # e.g. the real call raised

    ok2, _ = gate.try_reserve("text_generation_minor", "r2")
    assert ok2 is True  # released amount is no longer OUTSTANDING -- a second attempt is not pre-blocked by the first's failed one


def test_budget_gate_commit_keeps_the_spend_counted(tmp_path: Path) -> None:
    ledger = BudgetLedger(db_path=tmp_path / "growth.db")
    policy = BudgetPolicy(monthly_cap_minor=500, alert_thresholds=[0.7, 0.85, 1.0])
    gate = BudgetGate(ledger=ledger, policy=policy, costs={"text_generation_minor": 400})

    ok1, _ = gate.try_reserve("text_generation_minor", "r1")
    gate.commit("r1", "text_generation_minor")
    assert ok1 is True

    ok2, evaluation = gate.try_reserve("text_generation_minor", "r2")
    assert ok2 is False  # committed spend still counts against the cap (400 + 400 > 500)
    assert evaluation["blocked"] is True


def test_run_daily_cycle_skips_a_platform_when_text_budget_is_exhausted(tmp_path: Path) -> None:
    """Regression test: before BudgetGate was wired in (2026-08-06), every
    real gpt-5.5/gpt-image-2/GPT-4o call in daily_cycle ran completely
    unmetered against budget_policy.yaml's cap."""
    data_root = _tmp_data_root(tmp_path)
    content_bridge = M05ContentBridge(data_root=data_root, generator_fn=mock_social_generator)

    ledger = BudgetLedger(db_path=tmp_path / "growth.db")
    policy = BudgetPolicy(monthly_cap_minor=0, alert_thresholds=[0.7, 0.85, 1.0])  # cap already exhausted
    gate = BudgetGate(ledger=ledger, policy=policy, costs={"text_generation_minor": 1})

    result = run_daily_cycle(
        "monday",
        data_root=data_root,
        generate_image=False,
        content_bridge=content_bridge,
        validator_bridge=_AlwaysApproveValidatorBridge(),
        budget_gate=gate,
    )

    assert result.publications == []
    assert len(result.errors) == len(DEFAULT_PLATFORMS)
    assert all("budget cap reached" in error["error"] for error in result.errors)
