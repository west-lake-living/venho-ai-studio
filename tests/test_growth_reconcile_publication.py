from __future__ import annotations

from pathlib import Path

import pytest

from growth_orchestrator.application.reconcile_publication import reconcile_publication
from publishing_gateway.publication_registry import PublicationRegistry


def _reserve_dispatched(registry: PublicationRegistry, *, status: str = "GATEWAY_ACCEPTED") -> str:
    reserved = registry.reserve(
        {
            "publication_id": "pub-facebook-1",
            "content_package_id": "pkg-1",
            "idempotency_key": "idem-1",
            "platform": "facebook",
        }
    )
    registry.update(reserved["publication_id"], status=status, gateway_status=status, approved_by="harry")
    return reserved["publication_id"]


def test_reconcile_unknown_publication_raises(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    with pytest.raises(KeyError):
        reconcile_publication("nope", platform_post_id="123", reconciled_by="harry", registry=registry)


def test_reconcile_requires_dispatched_status(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_dispatched(registry, status="PENDING_APPROVAL")
    with pytest.raises(ValueError):
        reconcile_publication(publication_id, platform_post_id="123", reconciled_by="harry", registry=registry)


def test_reconcile_requires_platform_post_id(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_dispatched(registry)
    with pytest.raises(ValueError):
        reconcile_publication(publication_id, platform_post_id="", reconciled_by="harry", registry=registry)


def test_reconcile_records_post_id_and_moves_to_published(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_dispatched(registry)

    result = reconcile_publication(
        publication_id,
        platform_post_id="fb-post-999",
        permalink="https://facebook.com/venhohotel/posts/999",
        reconciled_by="harry",
        registry=registry,
    )

    assert result["status"] == "PUBLISHED"
    assert result["platform_post_id"] == "fb-post-999"
    assert result["permalink"] == "https://facebook.com/venhohotel/posts/999"
    assert result["reconciled_by"] == "harry"


def test_reconcile_verified_gateway_error_without_retrying_webhook(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_dispatched(registry, status="GATEWAY_ERROR")
    registry.update(
        publication_id,
        gateway_error="Make.com reported PUBLISHED without a valid platform_post_id",
    )

    result = reconcile_publication(
        publication_id,
        platform_post_id="fb-post-verified",
        permalink="https://facebook.com/venhohotelhanoi/posts/verified",
        reconciled_by="harry",
        registry=registry,
    )

    assert result["status"] == "PUBLISHED"
    assert result["platform_post_id"] == "fb-post-verified"


def test_reconcile_then_measure_unblocks_analytics(tmp_path: Path) -> None:
    """End-to-end proof this closes the real dead-end: before reconciliation
    M08 can't observe anything; after, it can."""
    from growth_orchestrator.bridges.m08_analytics_bridge import M08AnalyticsBridge

    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_dispatched(registry)
    bridge = M08AnalyticsBridge(data_root=tmp_path, registry=registry, questions_root=tmp_path / "questions")

    before = bridge.observe(publication_id)
    assert before["status"] == "pending_observation"

    reconcile_publication(publication_id, platform_post_id="fb-post-1", reconciled_by="harry", registry=registry)

    after = bridge.observe(publication_id)
    assert after["status"] == "observed"
