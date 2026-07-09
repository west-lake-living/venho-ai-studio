from __future__ import annotations

import importlib
import json
from pathlib import Path

from typer.testing import CliRunner

from analytics_feedback.adapters import MockMetricsAdapter
from analytics_feedback.alert_generator import generate_alert
from analytics_feedback.baseline_calculator import calculate_baseline
from analytics_feedback.cli import app
from analytics_feedback.collection_scheduler import build_collection_tasks
from analytics_feedback.feedback_advisory_generator import generate_feedback_advisory
from analytics_feedback.ingestion_router import parse_delivery_receipt
from analytics_feedback.metrics_standardizer import standardize_metrics
from analytics_feedback.performance_scorer import score_snapshot
from analytics_feedback.report_generator import generate_report
from analytics_feedback.sentiment_scorer import score_comments
from analytics_feedback.stores import RawMetricsStore, SnapshotStore

runner = CliRunner()


def _receipt_data() -> dict:
    return {
        "contract_version": "1.0",
        "package_id": "pkg_20260709_westlake_sunset",
        "project": "venho_hotel",
        "published_timestamp": "2026-07-09T04:00:05Z",
        "content_type": "reel",
        "pillar": "westlake_lifestyle",
        "theme": "sunset",
        "platform_results": {
            "facebook": {"success": False, "status": "FAILED"},
            "instagram": {
                "success": True,
                "status": "PUBLISHED",
                "post_id": "ig_media_1792837492384",
                "public_url": "https://instagram.example.test/p/C-923847/",
            },
        },
    }


def test_analytics_feedback_imports_and_scaffold_exists() -> None:
    module = importlib.import_module("analytics_feedback")
    root = Path("analytics_feedback")

    assert module.MODULE_ID == "M08"
    assert {"adapters", "schemas", "stores", "renderers", "utils"} <= {path.name for path in root.iterdir() if path.is_dir()}
    assert Path("config/projects/venho_hotel/analytics/scoring_rules.yaml").exists()


def test_delivery_receipt_router_schedules_successful_platforms_only() -> None:
    receipt = parse_delivery_receipt(_receipt_data())
    tasks = build_collection_tasks(receipt, windows=["24h", "72h"])

    assert [task.platform for task in tasks] == ["instagram", "instagram"]
    assert tasks[0].snapshot_timestamp_utc == "2026-07-10T04:00:05Z"
    assert tasks[1].snapshot_timestamp_utc == "2026-07-12T04:00:05Z"


def test_mock_adapter_standardizes_and_calculates_derived_metrics() -> None:
    receipt = parse_delivery_receipt(_receipt_data())
    raw = MockMetricsAdapter("instagram").fetch_metrics(receipt.package_id, "ig_media_1792837492384", "2026-07-12T11:00:00Z")
    snapshot = standardize_metrics(raw, receipt)

    assert snapshot.contract_version == "1.0"
    assert len(snapshot.snapshot_id) == 64
    assert snapshot.metrics.reach == 7400
    assert snapshot.metrics.views == 8900
    assert snapshot.derived.engagement_count == 1361
    assert snapshot.derived.engagement_rate_by_reach == 0.184
    assert snapshot.provenance.provider == "mock_insights"


def test_snapshot_store_is_idempotent(tmp_path: Path) -> None:
    receipt = parse_delivery_receipt(_receipt_data())
    raw = MockMetricsAdapter("instagram").fetch_metrics(receipt.package_id, "ig_media_1792837492384", "2026-07-12T11:00:00Z")
    snapshot = standardize_metrics(raw, receipt)
    store = SnapshotStore("venho_hotel", data_root=tmp_path / "data" / "projects")

    first = store.save(snapshot.snapshot_id, snapshot)
    second = store.save(snapshot.snapshot_id, snapshot.model_copy(update={"pillar": "changed"}))

    assert first == second
    assert store.load(snapshot.snapshot_id)["pillar"] == "westlake_lifestyle"


def test_performance_scoring_and_advisory_contract() -> None:
    receipt = parse_delivery_receipt(_receipt_data())
    raw = MockMetricsAdapter("instagram").fetch_metrics(receipt.package_id, "ig_media_1792837492384", "2026-07-12T11:00:00Z")
    snapshot = standardize_metrics(raw, receipt)
    weaker_history = [
        snapshot.model_copy(update={"derived": snapshot.derived.model_copy(update={"engagement_rate_by_reach": 0.129})})
        for _ in range(12)
    ]
    baseline = calculate_baseline(snapshot, weaker_history)
    score = score_snapshot(snapshot, baseline)
    sentiment = score_comments(raw.comments)
    advisory = generate_feedback_advisory(snapshot, score, sentiment)

    assert score.performance_label == "OUTPERFORM"
    assert score.relative_score == 1.43
    assert score.confidence == "medium"
    assert score.warnings
    assert advisory.status == "pending_approval"
    assert advisory.approval_route == ["M04_AUTOMATION_STUDIO", "M09_AGENT_STUDIO"]
    assert advisory.recommendations[0].target == "content_pillars.westlake_lifestyle"
    assert advisory.recommendations[0].theme == "sunset"


def test_sentiment_guardrail_generates_critical_alert() -> None:
    receipt = parse_delivery_receipt(_receipt_data())
    comments = ["dirty", "refund please", "rude", "ban", "unsafe", "ok", "ok", "ok", "ok", "ok"]
    raw = MockMetricsAdapter("facebook", comments=comments).fetch_metrics(receipt.package_id, "fb_1", "2026-07-12T11:00:00Z")
    sentiment = score_comments(raw.comments)
    alert = generate_alert(raw, sentiment, project=receipt.project)

    assert sentiment.negative_sentiment_spike is True
    assert alert is not None
    assert alert.severity == "CRITICAL"
    assert alert.handoff.target == "M04_AUTOMATION_STUDIO"


def test_end_to_end_report_and_cli_stay_offline(tmp_path: Path) -> None:
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(_receipt_data()), encoding="utf-8")
    receipt = parse_delivery_receipt(_receipt_data())
    raw = MockMetricsAdapter("instagram").fetch_metrics(receipt.package_id, "ig_media_1792837492384", "2026-07-12T11:00:00Z")
    snapshot = standardize_metrics(raw, receipt)
    baseline = calculate_baseline(snapshot, [snapshot] * 20)
    score = score_snapshot(snapshot, baseline)
    advisory = generate_feedback_advisory(snapshot, score, score_comments(raw.comments))
    report = generate_report(snapshot, score, advisory)

    RawMetricsStore("venho_hotel", data_root=tmp_path / "data" / "projects").save(snapshot.snapshot_id, raw)
    assert "Analytics Report" in report

    result = runner.invoke(app, [str(receipt_path), "--data-root", str(tmp_path / "data" / "projects")])
    assert result.exit_code == 0, result.output
    assert "Analytics package:" in result.output
