from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from content_studio.schemas.content_output import ContentOutput


def _manifest_path(project: str, root: Path) -> Path:
    return root / project / "content" / "content_manifest.json"


def load_manifest(project: str, root: Path = Path("data/projects")) -> Dict[str, Any]:
    path = _manifest_path(project, root)
    if not path.exists():
        return {"contract_version": "1.0", "module": "content_studio", "items": []}
    return json.loads(path.read_text(encoding="utf-8"))


def update_manifest(
    output: ContentOutput,
    *,
    markdown_path: Path,
    json_path: Path,
    root: Path = Path("data/projects"),
) -> Path:
    path = _manifest_path(output.project, root)
    manifest = load_manifest(output.project, root=root)
    items: List[Dict[str, Any]] = list(manifest.get("items", []))
    item_id = json_path.stem
    items = [item for item in items if item.get("id") != item_id]
    items.append(
        {
            "id": item_id,
            "type": output.content_type,
            "source_knowledge_hashes": [item.hash for item in output.source_knowledge],
            "source_prompt_version": output.source_prompt.prompt_version,
            "target_language": output.target_language,
            "generated_at": output.generated_at,
            "status": output.status,
            "staleness": "current",
            "markdown": str(markdown_path),
            "json": str(json_path),
        }
    )
    manifest["items"] = sorted(items, key=lambda item: item["generated_at"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


@dataclass
class StalenessResult:
    stale_count: int
    manifest_path: Path


def mark_stale_sources(
    project: str,
    latest_hashes: Dict[str, str],
    *,
    root: Path = Path("data/projects"),
) -> StalenessResult:
    path = _manifest_path(project, root)
    manifest = load_manifest(project, root=root)
    stale_count = 0
    for item in manifest.get("items", []):
        hashes = item.get("source_knowledge_hashes", [])
        if any(source_hash not in latest_hashes.values() for source_hash in hashes):
            item["staleness"] = "source_updated"
            stale_count += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return StalenessResult(stale_count=stale_count, manifest_path=path)

