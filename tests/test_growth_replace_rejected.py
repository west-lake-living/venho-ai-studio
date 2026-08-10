from datetime import date

import growth_orchestrator.application.replace_rejected as replacement_module
from growth_orchestrator.application.daily_cycle import DailyCycleResult
from growth_orchestrator.application.replace_rejected import replace_rejected_publication
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
