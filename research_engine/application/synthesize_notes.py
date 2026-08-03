from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from research_engine.adapters.vault_reader import VaultReader
from shared.security import ensure_safe_slug


def synthesize_notes(
    *,
    rs_id: str,
    domain: str,
    question: str,
    source_paths: list[Path],
    vault_root: Path = Path("research"),
    expiry_days: int = 90,
) -> Path:
    if not question.strip():
        raise ValueError("Research starts with one written question")
    claims = []
    reader = VaultReader(vault_root)
    for path in source_paths:
        claims.append(f"- Source: {path}")
    body = f"# {question.strip()}\n\n" + "\n".join(claims)
    frontmatter = {
        "rs_id": rs_id,
        "type": "synthesis",
        "domain": domain,
        "evidence_level": "R2",
        "status": "draft",
        "collected_at": date.today().isoformat(),
        "source_uri": None,
        "confidence": 0.8,
        "expires_at": (date.today() + timedelta(days=expiry_days)).isoformat(),
        "promoted_fact_keys": [],
        "related_briefs": [],
        "verified_by_human": False,
        "tags": [],
    }
    return reader.write_note(Path("synthesis") / f"{ensure_safe_slug(rs_id, field='rs_id')}.md", frontmatter, body)
