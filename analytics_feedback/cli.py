from __future__ import annotations

from pathlib import Path

import typer

from analytics_feedback.adapters import MockMetricsAdapter
from analytics_feedback.baseline_calculator import calculate_baseline
from analytics_feedback.feedback_advisory_generator import generate_feedback_advisory
from analytics_feedback.ingestion_router import load_delivery_receipt
from analytics_feedback.metrics_standardizer import standardize_metrics
from analytics_feedback.performance_scorer import score_snapshot
from analytics_feedback.report_generator import generate_report
from analytics_feedback.sentiment_scorer import score_comments
from analytics_feedback.stores import AdvisoryStore, RawMetricsStore, ReportStore, ScoreStore, SnapshotStore

app = typer.Typer(help="Module 08 Analytics & Feedback Loop")


@app.command()
def collect(receipt: Path, data_root: Path = Path("data/projects"), dry_run: bool = True) -> None:
    receipt_ref = load_delivery_receipt(receipt)
    first_platform = next((name for name, result in receipt_ref.platform_results.items() if result.success and result.post_id), None)
    if not first_platform:
        raise typer.BadParameter("receipt has no successful platform with post_id")
    result = receipt_ref.platform_results[first_platform]
    raw = MockMetricsAdapter(first_platform).fetch_metrics(receipt_ref.package_id, result.post_id or "", receipt_ref.published_timestamp)
    snapshot = standardize_metrics(raw, receipt_ref)
    baseline = calculate_baseline(snapshot, [])
    score = score_snapshot(snapshot, baseline)
    sentiment = score_comments(raw.comments)
    advisory = generate_feedback_advisory(snapshot, score, sentiment)
    report = generate_report(snapshot, score, advisory)
    if not dry_run:
        RawMetricsStore(receipt_ref.project, data_root).save(snapshot.snapshot_id, raw)
        SnapshotStore(receipt_ref.project, data_root).save(snapshot.snapshot_id, snapshot)
        ScoreStore(receipt_ref.project, data_root).save(snapshot.snapshot_id, score)
        AdvisoryStore(receipt_ref.project, data_root).save(advisory.advisory_id, advisory)
        ReportStore(receipt_ref.project, data_root).save_markdown(f"report_{snapshot.snapshot_id}", report)
    typer.echo(f"Analytics package: {snapshot.package_id} / {snapshot.platform}")
    typer.echo(f"Score: {score.performance_label} ({score.relative_score})")
