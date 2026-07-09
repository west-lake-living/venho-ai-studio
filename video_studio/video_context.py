from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml

from prompt_studio.knowledge_reader import KnowledgeDna, read_dna

from video_studio.schemas.video_request import VideoRequest

DEFAULT_DATA_ROOT = Path("data/projects")
DEFAULT_CONFIG_ROOT = Path("config/projects")


class VideoConfigError(Exception):
    """Video config is missing, malformed, or crosses Module 06 boundaries."""


class MissingKnowledgeError(Exception):
    """Required Knowledge DNA was not available; M06 must stop instead of guessing."""


@dataclass
class VideoContext:
    request: VideoRequest
    config: Dict[str, Any]
    environment_dnas: List[KnowledgeDna]
    character_dna: KnowledgeDna | None
    continuity_keys: List[str]


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise VideoConfigError(f"{path} must contain a mapping")
    return data


def _assert_no_spatial_forbidden(config: Dict[str, Any], path: Path) -> None:
    forbidden_keys = {"forbidden", "forbidden_claims", "spatial_forbidden", "brand_forbidden"}
    present = forbidden_keys & set(config.keys())
    if present:
        raise VideoConfigError(
            f"{path} must not define spatial/brand forbidden rules ({sorted(present)}); keep them in Module 02"
        )


def load_video_config(project: str, config_root: Path = DEFAULT_CONFIG_ROOT) -> Dict[str, Any]:
    base = config_root / project / "video"
    files = {
        "video_style": base / "video_style.yaml",
        "platform_rules": base / "platform_rules.yaml",
        "camera_rules": base / "camera_rules.yaml",
        "motion_rules": base / "motion_rules.yaml",
        "character_rules": base / "character_rules.yaml",
        "motion_negatives": base / "motion_negatives.yaml",
    }
    config = {}
    for key, path in files.items():
        value = _read_yaml(path)
        _assert_no_spatial_forbidden(value, path)
        config[key] = value
    return config


def _is_character_dna(dna: KnowledgeDna) -> bool:
    return "linh_an" in dna.subject.lower() or "character" in dna.subject.lower()


def load_source_dnas(request: VideoRequest, data_root: Path = DEFAULT_DATA_ROOT) -> tuple[List[KnowledgeDna], KnowledgeDna | None]:
    dnas: List[KnowledgeDna] = []
    for source in request.source_knowledge:
        path = data_root / request.project / "knowledge" / source.file
        if not path.exists():
            raise MissingKnowledgeError(f"Missing source Knowledge DNA: {path}")
        dnas.append(read_dna(path))

    character_dnas = [dna for dna in dnas if _is_character_dna(dna)]
    character_dna = character_dnas[0] if request.include_character and character_dnas else None
    environment_dnas = [dna for dna in dnas if dna is not character_dna]
    if not environment_dnas:
        raise MissingKnowledgeError("Video Studio requires at least one environment DNA for Module 02 video prompts")
    return environment_dnas, character_dna


def build_continuity_keys(environment_dnas: List[KnowledgeDna], character_dna: KnowledgeDna | None) -> List[str]:
    keys: List[str] = []
    for dna in environment_dnas:
        for item in dna.required_dna[:3]:
            if item.value not in keys:
                keys.append(item.value)
    if character_dna:
        for item in character_dna.required_dna:
            if item.value not in keys:
                keys.append(item.value)
    return keys


def load_video_context(
    request: VideoRequest,
    *,
    config_root: Path = DEFAULT_CONFIG_ROOT,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> VideoContext:
    config = load_video_config(request.project, config_root=config_root)
    environment_dnas, character_dna = load_source_dnas(request, data_root=data_root)
    continuity_keys = build_continuity_keys(environment_dnas, character_dna)
    return VideoContext(
        request=request,
        config=config,
        environment_dnas=environment_dnas,
        character_dna=character_dna,
        continuity_keys=continuity_keys,
    )

