from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from controlled_rollout.cli import app
from controlled_rollout.collect_real_scorecard_metrics import collect_real_scorecard_metrics
from controlled_rollout.rollout_state_store import RolloutStateStore
from growth_orchestrator.application.daily_cycle import _scorecard_signals
from publishing_gateway.publication_registry import PublicationRegistry
from shared.jobs.slot_store import SlotStore

runner = CliRunner()


def test_scorecard_signals_extracts_claim_kill_switch_and_content_brand_fit() -> None:
    validation = {
        "verdict": "READY_FOR_REVIEW",
        "reports": [
            {"verdict": "PASS", "kill_switches": []},
            {"verdict": "PASS", "kill_switches": []},
            {"overall_score": 88.0, "dna_match_score": 0.91, "verdict": "APPROVE"},
        ],
    }
    signals = _scorecard_signals(validation)
    assert signals["claim_kill_switch_triggered"] is False
    assert signals["content_brand_fit"] == 0.91
    assert signals["content_overall_score"] == 88.0


def test_scorecard_signals_handles_empty_reports_without_crashing() -> None:
    signals = _scorecard_signals({"verdict": "READY_FOR_REVIEW", "reports": []})
    assert signals == {"claim_kill_switch_triggered": False, "content_brand_fit": None, "content_overall_score": None}


def _seed_published_row(registry: PublicationRegistry, *, publication_id: str, edited: bool, has_post_id: bool, brand_fit: float, claim_kill_switch: bool) -> None:
    reserved = registry.reserve(
        {"publication_id": publication_id, "content_package_id": f"pkg-{publication_id}", "idempotency_key": f"idem-{publication_id}", "platform": "facebook"}
    )
    registry.update(
        reserved["publication_id"],
        status="PUBLISHED",
        platform_post_id="fb-123" if has_post_id else None,
        edited_by="harry" if edited else None,
        scorecard_signals={"claim_kill_switch_triggered": claim_kill_switch, "content_brand_fit": brand_fit, "content_overall_score": brand_fit * 100},
    )


def test_collect_real_scorecard_metrics_on_empty_registry_reports_honest_gaps(tmp_path: Path) -> None:
    result = collect_real_scorecard_metrics(project="venho_hotel", data_root=tmp_path, version="v-test")

    assert result["sample_size"] == 0
    assert result["metrics"]["duplicate_publication"] == 0
    assert result["metrics"]["unplanned_empty_days"] == 0
    assert any("0 PUBLISHED publications" in gap for gap in result["data_gaps"])
    assert any("copy_image_alignment" in gap for gap in result["data_gaps"])


def test_collect_real_scorecard_metrics_aggregates_real_published_rows(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    _seed_published_row(registry, publication_id="pub-1", edited=False, has_post_id=True, brand_fit=0.95, claim_kill_switch=False)
    _seed_published_row(registry, publication_id="pub-2", edited=True, has_post_id=True, brand_fit=0.85, claim_kill_switch=False)
    _seed_published_row(registry, publication_id="pub-3", edited=False, has_post_id=False, brand_fit=0.90, claim_kill_switch=True)

    result = collect_real_scorecard_metrics(project="venho_hotel", data_root=tmp_path, version="v-test")

    assert result["sample_size"] == 3
    assert result["metrics"]["brand_adherence"] == round((0.95 + 0.85 + 0.90) / 3, 4)
    assert result["metrics"]["critical_factual_precision"] == round(2 / 3, 4)  # 2 of 3 had no kill switch
    assert result["metrics"]["publication_post_id_rate"] == round(2 / 3, 4)
    assert result["metrics"]["human_acceptance_no_major_edit"] == round(2 / 3, 4)
    assert result["metrics"]["duplicate_publication"] == 0


def test_scorecard_cli_runs_end_to_end_on_real_empty_data(tmp_path: Path) -> None:
    result = runner.invoke(app, ["scorecard", "--version", "v-test", "--data-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["version"] == "v-test"
    assert payload["passed"] is False  # honest: missing image dims + 0 samples
    assert payload["sample_size"] == 0


def test_rollout_state_store_defaults_to_shadow_and_only_advances_on_allowed_decision(tmp_path: Path) -> None:
    store = RolloutStateStore("venho_hotel", tmp_path)
    assert store.status()["current_stage"] == "shadow"

    blocked = store.record_decision({"current_stage": "shadow", "next_stage": "pilot_25", "allowed": False, "reason": "scorecard_not_passed"})
    assert blocked["current_stage"] == "shadow"
    assert len(blocked["history"]) == 1

    allowed = store.record_decision({"current_stage": "shadow", "next_stage": "pilot_25", "allowed": True, "reason": None})
    assert allowed["current_stage"] == "pilot_25"
    assert len(allowed["history"]) == 2


def test_rollout_advance_cli_is_blocked_on_real_empty_pilot_data(tmp_path: Path) -> None:
    result = runner.invoke(app, ["rollout-advance", "--scorecard-version", "v-test", "--data-root", str(tmp_path)])

    assert result.exit_code == 1  # honestly blocked, not an error
    payload = json.loads(result.output)
    assert payload["decision"]["allowed"] is False
    assert RolloutStateStore("venho_hotel", tmp_path).status()["current_stage"] == "shadow"


def test_rollout_advance_cli_advances_once_real_data_clears_the_gate(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    for index in range(3):
        _seed_published_row(registry, publication_id=f"pub-{index}", edited=False, has_post_id=True, brand_fit=0.97, claim_kill_switch=False)

    result = runner.invoke(
        app,
        ["rollout-advance", "--scorecard-version", "v-test", "--metrics-days", "0", "--data-root", str(tmp_path)],
    )

    # Still blocked: 3/9 image dims are structurally missing (no real Vision
    # QC run recorded) regardless of how good the other 6 look -- proves the
    # gate cannot be gamed by only the collectible dimensions.
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["decision"]["allowed"] is False
    assert payload["scorecard"]["passed"] is False
    assert any(f.startswith("missing:") for f in payload["scorecard"]["failures"])


def test_rollback_plan_cli_enforces_dispatch_first() -> None:
    blocked = runner.invoke(app, ["rollback-plan", "--no-disable-dispatch-done"])
    assert blocked.exit_code != 0

    allowed = runner.invoke(app, ["rollback-plan", "--disable-dispatch-done"])
    assert allowed.exit_code == 0
    plan = json.loads(allowed.output)
    assert plan["steps"][0] == "disable_dispatch"


def test_runbook_validate_cli_passes_on_the_real_runbook() -> None:
    result = runner.invoke(app, ["runbook-validate"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["valid"] is True


def test_productize_run_cli_builds_a_draft_for_a_second_hotel_from_config_only(tmp_path: Path) -> None:
    config_root = tmp_path / "config"
    project_root = config_root / "hotel_2"
    (project_root / "content").mkdir(parents=True)
    (project_root / "growth").mkdir()
    (project_root / "content" / "tone_of_voice.yaml").write_text(yaml.safe_dump({"voice": "calm"}), encoding="utf-8")
    (project_root / "growth" / "taxonomy.yaml").write_text(yaml.safe_dump({"version": 1}), encoding="utf-8")
    brief_path = tmp_path / "brief.json"
    brief_path.write_text(json.dumps({"hotel_name": "Hotel Two", "objective": "increase direct booking", "single_minded_message": "Lake calm"}), encoding="utf-8")

    result = runner.invoke(app, ["productize-run", "--project", "hotel_2", "--brief-json", str(brief_path), "--config-root", str(config_root)])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["core_modified"] is False
    assert payload["content_package"]["headline"] == "Hotel Two: increase direct booking"


def test_unplanned_empty_days_metric_reads_real_missed_slots(tmp_path: Path) -> None:
    from growth_orchestrator.domain.publishing_slot import PublishingSlot

    slot_store = SlotStore(db_path=tmp_path / "venho_hotel" / "growth" / "growth.db")
    slot_store.ensure_slots([PublishingSlot(slot_id="slot-1", slot_date="2026-08-10", slot_type="regular", lane="regular", status="OPEN")])
    slot_store.transition("slot-1", "MISSED")

    result = collect_real_scorecard_metrics(project="venho_hotel", data_root=tmp_path, version="v-test")
    assert result["metrics"]["unplanned_empty_days"] == 1
