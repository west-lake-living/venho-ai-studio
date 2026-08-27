from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import pytest

from growth_orchestrator.application.approve_and_dispatch import (
    approve_and_dispatch,
    approve_publications,
    approve_week,
    edit_publication,
    expire_stale_approvals,
    list_pending,
    reject_publication,
    retry_dispatch,
)
from growth_orchestrator.application.scheduled_dispatch import dispatch_due, scheduled_at_for
from growth_orchestrator.bridges.m07_publishing_bridge import M07PublishingBridge
from growth_orchestrator.domain.publishing_slot import PublishingSlot
from publishing_gateway.adapters.make_gateway import MakeGatewayAdapter
from publishing_gateway.adapters.zalo_oa import ZaloOAAdapter
from controlled_rollout.rollout_state_store import RolloutStateStore
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


def _past_shadow(tmp_path: Path) -> None:
    """Move the rollout stage off `shadow` for tests about the dispatch path
    itself. `_dispatch_claimed` withholds the webhook while the stage is
    shadow (the real default), so without this every dispatch assertion below
    would be asserting the gate rather than the behaviour it names.
    """
    RolloutStateStore("venho_hotel", tmp_path).record_decision(
        {"current_stage": "shadow", "next_stage": "pilot_25", "allowed": True}
    )


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


def test_expire_stale_approvals_retires_only_past_unreviewed_slots(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    overdue = _reserve_pending(registry, platform="facebook", slot_id="slot-2026-08-17-monday")
    future = registry.reserve(
        {"publication_id": "pub-future", "content_package_id": "pkg-future", "idempotency_key": "idem-future", "platform": "instagram"}
    )
    registry.update(future["publication_id"], status="PENDING_APPROVAL", slot_id="slot-2026-08-29-saturday")
    unslotted = registry.reserve(
        {"publication_id": "pub-unslotted", "content_package_id": "pkg-unslotted", "idempotency_key": "idem-unslotted", "platform": "threads"}
    )
    registry.update(unslotted["publication_id"], status="PENDING_APPROVAL")

    expired = expire_stale_approvals(project="venho_hotel", data_root=tmp_path, registry=registry, today=date(2026, 8, 27))

    assert [item["publication_id"] for item in expired] == [overdue]
    stale = registry.find(overdue)
    assert stale["status"] == "STALE_APPROVAL"
    assert stale["stale_reason"] == "Approval window closed on 2026-08-17."
    assert registry.find(future["publication_id"])["status"] == "PENDING_APPROVAL"
    assert registry.find(unslotted["publication_id"])["status"] == "PENDING_APPROVAL"


def test_expire_stale_approvals_uses_ict_date_by_default(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    overdue = _reserve_pending(registry, platform="facebook", slot_id="slot-2020-01-01-wednesday")

    expired = expire_stale_approvals(project="venho_hotel", data_root=tmp_path, registry=registry)

    assert [item["publication_id"] for item in expired] == [overdue]


def test_approve_and_dispatch_calls_bridge_and_updates_status(tmp_path: Path) -> None:
    _past_shadow(tmp_path)
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
    _past_shadow(tmp_path)
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
    _past_shadow(tmp_path)
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


def test_slot_reaches_completed_only_when_the_platform_confirmed_the_post(tmp_path: Path) -> None:
    """A Make scenario that answers with a real platform_post_id closes the
    slot; a bare GATEWAY_ACCEPTED leaves it at DISPATCHED. Before this,
    COMPLETED had no caller at all, so the cadence table could not tell a
    post Facebook accepted from one that died inside the scenario."""
    _past_shadow(tmp_path)
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    slot_store = SlotStore(db_path=tmp_path / "growth.db")
    slot_store.ensure_slots([PublishingSlot(slot_id="slot-2026-08-10-monday", slot_date="2026-08-10", slot_type="regular", lane="regular")])
    slot_store.transition("slot-2026-08-10-monday", "DRAFT_ASSIGNED")
    slot_store.transition("slot-2026-08-10-monday", "PENDING_APPROVAL", content_package_id="pkg-1")
    publication_id = _reserve_pending(registry, slot_id="slot-2026-08-10-monday")

    make_adapter = MakeGatewayAdapter(enabled=True)
    make_adapter.send = lambda command: {"status": "PUBLISHED", "published": True, "platform_post_id": "1122334455"}
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=ZaloOAAdapter(enabled=True))

    result = approve_and_dispatch(
        publication_id, approved_by="harry", project="venho_hotel", data_root=tmp_path,
        registry=registry, bridge=bridge, slot_store=slot_store,
    )

    assert result["platform_post_id"] == "1122334455"
    assert slot_store.get("slot-2026-08-10-monday").status == "COMPLETED"


def test_approve_and_dispatch_slot_bookkeeping_failure_never_blocks_a_real_dispatch(tmp_path: Path) -> None:
    """slot_id points at a slot that doesn't exist (or slot_store is broken)
    -- the real approval/dispatch must still succeed."""
    _past_shadow(tmp_path)
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


def test_approve_week_records_one_scheduled_approval_without_dispatch(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    monday = _reserve_pending_with_snapshot(registry, platform="facebook")
    friday = registry.reserve(
        {"publication_id": "pub-instagram-snap-1", "content_package_id": "pkg-snap-2", "idempotency_key": "idem-instagram-snap-1", "platform": "instagram"}
    )
    registry.update(
        friday["publication_id"],
        status="PENDING_APPROVAL",
        slot_id="slot-2026-08-14-friday",
        package_snapshot={"id": "pkg-snap-2", "copy_version_ids": ["copy-v2"], "asset_version_ids": [], "validation_snapshot_id": "val-def", "fact_version_ids": [], "brief_version_id": "brief-2@1"},
    )
    registry.update(monday, slot_id="slot-2026-08-10-monday")
    next_week = _reserve_pending(registry, platform="threads", slot_id="slot-2026-08-17-monday")

    approved = approve_week(
        approved_by="harry@example.com",
        week_start=date(2026, 8, 10),
        data_root=tmp_path,
        registry=registry,
    )

    assert {item["publication_id"] for item in approved} == {monday, friday["publication_id"], next_week}
    for item in approved:
        assert item["status"] == "APPROVED_SCHEDULED"
        assert item["approval_scope"] == "weekly_schedule"
        assert item["approved_by"] == "harry@example.com"
        if item["approval_snapshot"] is not None:
            assert item["approval_snapshot"]["status"] == "approved"
    assert registry.find(next_week)["status"] == "APPROVED_SCHEDULED"


def test_list_pending_exposes_the_real_calendar_date_not_just_the_weekday(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    _reserve_pending(registry, platform="facebook", slot_id="slot-2026-08-12-wednesday")
    _reserve_pending(registry, platform="instagram", slot_id="slot-2026-08-19-wednesday")

    rows = {row["publication_id"]: row["slot_date"] for row in list_pending(project="venho_hotel", data_root=tmp_path, registry=registry)}

    assert rows == {"pub-facebook-1": "2026-08-12", "pub-instagram-1": "2026-08-19"}


def test_approve_publications_approves_only_the_given_topic_group(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    fb = _reserve_pending(registry, platform="facebook", slot_id="slot-2026-08-12-wednesday")
    other_topic = _reserve_pending(registry, platform="instagram", slot_id="slot-2026-08-12-wednesday")

    approved = approve_publications(publication_ids=[fb], approved_by="harry@example.com", data_root=tmp_path, registry=registry)

    assert {item["publication_id"] for item in approved} == {fb}
    assert approved[0]["status"] == "APPROVED_SCHEDULED"
    assert approved[0]["approval_scope"] == "topic_group"
    assert registry.find(other_topic)["status"] == "PENDING_APPROVAL"


def test_approve_publications_rejects_unknown_publication_id(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    with pytest.raises(KeyError):
        approve_publications(publication_ids=["does-not-exist"], approved_by="harry", data_root=tmp_path, registry=registry)


def test_approve_publications_is_atomic_across_the_group(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    fb = _reserve_pending(registry, platform="facebook", slot_id="slot-2026-08-12-wednesday")
    ig = _reserve_pending(registry, platform="instagram", slot_id="slot-2026-08-12-wednesday")
    registry.update(ig, status="REJECTED")

    with pytest.raises(ValueError, match="not PENDING_APPROVAL"):
        approve_publications(publication_ids=[fb, ig], approved_by="harry", data_root=tmp_path, registry=registry)
    assert registry.find(fb)["status"] == "PENDING_APPROVAL"


def test_independent_scheduler_dispatches_only_approved_posts_at_their_due_slot(tmp_path: Path) -> None:
    _past_shadow(tmp_path)
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    due = _reserve_pending(registry, platform="facebook", slot_id="slot-2026-08-10-monday")
    future = _reserve_pending(registry, platform="instagram", slot_id="slot-2026-08-12-wednesday")
    registry.update(due, status="APPROVED_SCHEDULED", approved_by="harry")
    registry.update(future, status="APPROVED_SCHEDULED", approved_by="harry")

    calls = []
    make_adapter = MakeGatewayAdapter(enabled=True)
    make_adapter.send = lambda command: calls.append(command) or {"status": "GATEWAY_ACCEPTED", "published": False}
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=ZaloOAAdapter(enabled=True))

    results = dispatch_due(
        project="venho_hotel",
        data_root=tmp_path,
        registry=registry,
        bridge=bridge,
        now=datetime(2026, 8, 10, 9, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")),
    )

    assert [result["publication_id"] for result in results] == [due]
    assert registry.find(due)["status"] == "GATEWAY_ACCEPTED"
    assert registry.find(future)["status"] == "APPROVED_SCHEDULED"
    assert [call["publication_id"] for call in calls] == [due]


def test_independent_scheduler_uses_the_policy_timezone_and_publish_time() -> None:
    scheduled = scheduled_at_for(
        {"slot_id": "slot-2026-08-10-monday"},
        cadence_policy={"timezone": "Asia/Ho_Chi_Minh", "publish_time": "09:00"},
    )
    assert scheduled == datetime(2026, 8, 10, 9, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))


def test_independent_scheduler_does_not_dispatch_an_expired_slot(tmp_path: Path) -> None:
    _past_shadow(tmp_path)
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry, platform="facebook", slot_id="slot-2026-08-10-monday")
    registry.update(publication_id, status="APPROVED_SCHEDULED", approved_by="harry")

    calls = []
    make_adapter = MakeGatewayAdapter(enabled=True)
    make_adapter.send = lambda command: calls.append(command) or {"status": "GATEWAY_ACCEPTED", "published": False}
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=ZaloOAAdapter(enabled=True))

    results = dispatch_due(
        project="venho_hotel",
        data_root=tmp_path,
        registry=registry,
        bridge=bridge,
        now=datetime(2026, 8, 10, 9, 31, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")),
    )

    assert results[0]["gateway_status"] == "MISSED_DISPATCH_WINDOW"
    assert registry.find(publication_id)["status"] == "GATEWAY_ERROR"
    assert calls == []


def test_manual_catch_up_dispatches_only_an_expired_slot_from_today(tmp_path: Path) -> None:
    _past_shadow(tmp_path)
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    today = _reserve_pending(registry, platform="facebook", slot_id="slot-2026-08-10-monday")
    old = _reserve_pending(registry, platform="instagram", slot_id="slot-2026-08-08-saturday")
    registry.update(today, status="APPROVED_SCHEDULED", approved_by="harry")
    registry.update(old, status="APPROVED_SCHEDULED", approved_by="harry")

    calls = []
    make_adapter = MakeGatewayAdapter(enabled=True)
    make_adapter.send = lambda command: calls.append(command) or {"status": "GATEWAY_ACCEPTED", "published": False}
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=ZaloOAAdapter(enabled=True))

    results = dispatch_due(
        project="venho_hotel",
        data_root=tmp_path,
        registry=registry,
        bridge=bridge,
        now=datetime(2026, 8, 10, 19, 45, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")),
        catch_up_today=True,
    )

    assert registry.find(today)["status"] == "GATEWAY_ACCEPTED"
    assert registry.find(old)["gateway_status"] == "MISSED_DISPATCH_WINDOW"
    assert [call["publication_id"] for call in calls] == [today]
    assert {item["publication_id"] for item in results} == {today, old}


def test_manual_catch_up_retries_today_after_scheduler_marked_missed_window(tmp_path: Path) -> None:
    _past_shadow(tmp_path)
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(
        registry, platform="facebook", slot_id="slot-2026-08-12-wednesday"
    )
    registry.update(
        publication_id,
        status="GATEWAY_ERROR",
        gateway_status="MISSED_DISPATCH_WINDOW",
        gateway_error="GitHub runner started late",
        approved_by="harry",
    )

    calls = []
    make_adapter = MakeGatewayAdapter(enabled=True)
    make_adapter.send = lambda command: calls.append(command) or {
        "status": "GATEWAY_ACCEPTED",
        "published": False,
    }
    bridge = M07PublishingBridge(
        make_adapter=make_adapter, zalo_adapter=ZaloOAAdapter(enabled=True)
    )

    results = dispatch_due(
        project="venho_hotel",
        data_root=tmp_path,
        registry=registry,
        bridge=bridge,
        now=datetime(2026, 8, 12, 10, 52, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")),
        catch_up_today=True,
    )

    assert [item["publication_id"] for item in results] == [publication_id]
    assert registry.find(publication_id)["status"] == "GATEWAY_ACCEPTED"
    assert [call["publication_id"] for call in calls] == [publication_id]


def test_approve_week_is_atomic_when_a_row_changes_during_review(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    first = _reserve_pending(registry, platform="facebook", slot_id="slot-2026-08-10-monday")
    second = _reserve_pending(registry, platform="instagram", slot_id="slot-2026-08-12-wednesday")
    original_update_many = registry.update_many_if_status

    def changed_after_read(updates):
        registry.update(second, status="REJECTED")
        return original_update_many(updates)

    registry.update_many_if_status = changed_after_read  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="not PENDING_APPROVAL"):
        approve_week(approved_by="harry", week_start=date(2026, 8, 10), data_root=tmp_path, registry=registry)
    assert registry.find(first)["status"] == "PENDING_APPROVAL"


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
    _past_shadow(tmp_path)
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
    _past_shadow(tmp_path)
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


def _bridge_recording(sent: list) -> M07PublishingBridge:
    make_adapter = MakeGatewayAdapter(enabled=True)
    make_adapter.send = lambda command: (sent.append(command), {"status": "GATEWAY_ACCEPTED", "published": False})[1]
    return M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=ZaloOAAdapter(enabled=True))


def test_shadow_stage_withholds_the_webhook_entirely(tmp_path: Path) -> None:
    """Rollout stage `shadow` must be enforced in code, not just documented.

    Until 2026-08-06 the stage was a governance record only: the sole thing
    stopping a shadow-stage agent from posting to the real Facebook page was
    an unset MAKE_GROWTH_WEBHOOK_URL. Approval is still recorded here -- only
    the outbound call is withheld.
    """
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)
    sent: list = []

    result = approve_and_dispatch(
        publication_id, approved_by="harry", data_root=tmp_path, registry=registry, bridge=_bridge_recording(sent),
    )

    assert sent == []
    assert result["status"] == "SHADOW_HELD"
    assert result["rollout_stage"] == "shadow"
    assert result["approved_by"] == "harry"


def test_shadow_held_row_is_not_returned_to_the_approval_queue(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)
    approve_and_dispatch(
        publication_id, approved_by="harry", data_root=tmp_path, registry=registry, bridge=_bridge_recording([]),
    )

    pending = list_pending(project="venho_hotel", data_root=tmp_path, registry=registry)

    assert pending == []


def test_allow_shadow_publishes_and_records_who_overrode(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)
    sent: list = []

    result = approve_and_dispatch(
        publication_id, approved_by="harry", data_root=tmp_path, registry=registry,
        bridge=_bridge_recording(sent), allow_shadow=True,
    )

    assert len(sent) == 1
    assert result["status"] == "GATEWAY_ACCEPTED"
    assert result["shadow_override_by"] == "harry"


def test_shadow_held_row_is_released_by_retry_once_the_stage_advances(tmp_path: Path) -> None:
    """A held row keeps its approval, so releasing it is a dispatch retry --
    Harry does not re-review content he already approved."""
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)
    approve_and_dispatch(
        publication_id, approved_by="harry", data_root=tmp_path, registry=registry, bridge=_bridge_recording([]),
    )
    _past_shadow(tmp_path)
    sent: list = []

    result = retry_dispatch(publication_id, data_root=tmp_path, registry=registry, bridge=_bridge_recording(sent))

    assert len(sent) == 1
    assert result["status"] == "GATEWAY_ACCEPTED"


def test_unreadable_rollout_state_fails_closed(tmp_path: Path) -> None:
    """Corrupt rollout state must hold the post, never publish it."""
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)
    state_path = tmp_path / "venho_hotel" / "rollout" / "rollout_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("{not json", encoding="utf-8")
    sent: list = []

    result = approve_and_dispatch(
        publication_id, approved_by="harry", data_root=tmp_path, registry=registry, bridge=_bridge_recording(sent),
    )

    assert sent == []
    assert result["status"] == "SHADOW_HELD"


def test_registry_records_the_real_post_id_when_make_answers_with_one(tmp_path: Path) -> None:
    _past_shadow(tmp_path)
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry)

    make_adapter = MakeGatewayAdapter(enabled=True)
    make_adapter.send = lambda command: {
        "status": "PUBLISHED",
        "published": True,
        "platform_post_id": "1122",
        "permalink": "https://facebook.com/p/1122",
    }
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=ZaloOAAdapter(enabled=True))

    result = approve_and_dispatch(
        publication_id, approved_by="harry", project="venho_hotel", data_root=tmp_path, registry=registry, bridge=bridge
    )

    assert result["status"] == "PUBLISHED"
    assert result["platform_post_id"] == "1122"
    assert result["permalink"] == "https://facebook.com/p/1122"


def test_platform_rejection_lands_on_gateway_error_not_a_false_accept(tmp_path: Path) -> None:
    """The 2026-08-06 incident in registry terms: Make returns HTTP 200, the
    platform refuses the post. The row must read GATEWAY_ERROR with the reason
    and stay actionable, instead of looking published."""
    _past_shadow(tmp_path)
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    publication_id = _reserve_pending(registry, platform="instagram")

    make_adapter = MakeGatewayAdapter(enabled=True)
    make_adapter.send = lambda command: {
        "status": "GATEWAY_ERROR",
        "published": False,
        "error": "(36003) The aspect ratio is not supported.",
    }
    bridge = M07PublishingBridge(make_adapter=make_adapter, zalo_adapter=ZaloOAAdapter(enabled=True))

    result = approve_and_dispatch(
        publication_id, approved_by="harry", project="venho_hotel", data_root=tmp_path, registry=registry, bridge=bridge
    )

    assert result["status"] == "GATEWAY_ERROR"
    assert "36003" in result["gateway_error"]
    assert [row["publication_id"] for row in list_pending(project="venho_hotel", data_root=tmp_path, registry=registry)] == [publication_id]
