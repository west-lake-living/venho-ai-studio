from __future__ import annotations

from video_studio.schemas.storyboard import DurationCheck, StoryboardScene
from video_studio.schemas.video_request import VideoRequest


class DurationMismatchError(Exception):
    """Storyboard scene durations must exactly match the requested video duration."""


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
    scene_templates = [
        ("Opening detail", "slow push-in"),
        ("Room and lake context", "gentle pan"),
        ("Human-scale atmosphere", "static composed shot"),
        ("Closing brand-safe CTA visual", "slow hold"),
        ("Final transition detail", "clean natural cut"),
    ]
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

