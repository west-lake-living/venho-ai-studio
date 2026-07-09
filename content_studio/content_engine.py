from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from prompt_studio.schemas.content_prompt import ContentPromptContract

from content_studio.builders.longform_builder import (
    build_blog_draft,
    build_email_draft,
    build_faq_draft,
    build_ota_draft,
    build_website_draft,
)
from content_studio.builders.social_builder import GeneratorFn, build_social_draft, mock_social_generator
from content_studio.content_context import DEFAULT_CONFIG_ROOT, DEFAULT_DATA_ROOT, load_content_context
from content_studio.content_manifest import update_manifest
from content_studio.content_validator_bridge import validate_draft
from content_studio.prompt_bridge import slugify
from content_studio.renderers.json_renderer import write_json
from content_studio.renderers.markdown_renderer import render_markdown
from content_studio.schemas.content_output import ContentOutput
from content_studio.schemas.content_request import ContentRequest

BuilderFn = Callable[[ContentRequest, ContentPromptContract, dict], ContentOutput]


@dataclass
class ContentEngineResult:
    output: ContentOutput
    markdown_path: Path
    json_path: Path
    manifest_path: Path


def _channel_dir(content_type: str) -> str:
    return content_type.removesuffix("_post").removesuffix("_caption")


def _file_stem(output: ContentOutput, topic: str) -> str:
    date = output.generated_at[:10]
    return f"{date}_{slugify(topic)}"


def _builder_for(content_type: str) -> BuilderFn:
    if content_type in {"facebook_post", "instagram_post", "threads_post", "tiktok_caption"}:
        return build_social_draft
    if content_type == "blog":
        return build_blog_draft
    if content_type == "website":
        return build_website_draft
    if content_type == "ota":
        return build_ota_draft
    if content_type == "faq":
        return build_faq_draft
    if content_type == "email":
        return build_email_draft
    raise ValueError(f"Unsupported content_type: {content_type}")


def generate_content(
    request: ContentRequest,
    *,
    config_root: Path = DEFAULT_CONFIG_ROOT,
    data_root: Path = DEFAULT_DATA_ROOT,
    generator_fn: GeneratorFn | None = None,
    validate: bool = True,
) -> ContentEngineResult:
    context = load_content_context(request, config_root=config_root, data_root=data_root)
    builder = _builder_for(request.content_type)
    if builder is build_social_draft:
        output = build_social_draft(
            request,
            context.prompt.contract,
            context.config,
            source_prompt_file=str(context.prompt.json_path),
            generator_fn=generator_fn or mock_social_generator,
        )
    else:
        output = builder(
            request,
            context.prompt.contract,
            context.config,
            source_prompt_file=str(context.prompt.json_path),
        )

    out_dir = data_root / request.project / "content" / _channel_dir(request.content_type)
    stem = _file_stem(output, request.topic)
    markdown_path = out_dir / f"{stem}.md"
    json_path = out_dir / f"{stem}.json"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(output), encoding="utf-8")

    if validate:
        validation = validate_draft(output, markdown_path, prompt_path=context.prompt.json_path)
        output = output.model_copy(update={"validation": validation})
        markdown_path.write_text(render_markdown(output), encoding="utf-8")

    write_json(json_path, output)
    manifest_path = update_manifest(output, markdown_path=markdown_path, json_path=json_path, root=data_root)
    return ContentEngineResult(
        output=output,
        markdown_path=markdown_path,
        json_path=json_path,
        manifest_path=manifest_path,
    )
