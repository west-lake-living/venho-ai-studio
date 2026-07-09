from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from prompt_studio.builders.video_prompt_builder import build_video_prompt
from prompt_studio.prompt_store import PromptFilePaths, save_prompt
from prompt_studio.schemas.video_prompt import VideoPromptContract

from video_studio.schemas.storyboard import StoryboardScene
from video_studio.video_context import VideoContext


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "video"


@dataclass
class ScenePromptResult:
    contract: VideoPromptContract
    paths: PromptFilePaths


def build_scene_prompt(
    context: VideoContext,
    scene: StoryboardScene,
    *,
    prompts_root: Path,
) -> ScenePromptResult:
    continuity = "\n".join(f"- {key}" for key in context.continuity_keys)
    task_brief = f"""Scene {scene.scene_number} for a {context.request.duration_seconds}s {context.request.video_type}.
Topic: {context.request.topic}.
Scene description: {scene.description}
Duration: {scene.duration_seconds} seconds.
Aspect ratio: {context.request.aspect_ratio}.
Camera movement: {scene.camera_movement}.
Continuity keys that must appear exactly:
{continuity}
Write the engine-facing scene prompt in English."""
    contract = build_video_prompt(
        environment_dnas=context.environment_dnas,
        character_dna=context.character_dna,
        task_brief=task_brief,
        brief_slug=f"{slugify(context.request.topic)}_scene_{scene.scene_number}",
    )
    paths = save_prompt(contract, root=prompts_root)
    return ScenePromptResult(contract=contract, paths=paths)

