"""growth_orchestrator.application.local_intel: approved research facts ->
Wednesday's local_discovery topic candidates.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from growth_orchestrator.application.local_intel import (
    approved_local_facts,
    clean_rationale,
    local_intel_topic_entries,
    place_key,
    recently_covered_places,
    text_mentions_place,
)


def _write_facts(data_root: Path, project: str, facts: list[dict]) -> None:
    path = data_root / project / "research" / "proposed_facts.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(facts, ensure_ascii=False), encoding="utf-8")


def _fact(fact_key: str, value: str, *, domain: str, status: str) -> dict:
    return {
        "id": f"fact-{fact_key}",
        "fact_key": fact_key,
        "value": value,
        "domain": domain,
        "status": status,
        "rationale": f"{fact_key} = {value}",
    }


def test_only_approved_facts_are_returned(tmp_path: Path) -> None:
    data_root = tmp_path / "data" / "projects"
    _write_facts(
        data_root, "venho_hotel",
        [
            _fact("cafe.a", "Cafe A", domain="local_intel", status="approved"),
            _fact("cafe.b", "Cafe B", domain="local_intel", status="pending_approval"),
            _fact("cafe.c", "Cafe C", domain="local_intel", status="rejected"),
        ],
    )

    facts = approved_local_facts(
        "venho_hotel", data_root, domains=["local_intel"], slot_date=date(2026, 8, 13)
    )

    assert [f["fact_key"] for f in facts] == ["cafe.a"]


def test_domains_outside_the_requested_list_are_excluded(tmp_path: Path) -> None:
    data_root = tmp_path / "data" / "projects"
    _write_facts(
        data_root, "venho_hotel",
        [
            _fact("cafe.a", "Cafe A", domain="local_intel", status="approved"),
            _fact("price.a", "500k", domain="market_pricing", status="approved"),
        ],
    )

    facts = approved_local_facts(
        "venho_hotel", data_root, domains=["local_intel"], slot_date=date(2026, 8, 13)
    )

    assert [f["fact_key"] for f in facts] == ["cafe.a"]


def test_an_event_past_its_end_date_is_excluded(tmp_path: Path) -> None:
    data_root = tmp_path / "data" / "projects"
    _write_facts(
        data_root, "venho_hotel",
        [
            _fact("event.old", "01/01/2026 - 05/01/2026", domain="local_events", status="approved"),
            _fact("event.future", "01/09/2026 - 30/09/2026", domain="local_events", status="approved"),
        ],
    )

    facts = approved_local_facts(
        "venho_hotel", data_root, domains=["local_events"], slot_date=date(2026, 8, 13)
    )

    assert [f["fact_key"] for f in facts] == ["event.future"]


def test_a_single_date_event_still_running_today_is_included(tmp_path: Path) -> None:
    data_root = tmp_path / "data" / "projects"
    _write_facts(
        data_root, "venho_hotel",
        [_fact("event.today", "13/08/2026", domain="local_events", status="approved")],
    )

    facts = approved_local_facts(
        "venho_hotel", data_root, domains=["local_events"], slot_date=date(2026, 8, 13)
    )

    assert [f["fact_key"] for f in facts] == ["event.today"]


def test_a_place_fact_without_a_date_never_expires(tmp_path: Path) -> None:
    data_root = tmp_path / "data" / "projects"
    _write_facts(
        data_root, "venho_hotel",
        [_fact("cafe.a", "Cafe A, 12 X Street", domain="local_intel", status="approved")],
    )

    facts = approved_local_facts(
        "venho_hotel", data_root, domains=["local_intel"], slot_date=date(2030, 1, 1)
    )

    assert [f["fact_key"] for f in facts] == ["cafe.a"]


def test_a_missing_fact_store_returns_no_facts_instead_of_raising(tmp_path: Path) -> None:
    data_root = tmp_path / "data" / "projects"  # never written
    facts = approved_local_facts(
        "venho_hotel", data_root, domains=["local_intel"], slot_date=date(2026, 8, 13)
    )
    assert facts == []


def test_topic_entries_carry_proof_points_matching_the_creative_brief_schema(tmp_path: Path) -> None:
    """contracts/creative_brief.schema.json requires proof_points items to
    have "text" and "fact_key" -- exactly the shape this must produce."""
    data_root = tmp_path / "data" / "projects"
    _write_facts(
        data_root, "venho_hotel",
        [_fact("cafe.a", "Cafe A", domain="local_intel", status="approved")],
    )

    entries = local_intel_topic_entries(
        "venho_hotel", data_root, domains=["local_intel"], pillar="Local Discovery", slot_date=date(2026, 8, 13)
    )

    assert len(entries) == 1
    entry = entries[0]
    assert entry["pillar"] == "Local Discovery"
    assert entry["research_backed"] is True
    assert entry["topic"]
    assert entry["topic"] == "Cafe A"  # the place name, not the extractor rationale
    assert entry["proof_points"] == [{"text": "Cafe.a = Cafe A", "fact_key": "cafe.a"}]
    assert "dna_subject" not in entry  # scenario picks the subject, not the topic


def test_topic_is_place_name_and_source_index_is_stripped(tmp_path: Path) -> None:
    """2026-10-21: Dashboard showed topics like "Nguồn 3 giới thiệu Chợ Hoa
    Quảng Bá tại 236 ..." -- extractor provenance leaking into the post."""
    data_root = tmp_path / "data" / "projects"
    fact = _fact("attraction.cho_hoa_quang_ba", "Chợ Hoa Quảng Bá (236 Đường Âu Cơ, Quảng An, Tây Hồ)", domain="local_intel", status="approved")
    fact["rationale"] = "Nguồn 3 giới thiệu Chợ Hoa Quảng Bá tại 236 Đường Âu Cơ là chợ hoa lớn."
    _write_facts(data_root, "venho_hotel", [fact])

    entry = local_intel_topic_entries("venho_hotel", data_root, domains=["local_intel"], pillar="P", slot_date=date(2026, 10, 21))[0]

    assert entry["topic"] == "Chợ Hoa Quảng Bá (236 Đường Âu Cơ, Quảng An, Tây Hồ)"
    assert entry["proof_points"][0]["text"] == "Chợ Hoa Quảng Bá tại 236 Đường Âu Cơ là chợ hoa lớn."
    assert clean_rationale("Nguồn 0 đề xuất ABC Coffee Roasters là quán.") == "ABC Coffee Roasters là quán."


def test_place_key_matches_old_rationale_topics_and_curated_lines() -> None:
    key = place_key({"value": "Chợ Hoa Quảng Bá (236 Đường Âu Cơ)"})
    assert key == ("cho", "hoa", "quang", "ba")
    assert text_mentions_place("Nguồn 3 giới thiệu Chợ Hoa Quảng Bá tại 236 Đường Âu Cơ", key)
    assert text_mentions_place("cho hoa Quang Ba luc tinh mo", key)
    assert not text_mentions_place("mot ngoi chua co canh Ho Tay", key)


def test_place_published_or_rejected_within_90_days_is_covered() -> None:
    quang_ba = ("cho", "hoa", "quang", "ba")
    kim_lien = ("chua", "kim", "lien")
    treebee = ("treebee", "coffee")
    publications = [
        {"topic": "Nguồn 3 giới thiệu Chợ Hoa Quảng Bá tại 236", "status": "PUBLISHED", "created_at": "2026-09-13T17:00:00+00:00"},
        {"topic": "Nguồn 1 đề xuất Treebee coffee tại 171 Vệ Hồ", "status": "REJECTED", "created_at": "2026-10-07T06:55:00+00:00"},
        {"topic": "Nguồn 3 nêu Chùa Kim Liên tại Nghi Tàm", "status": "PUBLISHED", "created_at": "2026-05-01T00:00:00+00:00"},
    ]

    covered = recently_covered_places([quang_ba, kim_lien, treebee], publications, today=date(2026, 10, 21))

    assert covered == {quang_ba, treebee}  # Kim Liên's only post is older than 90 days
