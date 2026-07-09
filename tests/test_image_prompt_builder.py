from pathlib import Path

from prompt_studio.builders.image_prompt_builder import build_image_prompt
from prompt_studio.knowledge_reader import read_dna

REAL_DNA = Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json")
BRIEF = "Create a realistic booking-style image of the lake view room."


def _build():
    dna = read_dna(REAL_DNA)
    return build_image_prompt(dna, BRIEF, brief_slug="booking-style", generated_at="2026-07-08T00:00:00+00:00")


def test_build_image_prompt_produces_valid_contract_from_real_dna():
    contract = _build()
    assert contract.prompt_type == "image"
    assert contract.prompt_id == "lake_view_room__image__booking-style"
    assert contract.project == "venho_hotel"
    assert contract.target_language == "en"
    assert contract.optimizer.used is False
    assert contract.validation.structural == "pending"


def test_required_dna_filled_from_every_invariant():
    dna = read_dna(REAL_DNA)
    contract = _build()
    assert len(contract.required_dna) == len(dna.required_dna)
    keys = {item.key for item in contract.required_dna}
    assert {item.key for item in dna.required_dna} == keys


def test_forbidden_maps_into_negative_prompt():
    dna = read_dna(REAL_DNA)
    contract = _build()
    assert contract.forbidden == dna.forbidden
    for item in dna.forbidden:
        assert item.rule in contract.negative_prompt


def test_allowed_imperfections_map_into_authenticity_section_of_final_prompt():
    dna = read_dna(REAL_DNA)
    contract = _build()
    assert "Authenticity" in contract.final_prompt
    for item in dna.allowed_imperfections:
        assert item.value in contract.final_prompt


def test_build_image_prompt_is_deterministic_across_two_runs():
    first = _build()
    second = _build()
    assert first.model_dump() == second.model_dump()
