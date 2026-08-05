from __future__ import annotations

from pathlib import Path

import pytest

from growth_orchestrator.application.approve_and_dispatch import (
    approve_and_dispatch,
    edit_publication,
    list_pending,
    reject_publication,
    retry_dispatch,
)
from growth_orchestrator.bridges.m07_publishing_bridge import M07PublishingBridge
from growth_orchestrator.domain.publishing_slot import PublishingSlot
from publishing_gateway.adapters.make_gateway import MakeGatewayAdapter
from publishing_gateway.adapters.zalo_oa import ZaloOAAdapter
from publishing_gateway.publication_registry import PublicationRegistry
from shared.jobs.slot_store import SlotStore


def _reserve_pending(registry: PublicationRegistry, *, platform: str = "facebook", slot_id: str | None = None) -> str:
    reserved = registry.reserve(
        {
            "publication_id": f"pub-{platform}-1",
            "content_package_id": "pkg-1",
            "idempotency_key": f"idem-{platform}-1",
            "platform": platform,
        }
    )
    registry.update(reserved["publication_id"], status="PENDING_APPROVAL", content={"text": "hello"}, slot_id=slot_id)
    return reserved["publication_id"]


def test_list_pending_returns_pending_approval_rows_only(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    pending_id = _reserve_pending(registry)
    other = registry.reserve(
        {"publication_id": "pub-2", "content_package_id": "pkg-2", "idempotency_key": "idem-2", "platform": "facebook"}
    )
    registry.update(other["publication_id"], status="PUBLISHED")

    pending = list_pending(project="venho_hotel", data_root=tmp_path, registry=registry)

    assert [item["publication_id"] for item in pending] == [pending_id]


def test_list_pending_also_surfaces_gateway_error_rows_so_they_are_never_invisible(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    pending_id = _reserve_pending(registry, platform="facebook")
    stranded = registry.reserve(
        {"publication_id": "pub-stranded", "content_package_id": "pkg-2", "idempotency_key": "idem-2", "platform": "instagram"}
    )
    registry.update(stranded["publication_id"], status="GATEWAY_ERROR", gateway_error="timeout")
    other = registry.reserve(
        {"publication_id": "pub-published", "content_package_id": "pkg-3", "idempotency_key": "idem-3", "platform": "threads"}
    )
    registry.update(other["publication_id"], status="PUBLISHED")

    pending = list_pending(project="venho_hotel", data_root=tmp_path, registry=registry)

    assert {item["publication_id"] for item in pending} == {pending_id, "pub-stranded"}
    stranded_row = next(item for item in pending if item["publication_id"] == "pub-stranded")
    assert stranded_row["status"] == "GATEWAY_ERROR"


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


def test_approve_and_dispatch_blocks_real_dispatch_when_referenced_fact_expired_since_queueing(tmp_path: Path) -> None:
    """PB-005 pre-flight (DoD #15): a fact that expired in the days between
    daily_cycle queueing the draft and Harry clicking Duyệt must never let
    the since-unsupported claim reach the real Make.com webhook."""
    from knowledge_studio.facts.fact_store import FactStore

    FactStore("venho_hotel", data_root=tmp_path).save(
        {
            "fact_key": "promo.expired_deal",
            "value": "Giảm 20% cuối tuần",
            "status": "approved",
            "valid_from": "2020-01-01T00:00:00+00:00",
            "valid_to": "2020-01-31T00:00:00+00:00",  # long expired
        },
        overwrite=True,
    )

    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)
    registry.update(
        publication_id,
        creative_brief={"id": "brief-x", "visual": {}},
        claims=[{"text": "Giảm 20% cuối tuần", "fact_key": "promo.expired_deal"}],
        scene_summary={},
    )

    calls = []
    make_adapter = MakeGatewayAdapter(enabled=True)
    make_adapter.send = lambda command: calls.append(command) or {"status": "GATEWAY_ACCEPTED", "published": False}
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=ZaloOAAdapter(enabled=True))

    result = approve_and_dispatch(
        publication_id, approved_by="harry", project="venho_hotel", data_root=tmp_path, registry=registry, bridge=bridge
    )

    assert calls == []  # the real webhook was never called
    assert result["status"] == "NEEDS_REVISION"
    assert result["preflight_report"]["claim_report"]["kill_switches"] == ["unsupported_critical_claim"]
    # dropped out of the approval queue, same as a failed edit_publication would
    assert list_pending(project="venho_hotel", data_root=tmp_path, registry=registry) == []


def test_approve_and_dispatch_still_dispatches_when_claims_are_absent_or_valid(tmp_path: Path) -> None:
    """Rows without a persisted creative_brief (pre-2026-08-05 convention)
    skip the check gracefully instead of blocking every legacy row."""
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)  # no creative_brief/claims set

    calls = []
    make_adapter = MakeGatewayAdapter(enabled=True)
    make_adapter.send = lambda command: calls.append(command) or {"status": "GATEWAY_ACCEPTED", "published": False}
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=ZaloOAAdapter(enabled=True))

    result = approve_and_dispatch(
        publication_id, approved_by="harry", project="venho_hotel", data_root=tmp_path, registry=registry, bridge=bridge
    )

    assert len(calls) == 1
    assert result["status"] == "GATEWAY_ACCEPTED"


def test_approve_and_dispatch_advances_slot_to_dispatched_on_success(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    slot_store = SlotStore(db_path=tmp_path / "growth.db")
    slot_store.ensure_slots([PublishingSlot(slot_id="slot-2026-08-10-monday", slot_date="2026-08-10", slot_type="regular", lane="regular")])
    slot_store.transition("slot-2026-08-10-monday", "DRAFT_ASSIGNED")
    slot_store.transition("slot-2026-08-10-monday", "PENDING_APPROVAL", content_package_id="pkg-1")
    publication_id = _reserve_pending(registry, slot_id="slot-2026-08-10-monday")

    make_adapter = MakeGatewayAdapter(enabled=True)
    make_adapter.send = lambda command: {"status": "GATEWAY_ACCEPTED", "published": False}
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=ZaloOAAdapter(enabled=True))

    approve_and_dispatch(
        publication_id, approved_by="harry", project="venho_hotel", data_root=tmp_path,
        registry=registry, bridge=bridge, slot_store=slot_store,
    )

    assert slot_store.get("slot-2026-08-10-monday").status == "DISPATCHED"


def test_approve_and_dispatch_slot_bookkeeping_failure_never_blocks_a_real_dispatch(tmp_path: Path) -> None:
    """slot_id points at a slot that doesn't exist (or slot_store is broken)
    -- the real approval/dispatch must still succeed."""
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    slot_store = SlotStore(db_path=tmp_path / "growth.db")
    publication_id = _reserve_pending(registry, slot_id="slot-does-not-exist")

    make_adapter = MakeGatewayAdapter(enabled=True)
    make_adapter.send = lambda command: {"status": "GATEWAY_ACCEPTED", "published": False}
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=ZaloOAAdapter(enabled=True))

    result = approve_and_dispatch(
        publication_id, approved_by="harry", project="venho_hotel", data_root=tmp_path,
        registry=registry, bridge=bridge, slot_store=slot_store,
    )

    assert result["status"] == "GATEWAY_ACCEPTED"


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


def _reserve_pending_with_dna_subject(registry: PublicationRegistry, *, platform: str = "facebook") -> str:
    reserved = registry.reserve(
        {
            "publication_id": f"pub-edit-{platform}-1",
            "content_package_id": "pkg-edit-1",
            "idempotency_key": f"idem-edit-{platform}-1",
            "platform": platform,
        }
    )
    registry.update(
        reserved["publication_id"],
        status="PENDING_APPROVAL",
        content={"text": "old draft text", "hashtags": []},
        dna_subject="westlake",
    )
    return reserved["publication_id"]


# Real content_validator rubric rewards warm, specific, Vietnamese, on-brand
# copy with a soft CTA -- mirrors what a real gpt-5.5 draft would produce.
_GOOD_EDIT_TEXT = (
    "Một buổi sáng chậm rãi bên Hồ Tây, sương còn vương trên mặt nước, Ven Hồ Hotel "
    "đón bạn với không gian ấm áp và chân thật ngay giữa lòng Hà Nội. Đây là nơi bạn "
    "có thể ngồi lặng nhìn hồ, thưởng một tách cà phê, và cảm nhận nhịp sống Tây Hồ "
    "không vội vã. Nhắn tin cho chúng tôi để kiểm tra phòng trống nhé."
)
_BAD_EDIT_TEXT = "spam spam spam"


def test_edit_publication_good_text_re_enters_pending_approval(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending_with_dna_subject(registry)

    result = edit_publication(
        publication_id, edited_by="harry", new_text=_GOOD_EDIT_TEXT, data_root=tmp_path, registry=registry
    )

    assert result["status"] == "PENDING_APPROVAL"
    assert result["content"]["text"] == _GOOD_EDIT_TEXT
    assert result["edited_by"] == "harry"
    assert result["edit_validation"]["content_report"]["verdict"] == "approve"
    # Row has no persisted creative_brief (predates 2026-08-05) -- claim/
    # alignment re-check is skipped, not silently treated as passing.
    assert result["edit_validation"]["claim_alignment_skipped"] is True


def test_edit_publication_passes_when_persisted_claims_are_fact_backed(tmp_path: Path) -> None:
    from knowledge_studio.facts.fact_store import FactStore

    FactStore(project="venho_hotel", data_root=tmp_path).save(
        {"fact_key": "hotel.room_count", "value": 12, "value_type": "integer", "source_type": "owner_confirmed",
         "confidence": 1.0, "status": "approved", "version": 1, "valid_from": "2026-01-01T00:00:00+07:00", "valid_to": None}
    )
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending_with_dna_subject(registry)
    registry.update(
        publication_id,
        creative_brief={"visual": {"required_entities": [], "forbidden_entities": []}},
        claims=[{"text": "Khách sạn có 12 phòng", "fact_key": "hotel.room_count"}],
        scene_summary={"entities": []},
    )

    result = edit_publication(
        publication_id, edited_by="harry", new_text=_GOOD_EDIT_TEXT, data_root=tmp_path, registry=registry
    )

    assert result["edit_validation"]["claim_report"]["kill_switches"] == []
    assert result["edit_validation"]["alignment_report"]["kill_switches"] == []
    assert result["status"] == "PENDING_APPROVAL"


def test_edit_publication_reruns_claim_alignment_when_brief_is_persisted(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending_with_dna_subject(registry)
    registry.update(
        publication_id,
        creative_brief={"visual": {"required_entities": [], "forbidden_entities": []}},
        claims=[{"text": "Khách sạn có 12 phòng", "fact_key": "room_count"}],
        scene_summary={"entities": []},
    )

    result = edit_publication(
        publication_id, edited_by="harry", new_text=_GOOD_EDIT_TEXT, data_root=tmp_path, registry=registry
    )

    assert "claim_alignment_skipped" not in result["edit_validation"]
    assert result["edit_validation"]["claim_report"]["kill_switches"] == ["unsupported_critical_claim"]
    # The persisted claim has a fact_key pointing at a fact that doesn't
    # exist in this test's (empty) fact store -- ClaimValidator correctly
    # kill-switches it, and that must still block re-entering the queue
    # even though the content-quality rubric alone would have passed.
    assert result["status"] == "NEEDS_REVISION"


def test_edit_publication_bad_text_lands_on_needs_revision_and_drops_from_pending(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending_with_dna_subject(registry)

    result = edit_publication(
        publication_id, edited_by="harry", new_text=_BAD_EDIT_TEXT, data_root=tmp_path, registry=registry
    )

    assert result["status"] == "NEEDS_REVISION"
    assert list_pending(project="venho_hotel", data_root=tmp_path, registry=registry) == []


def test_edit_publication_clears_prior_approval_snapshot(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending_with_dna_subject(registry)
    registry.update(
        publication_id,
        status="GATEWAY_ERROR",
        approved_by="harry",
        gateway_status="GATEWAY_ERROR",
        approval_snapshot={"status": "approved", "approved_by": "harry"},
    )

    result = edit_publication(
        publication_id, edited_by="harry", new_text=_GOOD_EDIT_TEXT, data_root=tmp_path, registry=registry
    )

    assert result["approval_snapshot"] is None
    assert result["approved_by"] is None
    assert result["gateway_status"] is None


def test_edit_publication_rejects_dispatched_status(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending_with_dna_subject(registry)
    registry.update(publication_id, status="GATEWAY_ACCEPTED")

    with pytest.raises(ValueError):
        edit_publication(publication_id, edited_by="harry", new_text=_GOOD_EDIT_TEXT, data_root=tmp_path, registry=registry)


def test_edit_publication_without_dna_subject_fails_closed_to_needs_revision(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)  # no dna_subject set

    with pytest.raises(ValueError, match="dna_subject"):
        edit_publication(publication_id, edited_by="harry", new_text=_GOOD_EDIT_TEXT, data_root=tmp_path, registry=registry)

    assert registry.find(publication_id)["status"] == "NEEDS_REVISION"
