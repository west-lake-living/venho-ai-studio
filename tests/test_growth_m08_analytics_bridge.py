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
    bridge = M08AnalyticsBridge(data_root=tmp_path, registry=registry)

    result = bridge.observe(publication_id)

    assert result["status"] == "observed"
    assert result["snapshot_id"]
    assert result["performance_label"] in {"OUTPERFORM", "NORMAL", "UNDERPERFORM", "INSUFFICIENT_DATA"}
    assert result["advisory_id"]

    snapshot_path = tmp_path / "venho_hotel" / "analytics" / "snapshots"
    assert list(snapshot_path.glob("*.json"))


def test_measure_publication_uses_injected_bridge(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_published(registry)
    bridge = M08AnalyticsBridge(data_root=tmp_path, registry=registry)

    result = measure_publication(publication_id, bridge=bridge)

    assert result["status"] == "observed"
