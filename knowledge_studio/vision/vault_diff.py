from __future__ import annotations

"""Vault diff: compare DNA versions for a subject."""

import difflib
import re
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.parent.parent


def _knowledge_dir(project: str) -> Path:
    return BASE_DIR / "data" / "projects" / project / "knowledge"


def _dna_filename(project: str, subject: str) -> str:
    return f"{project.upper()}_{subject.upper()}_DNA"


def list_versions(project: str, subject: str) -> list[dict]:
    """Return available archived versions for a subject, newest first.

    Each entry: {"version": "1.0", "timestamp": "20260707_162912", "path": Path}
    """
    knowledge_dir = _knowledge_dir(project)
    archive_dir = knowledge_dir / "_archive"
    if not archive_dir.is_dir():
        return []

    prefix = _dna_filename(project, subject)
    # Pattern: PREFIX_v{version}_{timestamp}.md
    pattern = re.compile(
        rf"^{re.escape(prefix)}_v(?P<version>[0-9.]+)_(?P<ts>\d{{8}}_\d{{6}})\.md$"
    )
    versions = []
    for p in archive_dir.glob("*.md"):
        m = pattern.match(p.name)
        if m:
            versions.append({
                "version": m.group("version"),
                "timestamp": m.group("ts"),
                "path": p,
            })

    versions.sort(key=lambda x: x["timestamp"], reverse=True)
    return versions


def diff_versions(
    project: str,
    subject: str,
    from_version: Optional[str] = None,
    context: int = 3,
) -> str:
    """Unified diff between an archived version and current DNA.

    If from_version is None, diffs the most recent archive vs current.
    """
    knowledge_dir = _knowledge_dir(project)
    dna_filename = _dna_filename(project, subject)
    current_path = knowledge_dir / f"{dna_filename}.md"

    if not current_path.exists():
        raise FileNotFoundError(f"Current DNA not found: {current_path}")

    versions = list_versions(project, subject)
    if not versions:
        return f"No archived versions found for subject '{subject}'."

    if from_version:
        match = next((v for v in versions if v["version"] == from_version), None)
        if not match:
            available = ", ".join(v["version"] for v in versions)
            return f"Version {from_version!r} not found. Available: {available}"
        archive_entry = match
    else:
        archive_entry = versions[0]

    archive_text = archive_entry["path"].read_text(encoding="utf-8").splitlines(keepends=True)
    current_text = current_path.read_text(encoding="utf-8").splitlines(keepends=True)

    label_a = f"v{archive_entry['version']}  ({archive_entry['timestamp']})"
    label_b = "current"

    diff = list(difflib.unified_diff(
        archive_text,
        current_text,
        fromfile=label_a,
        tofile=label_b,
        n=context,
    ))

    if not diff:
        return f"No differences found between v{archive_entry['version']} and current."

    return "".join(diff)


def format_version_list(project: str, subject: str) -> str:
    """Human-readable list of archived versions."""
    versions = list_versions(project, subject)
    if not versions:
        return f"No archived versions for subject '{subject}'."

    lines = [f"Archived versions for '{subject}' (project: {project}):\n"]
    for v in versions:
        ts = v["timestamp"]
        date_str = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[9:11]}:{ts[11:13]}:{ts[13:15]}"
        lines.append(f"  v{v['version']}  —  {date_str}")
    return "\n".join(lines)
