from __future__ import annotations

from pathlib import Path

import pytest

from growth_orchestrator.application.approve_and_dispatch import approve_and_dispatch, list_pending
from growth_orchestrator.bridges.m07_publishing_bridge import M07PublishingBridge
from publishing_gateway.adapters.make_gateway import MakeGatewayAdapter
from publishing_gateway.adapters.zalo_oa import ZaloOAAdapter
from publishing_gateway.publication_registry import PublicationRegistry


def _reserve_pending(registry: PublicationRegistry, *, platform: str = "facebook") -> str:
    reserved = registry.reserve(
        {
            "publication_id": f"pub-{platform}-1",
            "content_package_id": "pkg-1",
            "idempotency_key": f"idem-{platform}-1",
            "platform": platform,
        }
    )
    registry.update(reserved["publication_id"], status="PENDING_APPROVAL", content={"text": "hello"})
    return reserved["publication_id"]


def test_list_pending_only_returns_pending_approval_rows(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    pending_id = _reserve_pending(registry)
    other = registry.reserve(
        {"publication_id": "pub-2", "content_package_id": "pkg-2", "idempotency_key": "idem-2", "platform": "facebook"}
    )
    registry.update(other["publication_id"], status="PUBLISHED")

    pending = list_pending(project="venho_hotel", data_root=tmp_path, registry=registry)

    assert [item["publication_id"] for item in pending] == [pending_id]


def test_approve_and_dispatch_calls_bridge_and_updates_status(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)

    calls = []
    zalo_adapter = ZaloOAAdapter(enabled=True)
    make_adapter = MakeGatewayAdapter(enabled=True)
    make_adapter.send = lambda command: calls.append(command) or {"status": "GATEWAY_ACCEPTED", "published": False}
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=zalo_adapter)

    result = approve_and_dispatch(
        publication_id, approved_by="harry", project="venho_hotel", data_root=tmp_path, registry=registry, bridge=bridge
    )

    assert result["status"] == "GATEWAY_ACCEPTED"
    assert result["approved_by"] == "harry"
    assert calls[0]["platform"] == "facebook"
    assert calls[0]["content"] == {"text": "hello"}
    assert list_pending(project="venho_hotel", data_root=tmp_path, registry=registry) == []


def test_approve_and_dispatch_rejects_unknown_publication(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    with pytest.raises(KeyError):
        approve_and_dispatch("nope", approved_by="harry", data_root=tmp_path, registry=registry)


def test_approve_and_dispatch_rejects_non_pending_status(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)
    registry.update(publication_id, status="PUBLISHED")

    with pytest.raises(ValueError, match="not PENDING_APPROVAL"):
        approve_and_dispatch(publication_id, approved_by="harry", data_root=tmp_path, registry=registry)


def _reserve_pending_with_snapshot(registry: PublicationRegistry, *, platform: str = "facebook") -> str:
    reserved = registry.reserve(
        {
            "publication_id": f"pub-{platform}-snap-1",
            "content_package_id": "pkg-snap-1",
            "idempotency_key": f"idem-{platform}-snap-1",
            "platform": platform,
        }
    )
    registry.update(
        reserved["publication_id"],
        status="PENDING_APPROVAL",
        content={"text": "hello"},
        package_snapshot={
            "id": "pkg-snap-1",
            "copy_version_ids": ["copy-v1"],
            "asset_version_ids": [],
            "validation_snapshot_id": "val-abc",
            "fact_version_ids": [],
            "brief_version_id": "brief-1@1",
        },
    )
    return reserved["publication_id"]


def test_approve_and_dispatch_records_exact_version_approval_snapshot(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending_with_snapshot(registry)

    zalo_adapter = ZaloOAAdapter(enabled=True)
    make_adapter = MakeGatewayAdapter(enabled=True)
    make_adapter.send = lambda command: {"status": "GATEWAY_ACCEPTED", "published": False}
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=zalo_adapter)

    result = approve_and_dispatch(
        publication_id, approved_by="harry", data_root=tmp_path, registry=registry, bridge=bridge
    )

    snapshot = result["approval_snapshot"]
    assert snapshot["status"] == "approved"
    assert snapshot["approved_by"] == "harry"
    assert snapshot["copy_version_ids"] == ["copy-v1"]
    assert snapshot["content_package_id"] == "pkg-snap-1"
    assert snapshot["package_versions_checksum"]


def test_approve_and_dispatch_without_snapshot_still_works(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)

    result = approve_and_dispatch(publication_id, approved_by="harry", data_root=tmp_path, registry=registry)

    assert "approval_snapshot" not in result
