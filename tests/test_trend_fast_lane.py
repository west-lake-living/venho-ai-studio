from __future__ import annotations

from datetime import date
from pathlib import Path

from growth_orchestrator.application.daily_cycle import DailyCycleResult
from growth_orchestrator.application.trend_fast_lane import candidate_slot_dates, run_fast_lane
from publishing_gateway.publication_registry import PublicationRegistry
from research_engine.trend_radar.trend_candidate_store import TrendCandidateStore

# Wednesday 2026-10-07; the fireworks are Saturday 10/10.
_TODAY = date(2026, 10, 7)


def _store_with_event(tmp_path: Path, **extra) -> TrendCandidateStore:
    store = TrendCandidateStore(data_root=tmp_path)
    store.merge_new([{
        "id": "event-2026-10-10-abc", "title": "Pháo hoa", "event_name": "Bắn pháo hoa trên Hồ Tây",
        "event_start": "2026-10-10", "event_end": "2026-10-10", "venue": "Hồ Tây", "is_event": True,
        "westlake_area": True, "type": "cultural_event", "status": "needs_human_approval", "fast_lane": True,
        "sources": [{"title": "t", "source_name": "VTV.vn"}], **extra,
    }])
    return store


def _row(registry: PublicationRegistry, publication_id: str, slot_id: str, platform: str, status: str = "PENDING_APPROVAL", **extra) -> None:
    registry.reserve({"publication_id": publication_id, "content_package_id": f"{publication_id}-pkg", "idempotency_key": f"{publication_id}-idem", "platform": platform})
    registry.update(publication_id, status=status, slot_id=slot_id, pillar="Cuoi tuan o Tay Ho", **extra)


def _fake_generate(registry: PublicationRegistry, calls: list[dict], *, fail_platform: str | None = None):
    def generate(day, **kwargs):
        calls.append({"day": day, **kwargs})
        made, errors = [], []
        for platform in kwargs["platforms"]:
            if platform == fail_platform:
                errors.append({"platform": platform, "error": "validator"})
                continue
            pid = f"fast-{platform}"
            registry.reserve({"publication_id": pid, "content_package_id": f"{pid}-pkg", "idempotency_key": f"{pid}-idem", "platform": platform})
            made.append(registry.update(pid, status="PENDING_APPROVAL", slot_id=f"slot-{kwargs['slot_date']}-{day}"))
        return DailyCycleResult(day=day, topic=kwargs["topic_override"], publications=made, errors=errors)
    return generate


def test_slot_dates_run_from_tomorrow_to_the_event_latest_first() -> None:
    event = {"event_start": "2026-10-10", "event_end": "2026-10-10"}
    assert candidate_slot_dates(event, today=_TODAY) == [("2026-10-10", "saturday"), ("2026-10-09", "friday")]
    # Already running: slots until its last day.
    running = {"event_start": "2026-10-01", "event_end": "2026-10-12"}
    assert candidate_slot_dates(running, today=_TODAY)[0] == ("2026-10-12", "monday")


def test_unapproved_events_are_never_drafted(tmp_path: Path) -> None:
    store = _store_with_event(tmp_path)
    calls: list[dict] = []
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    assert run_fast_lane(data_root=tmp_path, today=_TODAY, store=store, registry=registry, generate=_fake_generate(registry, calls)) == []
    assert calls == []


def test_approved_event_replaces_the_curated_drafts_in_the_slot_before_it(tmp_path: Path) -> None:
    store = _store_with_event(tmp_path)
    store.approve("event-2026-10-10-abc", approved_by="harry")
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    _row(registry, "sat-fb", "slot-2026-10-10-saturday", "facebook")
    _row(registry, "sat-ig", "slot-2026-10-10-saturday", "instagram")
    calls: list[dict] = []

    outcomes = run_fast_lane(data_root=tmp_path, today=_TODAY, store=store, registry=registry, generate=_fake_generate(registry, calls))

    assert outcomes[0]["status"] == "drafted" and outcomes[0]["slot_id"] == "slot-2026-10-10-saturday"
    assert calls[0]["topic_override"]["topic"] == "Bắn pháo hoa trên Hồ Tây"
    assert "2026-10-10" in calls[0]["topic_override"]["proof_points"][0]["text"]
    assert registry.find("sat-fb")["status"] == "CANCELLED"
    assert registry.find("sat-fb")["replacement_publication_id"] == "fast-facebook"
    assert registry.find("fast-instagram")["replaces_publication_id"] == "sat-ig"
    assert registry.find("fast-facebook")["status"] == "PENDING_APPROVAL"  # still needs Duyệt
    candidate = store.load()[0]
    assert candidate["fast_lane_status"] == "drafted" and candidate["used_at"]
    # Done once: a second run does nothing.
    assert run_fast_lane(data_root=tmp_path, today=_TODAY, store=store, registry=registry, generate=_fake_generate(registry, calls)) == []


def test_an_approved_slot_is_never_replaced_the_earlier_slot_is_used(tmp_path: Path) -> None:
    store = _store_with_event(tmp_path)
    store.approve("event-2026-10-10-abc", approved_by="harry")
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    _row(registry, "sat-fb", "slot-2026-10-10-saturday", "facebook", status="APPROVED_SCHEDULED")
    calls: list[dict] = []

    outcomes = run_fast_lane(data_root=tmp_path, today=_TODAY, store=store, registry=registry, generate=_fake_generate(registry, calls))

    assert outcomes[0]["slot_id"] == "slot-2026-10-09-friday"
    assert registry.find("sat-fb")["status"] == "APPROVED_SCHEDULED"
    assert calls[0]["platforms"] == ["facebook", "instagram"]  # empty slot: default platforms


def test_research_drafts_are_not_replaced_and_no_slot_is_reported_once(tmp_path: Path) -> None:
    store = _store_with_event(tmp_path)
    store.approve("event-2026-10-10-abc", approved_by="harry")
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    _row(registry, "sat", "slot-2026-10-10-saturday", "facebook", status="SHADOW_HELD")
    _row(registry, "fri", "slot-2026-10-09-friday", "facebook", creative_brief={"proof_points": [{"text": "x", "fact_key": "f"}]})
    calls: list[dict] = []

    first = run_fast_lane(data_root=tmp_path, today=_TODAY, store=store, registry=registry, generate=_fake_generate(registry, calls))
    second = run_fast_lane(data_root=tmp_path, today=_TODAY, store=store, registry=registry, generate=_fake_generate(registry, calls))

    assert first[0]["status"] == "no_free_slot" and first[0]["alert"] is True
    assert second[0]["alert"] is False  # Telegram only once
    assert calls == []
    assert store.load()[0]["fast_lane_status"] == "no_free_slot"


def test_failed_generation_restores_the_curated_drafts(tmp_path: Path) -> None:
    store = _store_with_event(tmp_path)
    store.approve("event-2026-10-10-abc", approved_by="harry")
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    _row(registry, "sat-fb", "slot-2026-10-10-saturday", "facebook")
    _row(registry, "sat-ig", "slot-2026-10-10-saturday", "instagram")
    calls: list[dict] = []

    outcomes = run_fast_lane(
        data_root=tmp_path, today=_TODAY, store=store, registry=registry,
        generate=_fake_generate(registry, calls, fail_platform="instagram"),
    )

    assert outcomes[0]["status"] == "failed"
    assert registry.find("sat-fb")["status"] == "PENDING_APPROVAL"
    assert registry.find("sat-ig")["status"] == "PENDING_APPROVAL"
    assert registry.find("fast-facebook")["status"] == "CANCELLED"
    assert store.load()[0]["fast_lane_status"] == "failed"


def test_saturday_pool_skips_pending_fast_lane_and_ended_events(tmp_path: Path) -> None:
    store = TrendCandidateStore(data_root=tmp_path)
    store.merge_new([
        {"id": "fast", "status": "needs_human_approval", "fast_lane": True, "event_end": "2099-01-01"},
        {"id": "ended", "status": "needs_human_approval", "event_end": "2020-01-01"},
        {"id": "plain", "status": "needs_human_approval"},
        # The fast lane found no free slot: Saturday may still use it.
        {"id": "unplaced", "status": "needs_human_approval", "fast_lane": True, "fast_lane_status": "no_free_slot", "event_end": "2099-01-01"},
    ])
    for cid in ("fast", "ended", "plain", "unplaced"):
        store.approve(cid, approved_by="harry")
    assert [c["id"] for c in store.list_eligible_for_saturday()] == ["plain", "unplaced"]
