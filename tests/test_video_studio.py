from __future__ import annotations

import importlib
from pathlib import Path

import yaml


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

