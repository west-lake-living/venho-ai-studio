from datetime import date, timedelta

import growth_orchestrator.application.replace_rejected as replacement_module
from growth_orchestrator.application.daily_cycle import DailyCycleResult
from growth_orchestrator.application.replace_rejected import replace_rejected_publication
from growth_orchestrator.application.replace_rejected import ReplacementBatchError, replace_due_rejections
from publishing_gateway.publication_registry import PublicationRegistry


def test_rejected_publication_gets_fresh_pending_replacement(tmp_path, monkeypatch) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    old = registry.reserve({
        "publication_id": "old", "content_package_id": "old-pkg",
        "idempotency_key": "old-idem", "platform": "facebook",
    })
    registry.update(old["publication_id"], status="REJECTED", slot_id=f"slot-{date.today().isoformat()}-monday")

    def fake_cycle(day, **kwargs):
        new = registry.reserve({
            "publication_id": "new", "content_package_id": "new-pkg",
            "idempotency_key": "new-idem", "platform": kwargs["platforms"][0],
        })
        registry.update(new["publication_id"], status="PENDING_APPROVAL", slot_id=kwargs["slot_date"])
        return DailyCycleResult(day=day, topic={"topic": "new topic"}, publications=[registry.find("new")])

    monkeypatch.setattr(replacement_module, "run_daily_cycle", fake_cycle)
    replacement = replace_rejected_publication("old", data_root=tmp_path, registry=registry)

    assert replacement["publication_id"] == "new"
    assert replacement["status"] == "PENDING_APPROVAL"
    assert replacement["replaces_publication_id"] == "old"
    assert registry.find("old")["replacement_publication_id"] == "new"


def test_replace_due_rejections_continues_after_one_candidate_fails(tmp_path, monkeypatch) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    for publication_id, platform in (("bad", "facebook"), ("good", "instagram")):
        row = registry.reserve({
            "publication_id": publication_id,
            "content_package_id": f"{publication_id}-pkg",
            "idempotency_key": f"{publication_id}-idem",
            "platform": platform,
        })
        registry.update(
            row["publication_id"],
            status="REJECTED",
            slot_id=f"slot-{date.today().isoformat()}-monday",
        )

    calls = []

    def fake_replace(publication_id, **kwargs):
        calls.append(publication_id)
        if publication_id == "bad":
            raise RuntimeError("validator rejected")
        return {"publication_id": "replacement-good", "status": "PENDING_APPROVAL"}

    monkeypatch.setattr(replacement_module, "replace_rejected_publication", fake_replace)

    try:
        replace_due_rejections(data_root=tmp_path)
    except ReplacementBatchError as exc:
        assert [row["publication_id"] for row in exc.publications] == ["replacement-good"]
        assert exc.failures == [{
            "publication_id": "bad",
            "group_publication_ids": ["bad"],
            "error": "validator rejected",
        }]
    else:
        raise AssertionError("expected ReplacementBatchError")

    assert calls == ["bad", "good"]


def test_replace_due_rejections_creates_one_replacement_per_slot_platform(tmp_path, monkeypatch) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    for publication_id in ("duplicate-a", "duplicate-b"):
        row = registry.reserve({
            "publication_id": publication_id,
            "content_package_id": f"{publication_id}-pkg",
            "idempotency_key": f"{publication_id}-idem",
            "platform": "facebook",
        })
        registry.update(
            row["publication_id"],
            status="REJECTED",
            slot_id=f"slot-{date.today().isoformat()}-monday",
        )

    calls = []

    def fake_replace(publication_id, **kwargs):
        calls.append(publication_id)
        return {"publication_id": "one-replacement", "status": "PENDING_APPROVAL"}

    monkeypatch.setattr(replacement_module, "replace_rejected_publication", fake_replace)

    result = replace_due_rejections(data_root=tmp_path)

    assert calls == ["duplicate-a"]
    assert result == [{"publication_id": "one-replacement", "status": "PENDING_APPROVAL"}]
    assert registry.find("duplicate-b")["replacement_publication_id"] == "one-replacement"


def test_stale_approval_is_replaced_in_the_nearest_future_open_slot(tmp_path, monkeypatch) -> None:
    today = date(2026, 8, 27)
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    old = registry.reserve({
        "publication_id": "stale", "content_package_id": "stale-pkg",
        "idempotency_key": "stale-idem", "platform": "facebook",
    })
    registry.update(old["publication_id"], status="STALE_APPROVAL", slot_id="slot-2026-08-24-monday")

    calls = []

    def fake_cycle(day, **kwargs):
        calls.append((day, kwargs["slot_date"]))
        new = registry.reserve({
            "publication_id": "future", "content_package_id": "future-pkg",
            "idempotency_key": "future-idem", "platform": kwargs["platforms"][0],
        })
        registry.update(new["publication_id"], status="PENDING_APPROVAL", slot_id=f"slot-{kwargs['slot_date']}-{day}")
        return DailyCycleResult(day=day, topic={"topic": "replacement"}, publications=[registry.find("future")])

    monkeypatch.setattr(replacement_module, "run_daily_cycle", fake_cycle)
    result = replacement_module.replace_due_rejections(data_root=tmp_path, today=today)

    assert result[0]["publication_id"] == "future"
    assert calls == [("friday", (today + timedelta(days=1)).isoformat())]
    assert registry.find("stale")["replacement_publication_id"] == "future"
