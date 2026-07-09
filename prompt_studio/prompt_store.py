"""Writes a Prompt Contract as .md + .json into data/projects/<project>/prompts/<type>/
(§4, §7.2). File name is SUBJECT__brief_slug__TYPE_PROMPT_vVERSION so two different briefs
for the same subject never collide (§14)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from prompt_studio.prompt_renderer import render_markdown
from prompt_studio.schemas.prompt_contract import PromptContractBase

DEFAULT_PROMPTS_ROOT = Path("data/projects")


class PromptIdFormatError(Exception):
    """prompt_id does not follow the subject__type__brief_slug shape (§14)."""


@dataclass
class PromptFilePaths:
    markdown: Path
    json: Path


def _split_prompt_id(prompt_id: str) -> Tuple[str, str, str]:
    parts = prompt_id.split("__")
    if len(parts) != 3:
        raise PromptIdFormatError(
            f"prompt_id '{prompt_id}' must be 'subject__prompt_type__brief_slug' (exactly two '__')"
        )
    return parts[0], parts[1], parts[2]


def build_file_stem(contract: PromptContractBase) -> str:
    subject, _prompt_type, brief_slug = _split_prompt_id(contract.prompt_id)
    return f"{subject.upper()}__{brief_slug}__{contract.prompt_type.upper()}_PROMPT_v{contract.prompt_version}"


def save_prompt(contract: PromptContractBase, root: Path = DEFAULT_PROMPTS_ROOT) -> PromptFilePaths:
    """Write contract.md + contract.json under <root>/<project>/prompts/<prompt_type>/."""
    out_dir = root / contract.project / "prompts" / contract.prompt_type
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = build_file_stem(contract)
    md_path = out_dir / f"{stem}.md"
    json_path = out_dir / f"{stem}.json"

    md_path.write_text(render_markdown(contract), encoding="utf-8")
    json_path.write_text(json.dumps(contract.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")

    return PromptFilePaths(markdown=md_path, json=json_path)
