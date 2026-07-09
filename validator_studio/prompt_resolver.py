from __future__ import annotations

from pathlib import Path
from typing import Optional

from validator_studio.utils import BASE_DIR, load_json


class PromptManifestError(Exception):
    """Raised when a prompt cannot be resolved from Module 02 manifest data."""


def prompt_manifest_path(project: str, base_dir: Path = BASE_DIR) -> Path:
    return base_dir / "data" / "projects" / project / "prompts" / "prompt_manifest.json"


def load_prompt_manifest(project: str, base_dir: Path = BASE_DIR) -> dict:
    path = prompt_manifest_path(project, base_dir)
    if not path.exists():
        raise PromptManifestError(f"Prompt manifest not found: {path}")
    data = load_json(path)
    if not isinstance(data, dict) or "prompts" not in data:
        raise PromptManifestError(f"Invalid prompt manifest: {path}")
    return data


def resolve_latest_prompt_path(
    project: str,
    subject: str,
    prompt_type: str,
    brief_slug: Optional[str] = None,
    base_dir: Path = BASE_DIR,
) -> Path:
    """Resolve the active Module 02 prompt JSON from prompt_manifest.json.

    If `brief_slug` is omitted, exactly one active prompt for subject+type must exist.
    """
    manifest = load_prompt_manifest(project, base_dir)
    matches = [
        entry for entry in manifest.get("prompts", [])
        if entry.get("status", "active") == "active"
        and entry.get("subject") == subject
        and entry.get("prompt_type") == prompt_type
        and (brief_slug is None or entry.get("brief_slug") == brief_slug)
    ]
    if not matches:
        detail = f"{project}/{subject}/{prompt_type}"
        if brief_slug:
            detail += f"/{brief_slug}"
        raise PromptManifestError(f"No active prompt manifest entry for {detail}")
    if len(matches) > 1:
        slugs = ", ".join(sorted(str(entry.get("brief_slug")) for entry in matches))
        raise PromptManifestError(f"Multiple active prompts found; pass --brief-slug. Available: {slugs}")

    entry = matches[0]
    stem = (
        f"{subject.upper()}__{entry['brief_slug']}__"
        f"{prompt_type.upper()}_PROMPT_v{entry['current_version']}"
    )
    path = base_dir / "data" / "projects" / project / "prompts" / prompt_type / f"{stem}.json"
    if not path.exists():
        raise PromptManifestError(f"Prompt JSON listed in manifest is missing: {path}")
    return path

