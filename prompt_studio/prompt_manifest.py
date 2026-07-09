"""Prompt Manifest + Regeneration Policy (§13, §14, §16 Step 13).

Tracks, per prompt_id, which DNA hash(es) + template_version last produced it:

    Knowledge + template unchanged  → NO_CHANGE: skip saving, nothing on disk touched
    DNA hash or template_version changed → BUMPED: archive the old file, bump prompt_version
    prompt_id not seen before        → NEW: save as prompt_version "1.0" (or whatever the
                                        Builder set) and add a manifest entry

Draft prompts (pipeline `allow_draft` fallback) are never tracked here — only official,
faithfulness-passing prompts are versioned and archived (§13).
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from prompt_studio.prompt_store import DEFAULT_PROMPTS_ROOT, PromptFilePaths, build_file_stem, save_prompt
from prompt_studio.schemas.prompt_contract import PromptContractBase

MANIFEST_FILENAME = "prompt_manifest.json"


class RegenerationDecision:
    NEW = "new"
    NO_CHANGE = "no_change"
    BUMPED = "bumped"


@dataclass
class RegenerationResult:
    decision: str
    contract: PromptContractBase
    entry: Dict[str, Any]
    previous_version: Optional[str] = None


def manifest_path(project: str, root: Path = DEFAULT_PROMPTS_ROOT) -> Path:
    return root / project / "prompts" / MANIFEST_FILENAME


def load_manifest(project: str, root: Path = DEFAULT_PROMPTS_ROOT) -> Dict[str, Any]:
    path = manifest_path(project, root)
    if not path.exists():
        return {"project": project, "prompts": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(manifest: Dict[str, Any], root: Path = DEFAULT_PROMPTS_ROOT) -> Path:
    path = manifest_path(manifest["project"], root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _find_entry(manifest: Dict[str, Any], prompt_id: str) -> Optional[Dict[str, Any]]:
    for entry in manifest["prompts"]:
        if entry["prompt_id"] == prompt_id:
            return entry
    return None


def _bump_version(version: str) -> str:
    major, _, minor = version.partition(".")
    try:
        return f"{major}.{int(minor) + 1}"
    except ValueError:
        return f"{version}.1"


def _entry_from_contract(contract: PromptContractBase) -> Dict[str, Any]:
    subject, _prompt_type, brief_slug = contract.prompt_id.split("__")
    return {
        "prompt_id": contract.prompt_id,
        "prompt_type": contract.prompt_type,
        "subject": subject,
        "brief_slug": brief_slug,
        "current_version": contract.prompt_version,
        "source_knowledge_hashes": [entry.hash for entry in contract.source_knowledge],
        "template_version": contract.template.template_version,
        "target_language": contract.target_language,
        "generated_at": contract.generated_at,
        "status": "active",
    }


def resolve_regeneration(contract: PromptContractBase, root: Path = DEFAULT_PROMPTS_ROOT) -> RegenerationResult:
    """Compare a freshly-Built `contract` against the manifest entry for its prompt_id (§13)."""
    manifest = load_manifest(contract.project, root)
    existing = _find_entry(manifest, contract.prompt_id)

    if existing is None:
        return RegenerationResult(decision=RegenerationDecision.NEW, contract=contract, entry=_entry_from_contract(contract))

    new_hashes = [entry.hash for entry in contract.source_knowledge]
    same_knowledge = existing["source_knowledge_hashes"] == new_hashes
    same_template = existing["template_version"] == contract.template.template_version

    if same_knowledge and same_template:
        unchanged = contract.model_copy(update={"prompt_version": existing["current_version"]})
        return RegenerationResult(decision=RegenerationDecision.NO_CHANGE, contract=unchanged, entry=existing)

    bumped = contract.model_copy(update={"prompt_version": _bump_version(existing["current_version"])})
    return RegenerationResult(
        decision=RegenerationDecision.BUMPED,
        contract=bumped,
        entry=_entry_from_contract(bumped),
        previous_version=existing["current_version"],
    )


def _archive_existing_files(contract: PromptContractBase, previous_version: str, root: Path) -> None:
    """Move the .md/.json saved under the previous version into prompts/<type>/_archive/."""
    prompt_dir = root / contract.project / "prompts" / contract.prompt_type
    archive_dir = prompt_dir / "_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    old_stem = build_file_stem(contract.model_copy(update={"prompt_version": previous_version}))
    for ext in ("md", "json"):
        src = prompt_dir / f"{old_stem}.{ext}"
        if src.exists():
            shutil.move(str(src), str(archive_dir / f"{old_stem}.{ext}"))


def save_with_manifest(
    contract: PromptContractBase, root: Path = DEFAULT_PROMPTS_ROOT
) -> Tuple[PromptContractBase, Optional[PromptFilePaths], str]:
    """Apply the regeneration policy and persist: save + manifest update, or skip on NO_CHANGE."""
    result = resolve_regeneration(contract, root)

    if result.decision == RegenerationDecision.NO_CHANGE:
        return result.contract, None, result.decision

    if result.decision == RegenerationDecision.BUMPED and result.previous_version:
        _archive_existing_files(result.contract, result.previous_version, root)

    paths = save_prompt(result.contract, root=root)

    manifest = load_manifest(result.contract.project, root)
    manifest["prompts"] = [e for e in manifest["prompts"] if e["prompt_id"] != result.contract.prompt_id]
    manifest["prompts"].append(result.entry)
    save_manifest(manifest, root)

    return result.contract, paths, result.decision
