from pathlib import Path

from prompt_studio.builders.image_prompt_builder import build_image_prompt
from prompt_studio.knowledge_reader import read_dna
from prompt_studio.prompt_manifest import RegenerationDecision, load_manifest, save_with_manifest

REAL_DNA = Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json")
BRIEF = "Create a realistic booking-style image of the lake view room."


def _build():
    dna = read_dna(REAL_DNA)
    return build_image_prompt(dna, BRIEF, brief_slug="booking-style")


def test_first_save_is_new_and_creates_manifest_entry(tmp_path):
    contract = _build()
    saved_contract, paths, decision = save_with_manifest(contract, root=tmp_path)

    assert decision == RegenerationDecision.NEW
    assert saved_contract.prompt_version == "1.0"
    assert paths is not None and paths.markdown.exists()

    manifest = load_manifest("venho_hotel", root=tmp_path)
    entry = manifest["prompts"][0]
    assert entry["prompt_id"] == "lake_view_room__image__booking-style"
    assert entry["subject"] == "lake_view_room"
    assert entry["brief_slug"] == "booking-style"
    assert entry["current_version"] == "1.0"
    assert entry["template_version"] == "1.0"
    assert entry["status"] == "active"


def test_rebuild_with_unchanged_knowledge_and_template_is_no_change(tmp_path):
    first = _build()
    save_with_manifest(first, root=tmp_path)

    second = _build()  # fresh Build, same DNA + template
    saved_contract, paths, decision = save_with_manifest(second, root=tmp_path)

    assert decision == RegenerationDecision.NO_CHANGE
    assert paths is None
    assert saved_contract.prompt_version == "1.0"

    manifest = load_manifest("venho_hotel", root=tmp_path)
    assert len(manifest["prompts"]) == 1


def test_dna_hash_change_bumps_version_and_archives_old_file(tmp_path):
    first = _build()
    save_with_manifest(first, root=tmp_path)

    changed = first.model_copy(
        update={
            "source_knowledge": [
                first.source_knowledge[0].model_copy(update={"hash": "sha256:changedhash"})
            ]
        }
    )
    saved_contract, paths, decision = save_with_manifest(changed, root=tmp_path)

    assert decision == RegenerationDecision.BUMPED
    assert saved_contract.prompt_version == "1.1"
    assert paths.markdown.name == "LAKE_VIEW_ROOM__booking-style__IMAGE_PROMPT_v1.1.md"

    archived = tmp_path / "venho_hotel" / "prompts" / "image" / "_archive" / "LAKE_VIEW_ROOM__booking-style__IMAGE_PROMPT_v1.0.md"
    assert archived.exists()
    live_old = tmp_path / "venho_hotel" / "prompts" / "image" / "LAKE_VIEW_ROOM__booking-style__IMAGE_PROMPT_v1.0.md"
    assert not live_old.exists()

    manifest = load_manifest("venho_hotel", root=tmp_path)
    assert len(manifest["prompts"]) == 1
    assert manifest["prompts"][0]["current_version"] == "1.1"
    assert manifest["prompts"][0]["source_knowledge_hashes"] == ["sha256:changedhash"]


def test_template_version_change_bumps_version_and_archives_old_file(tmp_path):
    first = _build()
    save_with_manifest(first, root=tmp_path)

    changed = first.model_copy(update={"template": first.template.model_copy(update={"template_version": "1.1"})})
    saved_contract, paths, decision = save_with_manifest(changed, root=tmp_path)

    assert decision == RegenerationDecision.BUMPED
    assert saved_contract.prompt_version == "1.1"

    manifest = load_manifest("venho_hotel", root=tmp_path)
    assert manifest["prompts"][0]["template_version"] == "1.1"
