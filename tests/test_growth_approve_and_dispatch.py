from __future__ import annotations

from pathlib import Path

import pytest

from growth_orchestrator.application.approve_and_dispatch import (
    approve_and_dispatch,
    list_pending,
    reject_publication,
    retry_dispatch,
)
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


def test_approve_and_dispatch_second_concurrent_call_cannot_double_dispatch(tmp_path: Path) -> None:
    """Regression test for the check-then-act race: once the first caller's
    registry.claim() flips status off PENDING_APPROVAL, a second caller racing
    on the same publication_id must fail fast instead of also firing the
    webhook."""
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)

    calls = []
    make_adapter = MakeGatewayAdapter(enabled=True)
    make_adapter.send = lambda command: calls.append(command) or {"status": "GATEWAY_ACCEPTED", "published": False}
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=ZaloOAAdapter(enabled=True))

    # Simulate the first caller claiming the row (as approve_and_dispatch does
    # internally) before the second caller's approve_and_dispatch runs.
    registry.claim(publication_id, expected_status="PENDING_APPROVAL", claimed_status="DISPATCHING")

    with pytest.raises(ValueError, match="not PENDING_APPROVAL"):
        approve_and_dispatch(
            publication_id, approved_by="harry", data_root=tmp_path, registry=registry, bridge=bridge
        )
    assert calls == []


def test_dispatch_failure_lands_on_gateway_error_not_stuck_dispatching(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)

    make_adapter = MakeGatewayAdapter(enabled=True)

    def _boom(command):
        raise RuntimeError("webhook timed out")

    make_adapter.send = _boom
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=ZaloOAAdapter(enabled=True))

    result = approve_and_dispatch(
        publication_id, approved_by="harry", data_root=tmp_path, registry=registry, bridge=bridge
    )

    assert result["status"] == "GATEWAY_ERROR"
    assert "webhook timed out" in result["gateway_error"]


def test_retry_dispatch_recovers_a_gateway_error_row(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)
    registry.update(publication_id, status="GATEWAY_ERROR", approved_by="harry")

    make_adapter = MakeGatewayAdapter(enabled=True)
    make_adapter.send = lambda command: {"status": "GATEWAY_ACCEPTED", "published": False}
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=ZaloOAAdapter(enabled=True))

    result = retry_dispatch(publication_id, data_root=tmp_path, registry=registry, bridge=bridge)

    assert result["status"] == "GATEWAY_ACCEPTED"
    assert result["approved_by"] == "harry"  # original approval preserved, not re-collected


def test_retry_dispatch_rejects_non_gateway_error_status(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)

    with pytest.raises(ValueError, match="not GATEWAY_ERROR"):
        retry_dispatch(publication_id, data_root=tmp_path, registry=registry)


def test_reject_publication_marks_rejected_and_drops_from_pending(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)

    result = reject_publication(
        publication_id, rejected_by="harry", reason="sai chủ đề", data_root=tmp_path, registry=registry
    )

    assert result["status"] == "REJECTED"
    assert result["rejected_by"] == "harry"
    assert result["rejected_reason"] == "sai chủ đề"
    assert list_pending(project="venho_hotel", data_root=tmp_path, registry=registry) == []


def test_reject_publication_rejects_non_pending_status(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)
    registry.update(publication_id, status="PUBLISHED")

    with pytest.raises(ValueError, match="not PENDING_APPROVAL"):
        reject_publication(publication_id, rejected_by="harry", data_root=tmp_path, registry=registry)


def test_registry_claim_is_atomic_test_and_set(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)

    claimed = registry.claim(publication_id, expected_status="PENDING_APPROVAL", claimed_status="DISPATCHING")
    assert claimed["status"] == "DISPATCHING"

    with pytest.raises(ValueError, match="not PENDING_APPROVAL"):
        registry.claim(publication_id, expected_status="PENDING_APPROVAL", claimed_status="DISPATCHING")


def test_registry_claim_unknown_publication_raises_keyerror(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    with pytest.raises(KeyError):
        registry.claim("nope", expected_status="PENDING_APPROVAL", claimed_status="DISPATCHING")
