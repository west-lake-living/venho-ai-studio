from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from analytics_feedback.adapters.base_metrics_adapter import BaseMetricsAdapter
from analytics_feedback.adapters.mock_metrics import MockMetricsAdapter
from analytics_feedback.baseline_calculator import calculate_baseline
from analytics_feedback.feedback_advisory_generator import generate_feedback_advisory
from analytics_feedback.metrics_standardizer import standardize_metrics
from analytics_feedback.performance_scorer import score_snapshot
from analytics_feedback.report_generator import generate_report
from analytics_feedback.schemas.delivery_receipt_ref import DeliveryReceiptRef, PlatformReceiptRef
from analytics_feedback.sentiment_scorer import score_comments
from analytics_feedback.stores import AdvisoryStore, RawMetricsStore, ReportStore, ScoreStore, SnapshotStore
from publishing_gateway.publication_registry import PublicationRegistry

MetricsAdapterFactory = Callable[[str], BaseMetricsAdapter]


class M08AnalyticsBridge:
    """Real bridge to analytics_feedback (M08) -- replaces the `pending_observation` stub.

    `metrics_adapter_factory` defaults to `MockMetricsAdapter` -- there is no
    real Facebook/Instagram Insights or Zalo OA analytics API integration
    built (that needs its own credentialed adapter, a separate task from
    "wire M08 into growth_orchestrator"). Swap the factory for a real one
    once that adapter exists; everything downstream (standardize/score/
    sentiment/advisory/report/stores) is already real, not mocked.
    """

    def __init__(
        self,
        *,
        project: str = "venho_hotel",
        data_root: Path = Path("data/projects"),
        registry: Optional[PublicationRegistry] = None,
        metrics_adapter_factory: Optional[MetricsAdapterFactory] = None,
    ) -> None:
        self.project = project
        self.data_root = data_root
        self.registry = registry or PublicationRegistry(project, data_root=data_root)
        self.metrics_adapter_factory = metrics_adapter_factory or MockMetricsAdapter

    def observe(self, publication_id: str) -> dict[str, Any]:
        publication = self.registry.find(publication_id)
        if publication is None:
            raise KeyError(f"Unknown publication_id: {publication_id}")

        post_id = publication.get("platform_post_id")
        if not post_id:
            return {
                "publication_id": publication_id,
                "status": "pending_observation",
                "reason": "no platform_post_id yet (not confirmed published)",
            }

        platform = publication["platform"]
        receipt = DeliveryReceiptRef(
            package_id=publication["content_package_id"],
            project=self.project,
            published_timestamp=publication.get("updated_at") or publication.get("created_at"),
            platform_results={
                platform: PlatformReceiptRef(
                    success=True,
                    status="PUBLISHED",
                    post_id=post_id,
                    public_url=publication.get("permalink"),
                )
            },
        )

        adapter = self.metrics_adapter_factory(platform)
        raw = adapter.fetch_metrics(receipt.package_id, post_id, receipt.published_timestamp)
        snapshot = standardize_metrics(raw, receipt)
        baseline = calculate_baseline(snapshot, [])
        score = score_snapshot(snapshot, baseline)
        sentiment = score_comments(raw.comments)
        advisory = generate_feedback_advisory(snapshot, score, sentiment)
        report = generate_report(snapshot, score, advisory)

        RawMetricsStore(self.project, self.data_root).save(snapshot.snapshot_id, raw)
        SnapshotStore(self.project, self.data_root).save(snapshot.snapshot_id, snapshot)
        ScoreStore(self.project, self.data_root).save(snapshot.snapshot_id, score)
        AdvisoryStore(self.project, self.data_root).save(advisory.advisory_id, advisory)
        ReportStore(self.project, self.data_root).save_markdown(f"report_{snapshot.snapshot_id}", report)

        return {
            "publication_id": publication_id,
            "status": "observed",
            "snapshot_id": snapshot.snapshot_id,
            "performance_label": score.performance_label,
            "relative_score": score.relative_score,
            "advisory_id": advisory.advisory_id,
            "advisory_status": advisory.status,
        }
