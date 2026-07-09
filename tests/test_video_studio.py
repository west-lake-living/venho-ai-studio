from __future__ import annotations

import importlib
from shutil import copyfile
from pathlib import Path

import yaml

from prompt_studio.knowledge_reader import read_dna

from video_studio.continuity_checker import check_continuity
from video_studio.schemas.video_request import SourceKnowledgeRef, VideoRequest
from video_studio.storyboard_builder import build_storyboard
from video_studio.video_context import load_video_config
from video_studio.video_engine import generate_video_package


def _tmp_data_root(tmp_path: Path) -> Path:
    root = tmp_path / "data" / "projects"
    knowledge_dir = root / "venho_hotel" / "knowledge"
    knowledge_dir.mkdir(parents=True)
    for name in [
        "VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json",
        "VENHO_HOTEL_WESTLAKE_DNA.json",
        "VENHO_HOTEL_LINH_AN_DNA.json",
    ]:
        copyfile(Path("data/projects/venho_hotel/knowledge") / name, knowledge_dir / name)
    return root


def _source_ref(name: str, data_root: Path) -> SourceKnowledgeRef:
    dna = read_dna(data_root / "venho_hotel" / "knowledge" / name)
    return SourceKnowledgeRef(file=name, dna_version=dna.dna_version, hash=f"sha256:{dna.content_hash}")


def _request(data_root: Path) -> VideoRequest:
    return VideoRequest(
        project="venho_hotel",
        video_type="social_reel",
        topic="lake view room morning",
        duration_seconds=15,
        aspect_ratio="9:16",
        platform="instagram_reels",
        caption_language="vi",
        include_character=False,
        target_audience="Vietnamese leisure guests",
        source_knowledge=[
            _source_ref("VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json", data_root),
            _source_ref("VENHO_HOTEL_WESTLAKE_DNA.json", data_root),
        ],
        target_engine="veo",
        alt_engines=["kling"],
        validation_required=True,
    )


def test_video_studio_imports() -> None:
    module = importlib.import_module("video_studio")

    assert module.__doc__


def test_video_config_exists_without_spatial_forbidden_rules() -> None:
    video_dir = Path("config/projects/venho_hotel/video")
    expected = {
        "video_style.yaml",
        "platform_rules.yaml",
        "camera_rules.yaml",
        "motion_rules.yaml",
        "character_rules.yaml",
        "motion_negatives.yaml",
    }

    assert expected <= {path.name for path in video_dir.glob("*.yaml")}

    forbidden_keys = {"forbidden", "forbidden_claims", "spatial_forbidden", "brand_forbidden"}
    for path in video_dir.glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        assert forbidden_keys.isdisjoint(data.keys()), f"{path} must keep spatial/brand forbidden rules in M02"


def test_video_config_loader_keeps_forbidden_single_source() -> None:
    config = load_video_config("venho_hotel")

    assert "motion_negatives" in config
    assert "camera_rules" in config


def test_storyboard_duration_check_is_exact(tmp_path: Path) -> None:
    data_root = _tmp_data_root(tmp_path)
    request = _request(data_root)
    scenes, duration_check = build_storyboard(request, ["black aluminum window frame"])

    assert len(scenes) == 4
    assert duration_check.sum_scenes == 15
    assert duration_check.ok is True


def test_continuity_checker_fails_missing_key() -> None:
    data_root = Path("data/projects")
    request = _request(data_root)
    scenes, _duration_check = build_storyboard(request, ["black aluminum window frame"])

    result = check_continuity(scenes, ["not in prompt"])

    assert result.all_scenes_have_keys is False
    assert result.missing_by_scene


def test_video_engine_generates_mvp_lifestyle_reel(tmp_path: Path) -> None:
    data_root = _tmp_data_root(tmp_path)
    result = generate_video_package(_request(data_root), data_root=data_root, config_root=Path("config/projects"))

    package = result.package
    assert package.module == "video_studio"
    assert package.video_type == "social_reel"
    assert package.duration_check.ok is True
    assert package.duration_check.sum_scenes == 15
    assert package.continuity_check.all_scenes_have_keys is True
    assert package.text_from_content.caption_language == "vi"
    assert package.text_from_content.source_file
    assert package.engine_prompts[0].language == "en"
    assert "Module 02" not in package.engine_prompt_full
    assert all(scene.scene_prompt_ref and scene.scene_prompt_ref.source == "module_02" for scene in package.storyboard)
    assert result.markdown_path.exists()
    assert result.json_path.exists()
    assert result.manifest_path.exists()
    assert "## ENGINE PROMPT (English)" in result.markdown_path.read_text(encoding="utf-8")

