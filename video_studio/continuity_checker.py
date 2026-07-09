from __future__ import annotations

from video_studio.schemas.storyboard import ContinuityCheck, StoryboardScene


def check_continuity(storyboard: list[StoryboardScene], continuity_keys: list[str]) -> ContinuityCheck:
    missing: dict[int, list[str]] = {}
    for scene in storyboard:
        haystack = f"{scene.description}\n{scene.engine_prompt or ''}"
        scene_missing = [key for key in continuity_keys if key not in haystack]
        if scene_missing:
            missing[scene.scene_number] = scene_missing
    return ContinuityCheck(all_scenes_have_keys=not missing, missing_by_scene=missing)

