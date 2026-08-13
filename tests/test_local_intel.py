"""growth_orchestrator.application.local_intel: approved research facts ->
Wednesday's local_discovery topic candidates.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from growth_orchestrator.application.local_intel import approved_local_facts, local_intel_topic_entries


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
    assert entry["proof_points"] == [{"text": entry["topic"], "fact_key": "cafe.a"}]
    assert "dna_subject" not in entry  # scenario picks the subject, not the topic
