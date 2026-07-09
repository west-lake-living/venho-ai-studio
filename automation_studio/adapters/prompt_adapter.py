from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from automation_studio.paths import BASE_DIR
from automation_studio.types import StepResult


def _slugify(text: str, max_words: int = 5) -> str:
    words = re.findall(r"[A-Za-z0-9]+", text.lower())[:max_words]
    return "-".join(words) if words else "brief"


def _resolve_dna_path(project: str, subject: str) -> Path:
    knowledge_dir = BASE_DIR / "data" / "projects" / project / "knowledge"
    candidates = sorted(knowledge_dir.glob(f"*_{subject.upper()}_DNA.json"))
    if not candidates:
        raise FileNotFoundError(f"No DNA JSON found for subject '{subject}' in {knowledge_dir}")
    return candidates[0]


def _read_dna(project: str, subject: str):
    from prompt_studio.knowledge_reader import read_dna

    return read_dna(_resolve_dna_path(project, subject))


def generate_prompt(
    project: str,
    subject_or_subjects: str | list[str],
    prompt_type: str,
    brief: str,
    target_language: str | None = None,
    settings: dict[str, Any] | None = None,
) -> StepResult:
    from prompt_studio.pipeline import (
        run_content_pipeline,
        run_image_pipeline,
        run_seo_pipeline,
        run_video_pipeline,
    )
    from prompt_studio.optimizer_mock import optimize_mock
    from prompt_studio.optimizer import optimize
    from prompt_studio.prompt_store import DEFAULT_PROMPTS_ROOT, build_file_stem

    settings = settings or {}
    subjects = (
        [subject.strip() for subject in subject_or_subjects.split(",") if subject.strip()]
        if isinstance(subject_or_subjects, str)
        else list(subject_or_subjects)
    )
    if not subjects:
        raise ValueError("subject_or_subjects must contain at least one subject")

    brief_slug = settings.get("brief_slug") or _slugify(brief)
    allow_draft = bool(settings.get("allow_draft", False))
    optimize_fn = optimize_mock if settings.get("mock") else optimize
    prompt_type = prompt_type.lower()

    if prompt_type == "image":
        result = run_image_pipeline(_read_dna(project, subjects[0]), brief, brief_slug, allow_draft=allow_draft, optimize_fn=optimize_fn)
    elif prompt_type == "video":
        if len(subjects) == 1:
            character_dna = None
            environment_dnas = [_read_dna(project, subjects[0])]
        else:
            character_dna = _read_dna(project, subjects[0])
            environment_dnas = [_read_dna(project, subject) for subject in subjects[1:]]
        result = run_video_pipeline(environment_dnas, brief, brief_slug, character_dna=character_dna, allow_draft=allow_draft, optimize_fn=optimize_fn)
    elif prompt_type == "content":
        result = run_content_pipeline(_read_dna(project, subjects[0]), brief, brief_slug, target_language=target_language, allow_draft=allow_draft, optimize_fn=optimize_fn)
    elif prompt_type == "seo":
        keyword = settings.get("keyword") or brief
        result = run_seo_pipeline(_read_dna(project, subjects[0]), brief, brief_slug, keyword, target_language=target_language, allow_draft=allow_draft, optimize_fn=optimize_fn)
    else:
        raise ValueError("prompt_type must be one of: image, video, content, seo")

    outputs = []
    if result.paths:
        outputs = [result.paths.markdown, result.paths.json]
    elif result.regeneration_decision == "no_change":
        prompt_dir = DEFAULT_PROMPTS_ROOT / result.contract.project / "prompts" / result.contract.prompt_type
        stem = build_file_stem(result.contract)
        outputs = [path for path in (prompt_dir / f"{stem}.md", prompt_dir / f"{stem}.json") if path.exists()]
    warnings = list(result.notes)
    return StepResult(
        status="success",
        outputs=outputs,
        warnings=warnings,
        data={
            "prompt_id": result.contract.prompt_id,
            "prompt_type": result.contract.prompt_type,
            "validation": result.contract.validation.model_dump(mode="json"),
        },
    )
