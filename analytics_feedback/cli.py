from __future__ import annotations

import json
import os
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
from analytics_feedback.stores import AdvisoryStore, AttributionEventStore, RawMetricsStore, ReportStore, ScoreStore, SnapshotStore
from shared.notify.telegram import TelegramNotifier

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


@app.command("reconcile-channels")
def reconcile_channels_cmd(
    days: int = typer.Option(7, min=1, max=365),
    project: str = typer.Option("venho_hotel"),
    config_root: Path = typer.Option(Path("config/projects/venho_hotel")),
    data_root: Path = typer.Option(Path("data/projects")),
    reports_root: Path | None = typer.Option(None),
    send_telegram: bool = typer.Option(False, "--send-telegram"),
) -> None:
    """Compare legacy publications with recent Meta posts; never opens the v2 DB."""
    from analytics_feedback.channel_reconcile import reconcile_channels

    notifier = None
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if send_telegram and os.environ.get("TELEGRAM_BOT_TOKEN") and chat_id:
        notifier = TelegramNotifier(bot_token=os.environ["TELEGRAM_BOT_TOKEN"])
    try:
        output = reconcile_channels(
            days=days,
            project=project,
            config_root=config_root,
            data_root=data_root,
            reports_root=reports_root,
            env=os.environ,
            telegram_notifier=notifier,
            telegram_chat_id=chat_id,
            send_telegram=send_telegram,
        )
    except (OSError, ValueError, KeyError) as exc:
        typer.echo(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), err=True)
        raise typer.Exit(code=1)
    typer.echo(json.dumps({"ok": True, "report": str(output)}, ensure_ascii=False))


@app.command()
def attribute(
    events_file: Path = typer.Argument(..., help="JSON file: list of conversion events, e.g. [{\"id\":..., \"event_type\":..., \"occurred_at\":..., \"contact\":..., \"utm_content\":...}]"),
    project: str = typer.Option("venho_hotel"),
    data_root: Path = typer.Option(Path("data/projects")),
    config_root: Path = typer.Option(Path("config/projects")),
) -> None:
    """Attribute real conversion events (booking inquiries) to the
    publication that drove them (DoD #25: "một inquiry test truy được về
    đúng một publication").

    Reads only RECONCILED publications (real `published_at`, set by
    `venho-growth reconcile` after Harry confirms a post actually went live)
    from `PublicationRegistry` -- an un-reconciled row has no real
    published timestamp to match a real event's window against.

    `events_file` must be supplied by hand today (2026-08-06): there is no
    automatic feed of real conversion events into this codebase yet (no GA4
    Data API pull, no booking-form webhook capturing utm params) -- see
    `analytics_feedback/attribution.py`'s module docstring for the full gap
    analysis. This command is the real, runnable half of DoD #25's exit
    bar ("an inquiry test traces to exactly one publication") once Harry
    supplies real event data (e.g. exported from the booking inbox/GA4 by
    hand, or a phone/Zalo inquiry logged manually).

    Results are persisted to `AttributionEventStore` (2026-08-06) -- not
    just printed once and discarded -- so Phase 7's
    `strategy_memory.collect_pilot_evidence` can read real attributed
    events back as evidence for a strategy pattern.
    """
    from analytics_feedback.attribution import AttributionPolicy, attribute_conversion_event, dedupe_conversion_events, pseudonymize_contact
    from publishing_gateway.publication_registry import PublicationRegistry

    policy = AttributionPolicy.from_file(config_root / project / "growth" / "attribution_policy.yaml")
    registry = PublicationRegistry(project, data_root=data_root)
    publications = [
        {"publication_id": item["publication_id"], "published_at": item["published_at"]}
        for item in registry.load()["publications"]
        if item.get("published_at")
    ]

    raw_events = json.loads(events_file.read_text(encoding="utf-8"))
    pseudonymized_events = []
    for event in raw_events:
        contact = event.get("contact")
        pseudonymized_events.append(
            {**event, "normalized_contact_hash": pseudonymize_contact(contact)} if contact else dict(event)
        )
    deduped = dedupe_conversion_events(pseudonymized_events, policy)

    results = [attribute_conversion_event(event, publications, policy) for event in deduped]
    store = AttributionEventStore(project, data_root)
    for result in results:
        store.save(result["id"], result, overwrite=True)
    typer.echo(json.dumps(results, ensure_ascii=False, indent=2))
