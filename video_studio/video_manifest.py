from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from video_studio.schemas.video_package import VideoPackage


def _manifest_path(project: str, root: Path) -> Path:
    return root / project / "video" / "video_manifest.json"


def load_manifest(project: str, root: Path = Path("data/projects")) -> Dict[str, Any]:
    path = _manifest_path(project, root)
    if not path.exists():
        return {"contract_version": "1.0", "module": "video_studio", "items": []}
    return json.loads(path.read_text(encoding="utf-8"))


def update_manifest(package: VideoPackage, *, markdown_path: Path, json_path: Path, root: Path = Path("data/projects")) -> Path:
    path = _manifest_path(package.project, root)
    manifest = load_manifest(package.project, root=root)
    items = [item for item in manifest.get("items", []) if item.get("id") != json_path.stem]
    items.append(
        {
            "id": json_path.stem,
            "type": package.video_type,
            "target_engine": package.target_engine,
            "duration_seconds": package.duration_seconds,
            "source_knowledge_hashes": [item.hash for item in package.source_knowledge],
            "generated_at": package.generated_at,
            "status": package.status,
            "validation_status": package.validation.status,
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


def mark_stale_sources(project: str, latest_hashes: Dict[str, str], *, root: Path = Path("data/projects")) -> StalenessResult:
    path = _manifest_path(project, root)
    manifest = load_manifest(project, root=root)
    stale_count = 0
    for item in manifest.get("items", []):
        if any(source_hash not in latest_hashes.values() for source_hash in item.get("source_knowledge_hashes", [])):
            item["staleness"] = "source_updated"
            stale_count += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return StalenessResult(stale_count=stale_count, manifest_path=path)

