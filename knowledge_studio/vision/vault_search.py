from __future__ import annotations

"""Vault search: full-text search across DNA files in a project's knowledge dir."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.parent.parent


@dataclass
class SearchHit:
    subject: str
    file: str
    line_number: int
    line: str
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)


def _knowledge_dir(project: str) -> Path:
    return BASE_DIR / "data" / "projects" / project / "knowledge"


def _dna_files(knowledge_dir: Path, subject: Optional[str], compact: bool) -> list[tuple[str, Path]]:
    """Return (subject_name, path) pairs for matching DNA files."""
    suffix = "_COMPACT.md" if compact else "_DNA.md"
    results = []
    for p in sorted(knowledge_dir.glob("*.md")):
        if not p.name.endswith(suffix):
            continue
        if subject:
            # match if subject appears in filename (case-insensitive)
            if subject.upper() not in p.stem.upper():
                continue
        # derive subject name from filename: PROJECT_SUBJECT_DNA[_COMPACT]
        stem = p.stem  # e.g. VENHO_HOTEL_LAKE_VIEW_ROOM_DNA or ..._DNA_COMPACT
        for marker in ("_DNA_COMPACT", "_DNA"):
            if stem.endswith(marker):
                stem = stem[: -len(marker)]
                break
        results.append((stem, p))
    return results


def search(
    query: str,
    project: str = "venho_hotel",
    subject: Optional[str] = None,
    compact: bool = False,
    context_lines: int = 2,
    max_hits: int = 50,
) -> list[SearchHit]:
    """Search DNA files for query string. Returns list of SearchHit."""
    knowledge_dir = _knowledge_dir(project)
    if not knowledge_dir.is_dir():
        raise FileNotFoundError(f"Knowledge directory not found: {knowledge_dir}")

    pattern = re.compile(re.escape(query), re.IGNORECASE)
    hits: list[SearchHit] = []

    for subject_name, path in _dna_files(knowledge_dir, subject, compact):
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if pattern.search(line):
                before = lines[max(0, i - context_lines): i]
                after = lines[i + 1: i + 1 + context_lines]
                hits.append(SearchHit(
                    subject=subject_name,
                    file=path.name,
                    line_number=i + 1,
                    line=line,
                    context_before=before,
                    context_after=after,
                ))
                if len(hits) >= max_hits:
                    return hits

    return hits


def format_results(hits: list[SearchHit], query: str) -> str:
    """Format search hits for terminal display."""
    if not hits:
        return f'No results for "{query}"'

    lines = [f'Search results for "{query}" — {len(hits)} hit(s)\n']
    current_file = None

    for hit in hits:
        if hit.file != current_file:
            lines.append(f"\n{'─' * 60}")
            lines.append(f"  {hit.subject}  ({hit.file})")
            lines.append(f"{'─' * 60}")
            current_file = hit.file

        lines.append(f"  Line {hit.line_number:>4}:")
        for l in hit.context_before:
            lines.append(f"           {l}")
        lines.append(f"  >>>      {hit.line}")
        for l in hit.context_after:
            lines.append(f"           {l}")
        lines.append("")

    return "\n".join(lines)
