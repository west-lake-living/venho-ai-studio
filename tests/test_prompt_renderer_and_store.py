from pathlib import Path

from prompt_studio.builders.image_prompt_builder import build_image_prompt
from prompt_studio.knowledge_reader import read_dna
from prompt_studio.prompt_renderer import render_markdown
from prompt_studio.prompt_store import save_prompt
from prompt_studio.schemas.image_prompt import ImagePromptContract

REAL_DNA = Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json")
BRIEF = "Create a realistic booking-style image of the lake view room."

FIXED_SECTIONS = [
    "# PROMPT FILE",
    "## META",
    "## TASK BRIEF",
    "## SOURCE KNOWLEDGE",
    "## REQUIRED DNA",
    "## ALLOWED VARIATIONS",
    "## ALLOWED IMPERFECTIONS",
    "## FORBIDDEN / RESTRICTIONS",
    "## FINAL PROMPT",
    "## NEGATIVE PROMPT",
    "## VALIDATION",
    "## NOTES",
]


def _build_contract():
    dna = read_dna(REAL_DNA)
    return build_image_prompt(dna, BRIEF, brief_slug="booking-style", generated_at="2026-07-08T00:00:00+00:00")


def test_render_markdown_has_all_fixed_sections_in_order():
    contract = _build_contract()
    markdown = render_markdown(contract)
    positions = [markdown.index(section) for section in FIXED_SECTIONS]
    assert positions == sorted(positions)


def test_save_prompt_writes_md_and_json_with_brief_slug_in_filename(tmp_path):
    contract = _build_contract()
    paths = save_prompt(contract, root=tmp_path)

    assert paths.markdown.name == "LAKE_VIEW_ROOM__booking-style__IMAGE_PROMPT_v1.0.md"
    assert paths.json.name == "LAKE_VIEW_ROOM__booking-style__IMAGE_PROMPT_v1.0.json"
    assert paths.markdown.exists()
    assert paths.json.exists()
    assert paths.markdown.parent == tmp_path / "venho_hotel" / "prompts" / "image"


def test_json_round_trip_preserves_contract(tmp_path):
    contract = _build_contract()
    paths = save_prompt(contract, root=tmp_path)

    reloaded = ImagePromptContract.model_validate_json(paths.json.read_text(encoding="utf-8"))
    assert reloaded.model_dump() == contract.model_dump()
