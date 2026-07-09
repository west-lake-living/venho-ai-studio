from pathlib import Path

from prompt_studio.builders.video_prompt_builder import build_video_prompt
from prompt_studio.knowledge_reader import KnowledgeDna, read_dna
from prompt_studio.schemas.base import ForbiddenItem, RequiredDnaItem

LINH_AN_DNA = Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_LINH_AN_DNA.json")
LAKE_VIEW_ROOM_DNA = Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json")
BRIEF = "A 15-second video of Linh An standing at the lake view room window at golden hour."


def _build():
    character = read_dna(LINH_AN_DNA)
    environment = read_dna(LAKE_VIEW_ROOM_DNA)
    contract = build_video_prompt(
        [environment],
        BRIEF,
        brief_slug="window-15s",
        character_dna=character,
        generated_at="2026-07-08T00:00:00+00:00",
    )
    return character, environment, contract


def test_build_video_prompt_merges_character_and_environment_dna():
    character, environment, contract = _build()

    assert contract.prompt_type == "video"
    assert contract.prompt_id == "linh_an+lake_view_room__video__window-15s"
    assert len(contract.source_knowledge) == 2
    assert contract.source_knowledge[0].file == LINH_AN_DNA.name
    assert contract.source_knowledge[1].file == LAKE_VIEW_ROOM_DNA.name

    assert contract.character_lock is not None
    assert {item.key for item in contract.character_lock} == {item.key for item in character.required_dna}

    assert contract.environment_dna is not None
    assert {item.key for item in contract.environment_dna} == {item.key for item in environment.required_dna}

    # required_dna (used generically by Validate #2) is the union of both
    assert len(contract.required_dna) == len(character.required_dna) + len(environment.required_dna)


def test_forbidden_is_deduped_union_and_drives_negative_prompt():
    character, environment, contract = _build()

    expected_rule_texts = {item.rule for item in character.forbidden} | {item.rule for item in environment.forbidden}
    assert {item.rule for item in contract.forbidden} == expected_rule_texts
    for rule in expected_rule_texts:
        assert rule in contract.negative_prompt


def test_final_prompt_contains_every_required_dna_value():
    _character, _environment, contract = _build()
    for item in contract.required_dna:
        assert item.value in contract.final_prompt
    assert "Character lock" in contract.final_prompt
    assert "Environment" in contract.final_prompt
    assert "Consistency rules" in contract.final_prompt


def test_build_video_prompt_is_deterministic_across_two_runs():
    _c1, _e1, first = _build()
    _c2, _e2, second = _build()
    assert first.model_dump() == second.model_dump()


def test_build_video_prompt_without_character_dna_is_environment_only():
    environment = read_dna(LAKE_VIEW_ROOM_DNA)
    contract = build_video_prompt(
        [environment], "An empty lake view room at sunrise.", brief_slug="empty-room", generated_at="2026-07-08T00:00:00+00:00"
    )
    assert contract.character_lock is None
    assert contract.prompt_id == "lake_view_room__video__empty-room"
    assert len(contract.source_knowledge) == 1


def test_key_collision_between_character_and_environment_is_noted_not_dropped():
    character = KnowledgeDna(
        path=Path("fake_character.json"),
        project="venho_hotel",
        subject="fake_character",
        dna_version="1.0",
        contract_version="1.1",
        content_hash="aaaa",
        required_dna=[RequiredDnaItem(key="lighting", value="soft warm key light on face")],
        forbidden=[ForbiddenItem(rule="no harsh shadows on face", source="curated")],
    )
    environment = KnowledgeDna(
        path=Path("fake_environment.json"),
        project="venho_hotel",
        subject="fake_room",
        dna_version="1.0",
        contract_version="1.1",
        content_hash="bbbb",
        required_dna=[RequiredDnaItem(key="lighting", value="natural daylight through window")],
        forbidden=[ForbiddenItem(rule="no neon lighting", source="curated")],
    )

    contract = build_video_prompt(
        [environment], "Test brief.", brief_slug="collision-test", character_dna=character,
        generated_at="2026-07-08T00:00:00+00:00",
    )

    assert contract.character_lock == [RequiredDnaItem(key="lighting", value="soft warm key light on face")]
    assert contract.environment_dna == [RequiredDnaItem(key="lighting", value="natural daylight through window")]
    assert any("lighting" in note and "both character and environment" in note for note in contract.notes)
    assert any("lighting" in rule for rule in contract.consistency_rules)
