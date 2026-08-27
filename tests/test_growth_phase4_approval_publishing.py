from __future__ import annotations

import hashlib
import hmac
import json
import time
from pathlib import Path

import pytest

from automation_studio.approval_snapshot import assert_dispatch_allowed, build_final_review_state, create_approval_snapshot
from publishing_gateway.adapters.make_gateway import MakeGatewayAdapter
from publishing_gateway.callback_receiver import apply_callback, parse_callback
from publishing_gateway.publication_registry import PublicationRegistry
from publishing_gateway.reconciliation import apply_reconciliation


SECRET = "callback-secret"


def _package() -> dict:
    return {
        "id": "pkg-p4-001",
        "copy_version_ids": ["copy-v1"],
        "asset_version_ids": ["asset-v1"],
        "validation_snapshot_id": "validation-v1",
        "fact_version_ids": ["fact-v1"],
        "brief_version_id": "brief-v1",
    }


def _sign(body: bytes, timestamp: int) -> str:
    return hmac.new(SECRET.encode("utf-8"), f"{timestamp}.".encode("utf-8") + body, hashlib.sha256).hexdigest()


def test_exact_version_approval_blocks_dispatch_after_edit() -> None:
    package = _package()
    snapshot = create_approval_snapshot(package, approved_by="harry")

    assert_dispatch_allowed(snapshot, package)

    edited = {**package, "copy_version_ids": ["copy-v2"]}
    with pytest.raises(ValueError, match="copy_version_changed"):
        assert_dispatch_allowed(snapshot, edited)

    state = build_final_review_state(edited, snapshot)
    assert state["status"] == "BLOCKED"
    assert state["reason"] == "copy_version_changed"


def test_make_acceptance_is_gateway_accepted_not_published(tmp_path: Path) -> None:
    registry = PublicationRegistry(data_root=tmp_path)
    command = {
        "publication_id": "pub-p4-001",
        "content_package_id": "pkg-p4-001",
        "idempotency_key": "idem-p4-001",
        "platform": "facebook",
    }
    reserved = registry.reserve(command)
    response = MakeGatewayAdapter(enabled=True).send(command)
    updated = registry.update(reserved["publication_id"], gateway_status=response["status"], status=response["status"])

    assert response["status"] == "GATEWAY_ACCEPTED"
    assert response["published"] is False
    assert updated["status"] == "GATEWAY_ACCEPTED"
    with pytest.raises(ValueError, match="lacks post id"):
        registry.ensure_publishable_evidence("pub-p4-001")


def test_callback_requires_signature_and_supplies_post_id(tmp_path: Path) -> None:
    registry = PublicationRegistry(data_root=tmp_path)
    registry.reserve(
        {
            "publication_id": "pub-p4-002",
            "content_package_id": "pkg-p4-001",
            "idempotency_key": "idem-p4-002",
            "platform": "instagram",
        }
    )
    timestamp = int(time.time())
    body = json.dumps(
        {
            "publication_id": "pub-p4-002",
            "idempotency_key": "idem-p4-002",
            "platform": "instagram",
            "status": "PUBLISHED",
            "platform_post_id": "ig-123",
            "permalink": "https://example.test/ig-123",
            "published_at": "2026-08-03T08:00:00Z",
        }
    ).encode("utf-8")

    payload = parse_callback(body, signature=_sign(body, timestamp), secret=SECRET, timestamp=timestamp)
    updated = apply_callback(payload, registry=registry)

    assert updated["status"] == "PUBLISHED"
    assert registry.ensure_publishable_evidence("pub-p4-002")["platform_post_id"] == "ig-123"

    with pytest.raises(ValueError, match="invalid callback signature"):
        parse_callback(body, signature="bad", secret=SECRET, timestamp=timestamp)


def test_reconciliation_proof_can_close_unknown_publication(tmp_path: Path) -> None:
    registry = PublicationRegistry(data_root=tmp_path)
    publication = registry.reserve(
        {
            "publication_id": "pub-p4-003",
            "content_package_id": "pkg-p4-001",
            "idempotency_key": "idem-p4-003",
            "platform": "facebook",
        }
    )
    publication = registry.update(publication["publication_id"], status="UNKNOWN")

    updated = apply_reconciliation(
        publication,
        {"platform_post_id": "fb-777", "permalink": "https://example.test/fb-777", "reconciliation_proof": "operator-confirmed:fb-777"},
        registry=registry,
    )

    assert updated["status"] == "PUBLISHED"
    assert updated["reconciliation_proof"] == "operator-confirmed:fb-777"
    assert registry.ensure_publishable_evidence("pub-p4-003")["reconciliation_proof"]


def test_duplicate_chaos_reserves_one_publication(tmp_path: Path) -> None:
    registry = PublicationRegistry(data_root=tmp_path)
    command = {
        "publication_id": "pub-p4-dupe",
        "content_package_id": "pkg-p4-001",
        "idempotency_key": "same-key",
        "platform": "facebook",
    }

    results = [registry.reserve({**command, "publication_id": f"pub-p4-dupe-{index}"}) for index in range(10)]
    stored = registry.load()["publications"]

    assert len(stored) == 1
    assert sum(1 for result in results if result.get("duplicate")) == 9


def test_slot_platform_can_have_only_one_active_publication(tmp_path: Path) -> None:
    registry = PublicationRegistry(data_root=tmp_path)
    first = registry.reserve({
        "publication_id": "slot-fb-a", "content_package_id": "pkg-a",
        "idempotency_key": "idem-a", "platform": "facebook", "slot_id": "slot-2026-08-31-monday",
    })
    registry.update(first["publication_id"], status="PENDING_APPROVAL")

    duplicate = registry.reserve({
        "publication_id": "slot-fb-b", "content_package_id": "pkg-b",
        "idempotency_key": "idem-b", "platform": "facebook", "slot_id": "slot-2026-08-31-monday",
    })

    assert duplicate["duplicate"] is True
    assert duplicate["duplicate_reason"] == "slot_platform"
    assert len(registry.load()["publications"]) == 1

    registry.update(first["publication_id"], status="REJECTED")
    replacement = registry.reserve({
        "publication_id": "slot-fb-replacement", "content_package_id": "pkg-r",
        "idempotency_key": "idem-r", "platform": "facebook", "slot_id": "slot-2026-08-31-monday",
    })
    assert replacement.get("duplicate") is None
