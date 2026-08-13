"""topic_selector.select_from_candidates: cooldown + least-recently-used
topic selection, replacing the old bare modulo cursor.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from growth_orchestrator.application.topic_selector import select_from_candidates


def _write_publications(data_root: Path, project: str, publications: list[dict]) -> None:
    path = data_root / project / "publishing" / "publication_registry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"publications": publications}, ensure_ascii=False), encoding="utf-8")


def test_empty_registry_rotates_like_the_old_bare_modulo(tmp_path: Path) -> None:
    """With no posting history, every candidate is fresh -- selection must
    reduce to flat[index % len(flat)], exactly the old behaviour."""
    data_root = tmp_path / "data" / "projects"
    candidates = [{"topic": "A"}, {"topic": "B"}, {"topic": "C"}]

    first = select_from_candidates(candidates, project="venho_hotel", data_root=data_root, rotation_key="lane:test")
    second = select_from_candidates(candidates, project="venho_hotel", data_root=data_root, rotation_key="lane:test")
    third = select_from_candidates(candidates, project="venho_hotel", data_root=data_root, rotation_key="lane:test")
    fourth = select_from_candidates(candidates, project="venho_hotel", data_root=data_root, rotation_key="lane:test")

    assert [first["topic"], second["topic"], third["topic"], fourth["topic"]] == ["A", "B", "C", "A"]


def test_a_topic_posted_recently_is_excluded_until_its_cooldown_elapses(tmp_path: Path) -> None:
    data_root = tmp_path / "data" / "projects"
    today = date(2026, 8, 13)
    _write_publications(
        data_root, "venho_hotel",
        [{"topic": "A", "created_at": (today - timedelta(days=10)).isoformat() + "T09:00:00+00:00"}],
    )
    candidates = [{"topic": "A"}, {"topic": "B"}]

    picked = select_from_candidates(
        candidates, project="venho_hotel", data_root=data_root, rotation_key="lane:test",
        cooldown_days=60, today=today,
    )

    assert picked["topic"] == "B"


def test_a_topic_posted_outside_its_cooldown_is_eligible_again(tmp_path: Path) -> None:
    data_root = tmp_path / "data" / "projects"
    today = date(2026, 8, 13)
    _write_publications(
        data_root, "venho_hotel",
        [{"topic": "A", "created_at": (today - timedelta(days=61)).isoformat() + "T09:00:00+00:00"}],
    )
    candidates = [{"topic": "A"}]

    picked = select_from_candidates(
        candidates, project="venho_hotel", data_root=data_root, rotation_key="lane:test",
        cooldown_days=60, today=today,
    )

    assert picked["topic"] == "A"


def test_every_candidate_in_cooldown_falls_back_to_least_recently_used(tmp_path: Path) -> None:
    """A slot must never go unfilled for lack of a "fresh enough" topic
    (Harry's 2026-08-13 call) -- the oldest-used candidate wins instead of
    raising or leaving the lane empty."""
    data_root = tmp_path / "data" / "projects"
    today = date(2026, 8, 13)
    _write_publications(
        data_root, "venho_hotel",
        [
            {"topic": "A", "created_at": (today - timedelta(days=5)).isoformat() + "T09:00:00+00:00"},
            {"topic": "B", "created_at": (today - timedelta(days=40)).isoformat() + "T09:00:00+00:00"},
        ],
    )
    candidates = [{"topic": "A"}, {"topic": "B"}]

    picked = select_from_candidates(
        candidates, project="venho_hotel", data_root=data_root, rotation_key="lane:test",
        cooldown_days=60, today=today,
    )

    assert picked["topic"] == "B"  # used 40 days ago, further back than A's 5


def test_research_backed_defaults_to_false_when_not_supplied(tmp_path: Path) -> None:
    data_root = tmp_path / "data" / "projects"
    picked = select_from_candidates(
        [{"topic": "A"}], project="venho_hotel", data_root=data_root, rotation_key="lane:test",
    )
    assert picked["research_backed"] is False


def test_research_backed_true_is_preserved(tmp_path: Path) -> None:
    data_root = tmp_path / "data" / "projects"
    picked = select_from_candidates(
        [{"topic": "A", "research_backed": True}], project="venho_hotel", data_root=data_root, rotation_key="lane:test",
    )
    assert picked["research_backed"] is True


def test_no_candidates_raises_instead_of_silently_returning_nothing(tmp_path: Path) -> None:
    data_root = tmp_path / "data" / "projects"
    with pytest.raises(ValueError, match="lane:test"):
        select_from_candidates([], project="venho_hotel", data_root=data_root, rotation_key="lane:test")
