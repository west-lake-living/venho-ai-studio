from __future__ import annotations

from video_studio.schemas.shot import Shot
from video_studio.schemas.storyboard import StoryboardScene

_PUSH_MOVEMENTS = ("push-in", "arc", "track")
_STATIC_MOVEMENTS = ("static", "hold")


def _angle(scene_number: int, total: int) -> str:
    position = scene_number / total
    if position <= 0.3:
        return "low angle or close-up detail"
    if position <= 0.7:
        return "eye-level natural hotel perspective"
    return "eye-level or slight high angle for closure"


def _motion_note(camera_movement: str) -> str:
    if any(m in camera_movement for m in _PUSH_MOVEMENTS):
        return "controlled motion, no shake"
    if any(m in camera_movement for m in _STATIC_MOVEMENTS):
        return "minimal movement, environmental motion only"
    return "smooth movement, natural pace"


def _lighting_note(scene_number: int, total: int) -> str:
    position = scene_number / total
    if position <= 0.3:
        return "natural warm light or soft key light"
    if position <= 0.7:
        return "natural ambient, avoid harsh shadows"
    return "warm golden tones, soft close"


def build_shot_list(storyboard: list[StoryboardScene]) -> list[Shot]:
    total = len(storyboard)
    return [
        Shot(
            scene_number=scene.scene_number,
            angle=_angle(scene.scene_number, total),
            camera_movement=scene.camera_movement,
            motion_note=_motion_note(scene.camera_movement),
            lighting_note=_lighting_note(scene.scene_number, total),
        )
        for scene in storyboard
    ]
