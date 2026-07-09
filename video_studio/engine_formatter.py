from __future__ import annotations

from prompt_studio.schemas.video_prompt import VideoPromptContract

from video_studio.schemas.engine_prompt import EnginePrompt
from video_studio.schemas.storyboard import StoryboardScene


def format_scene_prompt(contract: VideoPromptContract, scene: StoryboardScene, engine: str) -> EnginePrompt:
    prompt = f"""Engine: {engine}
Language: English
Duration: {scene.duration_seconds} seconds
Aspect: keep the requested production aspect ratio

{contract.final_prompt}

Negative:
{contract.negative_prompt}"""
    return EnginePrompt(engine=engine, prompt=prompt.strip(), language="en")


def combine_engine_prompts(prompts: list[EnginePrompt]) -> str:
    return "\n\n---\n\n".join(prompt.prompt for prompt in prompts)

