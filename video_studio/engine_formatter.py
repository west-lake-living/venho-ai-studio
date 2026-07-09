from __future__ import annotations

from pathlib import Path

import yaml

from prompt_studio.schemas.video_prompt import VideoPromptContract

from video_studio.schemas.engine_prompt import EnginePrompt
from video_studio.schemas.storyboard import StoryboardScene

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _engine_notes(engine: str) -> list[str]:
    path = _TEMPLATES_DIR / f"{engine}.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("notes", [])


def format_scene_prompt(
    contract: VideoPromptContract,
    scene: StoryboardScene,
    engine: str,
    aspect_ratio: str = "9:16",
) -> EnginePrompt:
    notes = _engine_notes(engine)
    notes_block = ("\n\nEngine Notes:\n" + "\n".join(f"- {n}" for n in notes)) if notes else ""
    prompt = f"""Engine: {engine}
Language: English
Duration: {scene.duration_seconds} seconds
Aspect: {aspect_ratio}

{contract.final_prompt}

Negative:
{contract.negative_prompt}{notes_block}"""
    return EnginePrompt(engine=engine, prompt=prompt.strip(), language="en")


def combine_engine_prompts(prompts: list[EnginePrompt]) -> str:
    return "\n\n---\n\n".join(prompt.prompt for prompt in prompts)

