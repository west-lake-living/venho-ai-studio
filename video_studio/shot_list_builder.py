from __future__ import annotations

from video_studio.schemas.shot import Shot
from video_studio.schemas.storyboard import StoryboardScene


def build_shot_list(storyboard: list[StoryboardScene]) -> list[Shot]:
    shots: list[Shot] = []
    for scene in storyboard:
        shots.append(
            Shot(
                scene_number=scene.scene_number,
                angle="eye-level natural hotel perspective",
                camera_movement=scene.camera_movement,
                motion_note="subtle environmental movement only",
                lighting_note="natural warm light, realistic exposure",
            )
        )
    return shots

