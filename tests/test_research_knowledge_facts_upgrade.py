from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from research_engine.application import run_research_cycle as cycle
from shared.storage.proposed_fact_store import EXPIRED, PENDING, ProposedFactStore


def _proposal(id_: str, value: str, domain: str = "local_intel") -> dict:
    return {"id": id_, "domain": domain, "fact_key": f"{domain}.{id_}", "value": value, "rationale": "r", "source_uri": f"https://s/{id_}"}


def test_pending_proposals_expire_after_21_days_and_stay_as_tombstones(tmp_path: Path) -> None:
    store = ProposedFactStore(data_root=tmp_path)
    store.merge_new([_proposal("old", "Chợ Hoa Quảng Bá (236 Âu Cơ)"), _proposal("new", "Capella (27 Tô Ngọc Vân)")])
    items = store.load()
    items[0]["proposed_at"] = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    store._save(items)

    assert store.expire_stale() == 1
    by_id = {i["id"]: i for i in store.load()}
    assert by_id["old"]["status"] == EXPIRED and by_id["new"]["status"] == PENDING
    # The same finding next week is still refused.
    assert store.merge_new([_proposal("old", "Chợ Hoa Quảng Bá (236 Âu Cơ)")]) == 0


def test_weekly_all_cycle_skips_unscheduled_domains(tmp_path: Path, monkeypatch) -> None:
    config_root = tmp_path / "research"
    config_root.mkdir()
    (config_root / "research_questions.yaml").write_text(
        yaml.safe_dump({"version": 1, "domains": {
            "local_intel": {"question": "q?", "collector": "tavily", "queries": ["a"]},
            "brand_visual": {"question": "q?", "collector": "tavily", "queries": ["a"], "scheduled": False},
        }}),
        encoding="utf-8",
    )
    ran: list[str] = []
    monkeypatch.setattr(cycle, "run_research_cycle", lambda domain, **_: ran.append(domain) or cycle.ResearchCycleResult(domain=domain, question="q?"))

    results = cycle.run_all_research_cycles(config_root=config_root)

    assert ran == ["local_intel"]
    assert any(r.domain == "brand_visual" and "scheduled: false" in (r.skipped_reason or "") for r in results)


def test_query_pool_rotates_by_week() -> None:
    config = {"query_pool": ["q0", "q1", "q2", "q3", "q4"], "queries_per_run": 2}
    week_a = cycle._queries_for_this_run(config, today=date(2026, 10, 22))
    week_b = cycle._queries_for_this_run(config, today=date(2026, 10, 29))
    assert len(week_a) == 2 and week_a != week_b
    assert cycle._queries_for_this_run({"queries": ["fixed"]}) == ["fixed"]


def test_local_intel_drops_places_already_known_or_repeated(tmp_path: Path) -> None:
    store = ProposedFactStore(data_root=tmp_path)
    store.merge_new([_proposal("known", "Capella Coffee Roaster (27 Tô Ngọc Vân)")])
    kept = cycle._drop_known_places(
        [
            _proposal("a", "Capella Coffee Roaster (27 Tô Ngọc Vân, Tây Hồ)"),  # already in the store
            _proposal("b", "Tiệm bánh Mây (12 Quảng An)"),
            _proposal("c", "Tiệm bánh Mây (12 Quảng An, Tây Hồ)"),  # same place twice in one run
        ],
        store=store, project="venho_hotel", data_root=tmp_path, today=date(2026, 10, 22),
    )
    assert [p["id"] for p in kept] == ["b"]


def test_extraction_hint_reaches_the_extractor(tmp_path: Path) -> None:
    config_root = tmp_path / "research"
    config_root.mkdir()
    (config_root / "research_questions.yaml").write_text(
        yaml.safe_dump({"version": 1, "domains": {"local_intel": {
            "question": "Quán nào?", "collector": "manual", "extraction_hint": "value dạng Tên (địa chỉ)",
        }}}, allow_unicode=True),
        encoding="utf-8",
    )
    source = tmp_path / "export.md"
    source.write_text("Tiệm bánh Mây ở 12 Quảng An", encoding="utf-8")
    seen: list[str] = []

    def fake_extract(*, question, **_):
        seen.append(question)
        return []

    cycle.run_research_cycle(
        "local_intel", config_root=config_root, vault_root=tmp_path / "vault", data_root=tmp_path,
        input_file=source, extract_fn=fake_extract, gemini_api_key="k",
    )
    assert seen and "value dạng Tên (địa chỉ)" in seen[0]


def test_local_intel_reads_pages_one_at_a_time_and_caps_the_queue(tmp_path: Path) -> None:
    config_root = tmp_path / "research"
    config_root.mkdir()
    (config_root / "research_questions.yaml").write_text(
        yaml.safe_dump({"version": 1, "domains": {"local_intel": {
            "question": "Quán nào?", "collector": "manual", "per_source": True, "max_proposals": 2,
        }}}, allow_unicode=True),
        encoding="utf-8",
    )
    source = tmp_path / "export.md"
    source.write_text("x", encoding="utf-8")
    calls: list[bool] = []

    def fake_extract(*, per_source, **_):
        calls.append(per_source)
        names = ["Capella", "Tiệm Mây", "Bánh Cuốn Thanh Vân", "Chè Bốn Mùa", "Kem Tràng Tiền"]
        return [
            {"fact_key": f"local_intel.p{i}", "value": f"{name} ({i} Quảng An)", "value_type": "string", "rationale": "r", "source_index": 0, "source_uri": "u", "source_title": "t"}
            for i, name in enumerate(names)
        ]

    result = cycle.run_research_cycle(
        "local_intel", config_root=config_root, vault_root=tmp_path / "vault", data_root=tmp_path,
        input_file=source, extract_fn=fake_extract, gemini_api_key="k",
    )
    assert calls == [True]
    assert result.proposals_created == 2


def test_same_place_under_two_names_is_one_place() -> None:
    from growth_orchestrator.application.local_intel import place_key, same_place

    a = place_key({"value": "Skyon9 Rooftop West Lake (Tây Hồ)"})
    b = place_key({"value": "SkyOn9 Rooftop Bar & Restaurant (134 Từ Hoa)"})
    c = place_key({"value": "Phở Tráng Tay - Phở Gà (424 Lạc Long Quân)"})
    d = place_key({"value": "Bún bò Huế O Huông (Lạc Long Quân)"})
    assert same_place(a, b)
    assert not same_place(c, d)
    assert not same_place(a, c)
