from __future__ import annotations

"""DNA manifest management: versioning, archiving, change detection."""

import json
import shutil
from datetime import datetime
from pathlib import Path

from knowledge_studio.vision.schemas.base import BaseDNA


def _manifest_path(knowledge_dir: Path, subject: str) -> Path:
    return knowledge_dir / f"dna_manifest_{subject}.json"


def _archive_dir(knowledge_dir: Path) -> Path:
    return knowledge_dir / "_archive"


def load_manifest(knowledge_dir: Path, subject: str) -> dict | None:
    path = _manifest_path(knowledge_dir, subject)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(
    knowledge_dir: Path,
    subject: str,
    dna: BaseDNA,
    overlay_applied: bool = False,
) -> None:
    manifest = {
        "subject": subject,
        "current_version": dna.dna_version,
        "source_hashes": dna.source_images,
        "generated_at": dna.generated_at,
        "schema_id": dna.schema_id,
        "schema_version": dna.schema_version,
        "prompt_version": dna.prompt_version,
        "provider": dna.provider,
        "model": dna.model,
        "overlay_applied": overlay_applied,
    }
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    _manifest_path(knowledge_dir, subject).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def hashes_changed(manifest: dict | None, new_hashes: list[str]) -> bool:
    if manifest is None:
        return True
    old = set(manifest.get("source_hashes", []))
    new = set(new_hashes)
    return old != new


def needs_regeneration(
    manifest: dict | None,
    new_hashes: list[str],
    schema_version: str,
    prompt_version: str,
) -> bool:
    """True if source images changed, OR schema/prompt version drifted since last DNA build.

    Per master plan §11: changing the prompt or schema must invalidate the cache —
    otherwise a corrected prompt never propagates into DNA for an unchanged image set.
    """
    if hashes_changed(manifest, new_hashes):
        return True
    return (
        manifest.get("schema_version") != schema_version
        or manifest.get("prompt_version") != prompt_version
    )


def archive_dna(
    knowledge_dir: Path,
    dna_filename: str,
    old_version: str,
) -> None:
    """Move current DNA .md/.json to _archive/ before generating new version."""
    archive = _archive_dir(knowledge_dir)
    archive.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for ext in ("md", "json"):
        src = knowledge_dir / f"{dna_filename}.{ext}"
        if src.exists():
            dst = archive / f"{dna_filename}_v{old_version}_{timestamp}.{ext}"
            shutil.move(str(src), str(dst))


def bump_version(old_version: str) -> str:
    """Increment minor version: '1.0' → '1.1', '1.9' → '1.10'."""
    parts = old_version.split(".")
    if len(parts) == 2:
        try:
            major, minor = int(parts[0]), int(parts[1])
            return f"{major}.{minor + 1}"
        except ValueError:
            pass
    return old_version + ".1"
