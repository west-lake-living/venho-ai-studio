from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from video_studio.concept_builder import build_concept
from video_studio.content_bridge import build_text_from_content
from video_studio.continuity_checker import check_continuity
from video_studio.engine_formatter import combine_engine_prompts, format_scene_prompt
from video_studio.prompt_bridge import build_scene_prompt, slugify
from video_studio.renderers.json_renderer import write_json
from video_studio.renderers.markdown_renderer import render_markdown
from video_studio.schemas.storyboard import ScenePromptRef
from video_studio.schemas.video_package import VideoPackage
from video_studio.schemas.video_request import VideoRequest
from video_studio.shot_list_builder import build_shot_list
from video_studio.storyboard_builder import build_storyboard
from video_studio.validator_bridge import validate_scene_prompts
from video_studio.video_context import DEFAULT_CONFIG_ROOT, DEFAULT_DATA_ROOT, load_video_context
from video_studio.video_manifest import update_manifest


@dataclass
class VideoEngineResult:
    package: VideoPackage
    markdown_path: Path
    json_path: Path
    manifest_path: Path


def _motion_negative_prompt(config: dict) -> str:
    negatives = config.get("motion_negatives", {}).get("default", [])
    return ", ".join(negatives)


def _file_stem(package: VideoPackage, topic: str) -> str:
    date = package.generated_at[:10]
    return f"{date}_{slugify(topic)}_{package.duration_seconds}s"


def generate_video_package(
    request: VideoRequest,
    *,
    config_root: Path = DEFAULT_CONFIG_ROOT,
    data_root: Path = DEFAULT_DATA_ROOT,
    validate: bool = True,
) -> VideoEngineResult:
    context = load_video_context(request, config_root=config_root, data_root=data_root)
    concept = build_concept(request, context.config)
    storyboard, duration_check = build_storyboard(request, context.continuity_keys)
    shot_list = build_shot_list(storyboard)
    text = build_text_from_content(request, config_root=config_root, data_root=data_root).text

    scene_contracts = []
    primary_engine_prompts = []
    for index, scene in enumerate(storyboard):
        prompt_result = build_scene_prompt(context, scene, prompts_root=data_root)
        scene_contracts.append(prompt_result.contract.model_dump(mode="json"))
        engine_prompt = format_scene_prompt(prompt_result.contract, scene, request.target_engine)
        primary_engine_prompts.append(engine_prompt)
        storyboard[index] = scene.model_copy(
            update={
                "scene_prompt_ref": ScenePromptRef(
                    prompt_id=prompt_result.contract.prompt_id,
                    prompt_version=prompt_result.contract.prompt_version,
                    file=str(prompt_result.paths.json),
                ),
                "engine_prompt": engine_prompt.prompt,
                "forbidden": [item.model_dump(mode="json") for item in prompt_result.contract.forbidden],
            }
        )

    continuity_check = check_continuity(storyboard, context.continuity_keys)
    validation = (
        validate_scene_prompts(request, scene_contracts, required=request.validation_required)
        if validate
        else validate_scene_prompts(request, [], required=request.validation_required).model_copy(update={"status": "pending"})
    )
    if not continuity_check.all_scenes_have_keys:
        validation = validation.model_copy(
            update={
                "status": "fail",
                "notes": validation.notes + [f"Continuity missing by scene: {continuity_check.missing_by_scene}"],
            }
        )

    package = VideoPackage(
        project=request.project,
        video_type=request.video_type,
        duration_seconds=request.duration_seconds,
        aspect_ratio=request.aspect_ratio,
        platform=request.platform,
        target_engine=request.target_engine,
        alt_engines=request.alt_engines,
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_knowledge=request.source_knowledge,
        continuity_keys=context.continuity_keys,
        concept=concept,
        storyboard=storyboard,
        shot_list=shot_list,
        duration_check=duration_check,
        continuity_check=continuity_check,
        text_from_content=text,
        engine_prompt_full=combine_engine_prompts(primary_engine_prompts),
        engine_prompts=primary_engine_prompts,
        motion_negative_prompt=_motion_negative_prompt(context.config),
        character_rules=context.config.get("character_rules", {}),
        camera_motion_rules={
            "camera_rules": context.config.get("camera_rules", {}),
            "motion_rules": context.config.get("motion_rules", {}),
        },
        validation=validation,
    )

    out_dir = data_root / request.project / "video" / "packages"
    stem = _file_stem(package, request.topic)
    markdown_path = out_dir / f"{stem}.md"
    json_path = out_dir / f"{stem}.json"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(package), encoding="utf-8")
    write_json(json_path, package)
    manifest_path = update_manifest(package, markdown_path=markdown_path, json_path=json_path, root=data_root)
    return VideoEngineResult(package=package, markdown_path=markdown_path, json_path=json_path, manifest_path=manifest_path)

