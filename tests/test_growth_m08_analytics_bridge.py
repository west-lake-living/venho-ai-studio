from __future__ import annotations

from pathlib import Path

import pytest

from growth_orchestrator.application.measure_publication import measure_publication
from growth_orchestrator.bridges.m08_analytics_bridge import M08AnalyticsBridge
from publishing_gateway.publication_registry import PublicationRegistry


def _reserve_published(registry: PublicationRegistry, *, platform: str = "facebook") -> str:
    reserved = registry.reserve(
        {
            "publication_id": f"pub-{platform}-1",
            "content_package_id": "pkg-1",
            "idempotency_key": f"idem-{platform}-1",
            "platform": platform,
        }
    )
    registry.update(
        reserved["publication_id"],
        status="PUBLISHED",
        platform_post_id="post-123",
        permalink="https://example.test/post-123",
    )
    return reserved["publication_id"]


def test_observe_unknown_publication_raises(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    bridge = M08AnalyticsBridge(data_root=tmp_path, registry=registry)
    with pytest.raises(KeyError):
        bridge.observe("nope")


def test_observe_without_post_id_returns_pending(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    reserved = registry.reserve(
        {"publication_id": "pub-1", "content_package_id": "pkg-1", "idempotency_key": "idem-1", "platform": "facebook"}
    )
    bridge = M08AnalyticsBridge(data_root=tmp_path, registry=registry)

    result = bridge.observe(reserved["publication_id"])

    assert result["status"] == "pending_observation"


def test_observe_published_publication_scores_and_saves_snapshot(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_published(registry)
    bridge = M08AnalyticsBridge(data_root=tmp_path, registry=registry, questions_root=tmp_path / "research_questions")

    result = bridge.observe(publication_id)

    assert result["status"] == "observed"
    assert result["snapshot_id"]
    assert result["performance_label"] in {"OUTPERFORM", "NORMAL", "UNDERPERFORM", "INSUFFICIENT_DATA"}
    assert result["advisory_id"]

    snapshot_path = tmp_path / "venho_hotel" / "analytics" / "snapshots"
    assert list(snapshot_path.glob("*.json"))


def test_observe_carries_the_publication_pillar_onto_the_saved_snapshot(tmp_path: Path) -> None:
    """Regression test (2026-08-06, Phase 7 prep): before this, observe()
    never read `pillar` off the registry row, so every real snapshot's
    `pillar` defaulted to "unknown" -- making pillar-based grouping
    (strategy_memory.collect_pilot_evidence) impossible."""
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_published(registry)
    registry.update(publication_id, pillar="lake_view_rooms")
    bridge = M08AnalyticsBridge(data_root=tmp_path, registry=registry, questions_root=tmp_path / "research_questions")

    result = bridge.observe(publication_id)

    snapshot_path = tmp_path / "venho_hotel" / "analytics" / "snapshots" / f"{result['snapshot_id']}.json"
    import json

    saved = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert saved["pillar"] == "lake_view_rooms"


def test_observe_generates_a_new_research_question(tmp_path: Path) -> None:
    """DoD #25: the feedback loop must not stop at 'advisory pending_approval'
    -- every real observation should also write a new research question back
    into the Research OS vault (research/questions/, injectable for tests)."""
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_published(registry)
    questions_root = tmp_path / "research_questions"
    bridge = M08AnalyticsBridge(data_root=tmp_path, registry=registry, questions_root=questions_root)

    result = bridge.observe(publication_id)

    assert result["research_question_path"]
    question_path = Path(result["research_question_path"])
    assert question_path.exists()
    assert question_path.parent == questions_root
    assert question_path.read_text(encoding="utf-8").strip()


def test_measure_publication_uses_injected_bridge(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_published(registry)
    bridge = M08AnalyticsBridge(data_root=tmp_path, registry=registry, questions_root=tmp_path / "research_questions")

    result = measure_publication(publication_id, bridge=bridge)

    assert result["status"] == "observed"
