from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "projects" / "venho_hotel"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_growth_policy_registry_has_required_files_and_thresholds() -> None:
    growth = CONFIG / "growth"
    required = {
        "quality_policy.yaml",
        "model_policy.yaml",
        "budget_policy.yaml",
        "taxonomy.yaml",
        "scenario_registry.yaml",
        "attribution_policy.yaml",
        "cadence_policy.yaml",
        "queue_policy.yaml",
        "feature_flags.yaml",
        "reference_assets.yaml",
        "paid_call_costs.yaml",  # added 2026-08-06 when BudgetGate wired real paid-call metering into daily_cycle.py
    }
    assert {path.name for path in growth.glob("*.yaml")} == required

    quality = load_yaml(growth / "quality_policy.yaml")
    assert quality["image"]["dna_min"] == 9.0
    assert quality["copy"]["duplicate_similarity_block"] == 0.88
    assert quality["verdict_rules"]["validator_incomplete"] == "UNVALIDATED"
    assert "unsupported_critical_claim" in quality["kill_switches"]


def test_research_policy_registry_has_evidence_and_safety_rules() -> None:
    research = CONFIG / "research"
    required = {
        "domains.yaml",
        "evidence_policy.yaml",
        "promotion_policy.yaml",
        "trend_policy.yaml",
        "brand_safety.yaml",
        "event_sources.yaml",
        "weather_policy.yaml",
        # The one written question per domain that run_research_cycle refuses
        # to run without (plan §6.7 guardrail).
        "research_questions.yaml",
    }
    assert {path.name for path in research.glob("*.yaml")} == required

    evidence = load_yaml(research / "evidence_policy.yaml")
    assert evidence["citable_levels"] == ["R3"]
    assert "R2-T" in evidence["context_only_levels"]
    assert evidence["auto_promotion_allowed"] is False

    safety = load_yaml(research / "brand_safety.yaml")
    assert safety["human_approval"] == "mandatory"
    assert "politics_governance" in safety["forbidden_trend_categories"]


def test_feature_flags_default_real_providers_off() -> None:
    flags = load_yaml(CONFIG / "growth" / "feature_flags.yaml")
    assert flags["final_approval_required"] is True
    assert flags["research_os_enabled"] is True
    assert flags["growth_pipeline_enabled"] is False
    assert flags["real_image_provider_enabled"] is False
    assert flags["real_meta_insights_enabled"] is False
    assert flags["trend_lane_enabled"] is False
