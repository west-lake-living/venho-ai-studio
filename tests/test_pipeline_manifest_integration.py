"""Confirms all four pipeline wrappers save through the manifest + regeneration policy (§13),
not just the image path already covered in test_pipeline.py."""

from pathlib import Path

from prompt_studio.knowledge_reader import read_dna
from prompt_studio.optimizer_mock import optimize_mock
from prompt_studio.pipeline import (
    run_content_pipeline,
    run_image_pipeline,
    run_seo_pipeline,
    run_video_pipeline,
)
from prompt_studio.prompt_manifest import RegenerationDecision, load_manifest

LAKE_VIEW_ROOM_DNA = Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json")
LINH_AN_DNA = Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_LINH_AN_DNA.json")
WESTLAKE_DNA = Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_WESTLAKE_DNA.json")


def test_image_pipeline_saves_via_manifest_and_is_no_change_on_rerun(tmp_path):
    dna = read_dna(LAKE_VIEW_ROOM_DNA)
    first = run_image_pipeline(dna, "Booking-style image.", "booking-style", optimize_fn=optimize_mock, root=tmp_path)
    assert first.regeneration_decision == RegenerationDecision.NEW

    second = run_image_pipeline(dna, "Booking-style image.", "booking-style", optimize_fn=optimize_mock, root=tmp_path)
    assert second.regeneration_decision == RegenerationDecision.NO_CHANGE
    assert second.paths is None

    manifest = load_manifest("venho_hotel", root=tmp_path)
    assert len(manifest["prompts"]) == 1


def test_video_pipeline_saves_via_manifest(tmp_path):
    character = read_dna(LINH_AN_DNA)
    environment = read_dna(LAKE_VIEW_ROOM_DNA)

    result = run_video_pipeline(
        [environment], "A 15-second video of Linh An standing at the lake view room window at golden hour.",
        "window-15s", character_dna=character, optimize_fn=optimize_mock, root=tmp_path,
    )
    assert result.regeneration_decision == RegenerationDecision.NEW
    assert result.paths is not None
    assert result.paths.markdown.name.startswith("LINH_AN+LAKE_VIEW_ROOM__")

    manifest = load_manifest("venho_hotel", root=tmp_path)
    assert manifest["prompts"][0]["prompt_type"] == "video"


def test_content_pipeline_saves_via_manifest():
    dna = read_dna(WESTLAKE_DNA)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = run_content_pipeline(dna, "FB post about West Lake.", "fb-stay", optimize_fn=optimize_mock, root=root)
        assert result.regeneration_decision == RegenerationDecision.NEW
        assert result.paths is not None
        manifest = load_manifest("venho_hotel", root=root)
        assert manifest["prompts"][0]["prompt_type"] == "content"


def test_seo_pipeline_saves_via_manifest():
    dna = read_dna(WESTLAKE_DNA)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = run_seo_pipeline(
            dna, "Blog post about hotels near West Lake.", "blog", "hotels near west lake hanoi",
            optimize_fn=optimize_mock, root=root,
        )
        assert result.regeneration_decision == RegenerationDecision.NEW
        assert result.paths is not None
        manifest = load_manifest("venho_hotel", root=root)
        assert manifest["prompts"][0]["prompt_type"] == "seo"
