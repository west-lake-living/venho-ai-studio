from __future__ import annotations

from video_studio.schemas.storyboard import DurationCheck, StoryboardScene
from video_studio.schemas.video_request import VideoRequest


class DurationMismatchError(Exception):
    """Storyboard scene durations must exactly match the requested video duration."""


_SCENE_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "social_reel": [
        ("Opening hook close-up", "fast push-in"),
        ("Environment context reveal", "gentle pan"),
        ("Human-scale lifestyle moment", "static composed shot"),
        ("Closing CTA visual", "slow hold"),
        ("Final cut-away detail", "clean natural cut"),
    ],
    "character": [
        ("Character introduction moment", "slow push-in toward character"),
        ("Character in environment context", "gentle arc around character"),
        ("Character interaction or expression", "static composed medium shot"),
        ("Character and brand identity beat", "slow hold on face"),
        ("Character signature closing gesture", "clean natural cut"),
    ],
    "hotel_lifestyle": [
        ("Opening detail of hotel space", "slow push-in"),
        ("Room and lake view context", "gentle pan"),
        ("Human-scale hotel atmosphere", "static composed shot"),
        ("Closing brand-safe CTA visual", "slow hold"),
        ("Final transition detail", "clean natural cut"),
    ],
    "website_hero": [
        ("Establishing wide hotel shot", "slow push-in"),
        ("Signature hotel feature detail", "gentle pan"),
        ("Lifestyle or guest experience moment", "static composed"),
        ("Brand identity visual close", "slow hold"),
        ("End card transition", "clean natural cut"),
    ],
    "explainer": [
        ("Hook statement or problem visual", "static composed"),
        ("Solution or feature reveal", "gentle pan"),
        ("Feature demonstration detail", "slow push-in"),
        ("Proof or social evidence moment", "static composed"),
        ("CTA close with brand visual", "slow hold"),
    ],
}
_DEFAULT_TEMPLATES = _SCENE_TEMPLATES["hotel_lifestyle"]


def _durations(total: int, scene_count: int) -> list[int]:
    base = total // scene_count
    remainder = total % scene_count
    return [base + (1 if index < remainder else 0) for index in range(scene_count)]


def planned_scene_count(request: VideoRequest) -> int:
    if request.duration_seconds <= 12:
        return 3
    if request.duration_seconds <= 20:
        return 4
    return 5


def build_storyboard(request: VideoRequest, continuity_keys: list[str]) -> tuple[list[StoryboardScene], DurationCheck]:
    durations = _durations(request.duration_seconds, planned_scene_count(request))
    scene_templates = _SCENE_TEMPLATES.get(request.video_type, _DEFAULT_TEMPLATES)
    scenes: list[StoryboardScene] = []
    for index, duration in enumerate(durations, start=1):
        label, movement = scene_templates[index - 1]
        scenes.append(
            StoryboardScene(
                scene_number=index,
                duration_seconds=duration,
                description=f"{label} for {request.topic}, grounded in the provided Knowledge DNA.",
                camera_movement=movement,
                visual_dna_required=list(continuity_keys),
            )
        )
    check = DurationCheck(
        sum_scenes=sum(scene.duration_seconds for scene in scenes),
        target=request.duration_seconds,
        ok=sum(scene.duration_seconds for scene in scenes) == request.duration_seconds,
    )
    if not check.ok:
        raise DurationMismatchError(f"Storyboard duration {check.sum_scenes}s != request {check.target}s")
    return scenes, check
