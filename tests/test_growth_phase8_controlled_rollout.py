from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from controlled_rollout.metrics_window import has_90_day_comparison
from controlled_rollout.rollout_policy import next_rollout_stage, rollback_sequence
from controlled_rollout.runbook_validator import validate_runbook
from controlled_rollout.scorecard import evaluate_golden_set
from productize.hotel_content_engine import run_hotel_content_engine


def _golden_metrics() -> dict:
    return {
        "version": "growth-golden-v1",
        "metrics": {
            "critical_factual_precision": 1.0,
            "brand_adherence": 0.97,
            "copy_image_alignment": 0.96,
            "hotel_dna_pass": 0.96,
            "linh_an_identity_pass": 0.93,
            "duplicate_publication": 0,
            "publication_post_id_rate": 0.995,
            "human_acceptance_no_major_edit": 0.8,
            "unplanned_empty_days": 0,
        },
    }


def test_versioned_golden_scorecard_passes_93_gate() -> None:
    result = evaluate_golden_set(_golden_metrics())

    assert result.version == "growth-golden-v1"
    assert result.score >= 9.3
    assert result.passed is True


def test_golden_scorecard_requires_version_and_reports_failures() -> None:
    bad = _golden_metrics()
    bad["version"] = ""
    try:
        evaluate_golden_set(bad)
    except ValueError as exc:
        assert "version" in str(exc)
    else:
        raise AssertionError("versionless golden set must fail")

    failed = _golden_metrics()
    failed["metrics"]["duplicate_publication"] = 1
    result = evaluate_golden_set(failed)
    assert result.passed is False
    assert "duplicate_publication" in result.failures


def test_90_day_metrics_required_for_comparison() -> None:
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    metrics = [
        {"observed_at": (start + timedelta(days=index)).isoformat().replace("+00:00", "Z"), "period": "baseline" if index < 45 else "candidate"}
        for index in range(90)
    ]

    assert has_90_day_comparison(metrics)["ready"] is True
    assert has_90_day_comparison(metrics[:30])["ready"] is False


def test_rollout_requires_scorecard_metrics_and_keeps_human_approval() -> None:
    blocked = next_rollout_stage("pilot_50", scorecard_passed=True, has_90_day_metrics=False)
    allowed = next_rollout_stage("pilot_50", scorecard_passed=True, has_90_day_metrics=True)
    trend = next_rollout_stage("pilot_100", scorecard_passed=True, has_90_day_metrics=True, lane="trend")

    assert blocked.allowed is False
    assert blocked.reason == "requires_90_day_metrics"
    assert allowed.next_stage == "pilot_100"
    assert allowed.human_approval_required is True
    assert trend.allowed is False
    assert trend.reason == "trend_lane_never_auto_approves"


def test_rollback_sequence_enforces_dispatch_first_and_immutability() -> None:
    try:
        rollback_sequence(disable_dispatch_done=False)
    except ValueError as exc:
        assert "disable dispatch" in str(exc)
    else:
        raise AssertionError("rollback must require dispatch disable first")

    plan = rollback_sequence(disable_dispatch_done=True)
    assert plan["steps"][0] == "disable_dispatch"
    assert plan["forward_only_migration"] is True


def test_productize_hotel_content_engine_runs_for_hotel_2_without_core_change(tmp_path: Path) -> None:
    project_root = tmp_path / "hotel_2"
    (project_root / "content").mkdir(parents=True)
    (project_root / "growth").mkdir()
    (project_root / "content" / "tone_of_voice.yaml").write_text(yaml.safe_dump({"voice": "calm"}), encoding="utf-8")
    (project_root / "growth" / "taxonomy.yaml").write_text(yaml.safe_dump({"version": 1}), encoding="utf-8")

    result = run_hotel_content_engine(
        project="hotel_2",
        config_root=tmp_path,
        brief={"hotel_name": "Hotel Two", "objective": "increase direct booking", "single_minded_message": "Lake calm, direct booking clarity"},
    )

    assert result["project"] == "hotel_2"
    assert result["core_modified"] is False
    assert result["content_package"]["headline"] == "Hotel Two: increase direct booking"


def test_productize_skill_and_runbook_docs_exist() -> None:
    assert Path(".claude/skills/_productize/hotel-content-engine/SKILL.md").exists()
    assert validate_runbook(Path("docs/growth/controlled_rollout_runbook.md"))["valid"] is True
    assert Path("docs/growth/eval_golden_sets.md").exists()
