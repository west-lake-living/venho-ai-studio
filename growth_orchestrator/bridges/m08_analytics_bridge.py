from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from analytics_feedback.adapters.base_metrics_adapter import BaseMetricsAdapter
from analytics_feedback.adapters.mock_metrics import MockMetricsAdapter
from analytics_feedback.baseline_calculator import calculate_baseline
from analytics_feedback.meta_insights import build_metrics_adapter
from analytics_feedback.feedback_advisory_generator import generate_feedback_advisory
from analytics_feedback.metrics_standardizer import standardize_metrics
from analytics_feedback.performance_scorer import score_snapshot
from analytics_feedback.report_generator import generate_report
from analytics_feedback.research_question_generator import generate_research_question_from_analytics
from analytics_feedback.schemas.delivery_receipt_ref import DeliveryReceiptRef, PlatformReceiptRef
from analytics_feedback.sentiment_scorer import score_comments
from analytics_feedback.stores import AdvisoryStore, RawMetricsStore, ReportStore, ScoreStore, SnapshotStore
from publishing_gateway.publication_registry import PublicationRegistry

MetricsAdapterFactory = Callable[[str], BaseMetricsAdapter]


class M08AnalyticsBridge:
    """Real bridge to analytics_feedback (M08) -- replaces the `pending_observation` stub.

    `metrics_adapter_factory` defaults to `meta_insights.build_metrics_adapter`
    (2026-08-06 -- previously hardcoded `MockMetricsAdapter` directly, which
    meant `feature_flags.yaml`'s `meta_insights_enabled` flag existed but
    had zero effect on this real entry point). `build_metrics_adapter`
    itself still returns `MockMetricsAdapter` while the flag is off (the
    default, and the honest state today -- no real Facebook/Instagram
    Insights or Zalo OA analytics API integration is built); flipping the
    flag on without first implementing a real Graph API adapter makes it
    raise loudly instead of silently mocking, which is the correct failure
    mode. Everything downstream (standardize/score/sentiment/advisory/
    report/stores) is already real, not mocked.
    """

    def __init__(
        self,
        *,
        project: str = "venho_hotel",
        data_root: Path = Path("data/projects"),
        registry: Optional[PublicationRegistry] = None,
        metrics_adapter_factory: Optional[MetricsAdapterFactory] = None,
        questions_root: Optional[Path] = None,
    ) -> None:
        self.project = project
        self.data_root = data_root
        self.registry = registry or PublicationRegistry(project, data_root=data_root)
        self.metrics_adapter_factory = metrics_adapter_factory or build_metrics_adapter
        # research/questions is the real Research OS vault (see research/README.md
        # ownership split) -- every observation feeds a "why" question back
        # into research, closing DoD #25's advisory -> new-research-question loop.
        self.questions_root = questions_root or Path("research/questions")

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

        # DoD #25: the feedback loop must generate new research questions, not
        # stop at "recommendation pending_approval". INSUFFICIENT_DATA maps to
        # the generator's "INCONCLUSIVE" branch (its exact expected string);
        # UNDERPERFORM flags qbsr_drop=True; everything else still asks "what
        # explains this pattern" via the advisory's own summary.
        research_question_path = generate_research_question_from_analytics(
            {
                "id": advisory.advisory_id,
                "status": "INCONCLUSIVE" if score.performance_label == "INSUFFICIENT_DATA" else score.performance_label,
                "scope": {"pillar": snapshot.pillar, "platform": snapshot.platform},
                "qbsr_drop": score.performance_label == "UNDERPERFORM",
                "pattern": advisory.analysis_summary,
            },
            root=self.questions_root,
        )

        return {
            "publication_id": publication_id,
            "status": "observed",
            "snapshot_id": snapshot.snapshot_id,
            "performance_label": score.performance_label,
            "relative_score": score.relative_score,
            "advisory_id": advisory.advisory_id,
            "advisory_status": advisory.status,
            "research_question_path": str(research_question_path),
        }
