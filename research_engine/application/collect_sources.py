from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from research_engine.adapters.vault_reader import VaultReader
from shared.security import ensure_safe_slug


def collect_source_note(
    *,
    rs_id: str,
    domain: str,
    source_uri: str,
    title: str,
    body: str,
    vault_root: Path = Path("research"),
) -> Path:
    frontmatter = {
        "rs_id": rs_id,
        "type": "source",
        "domain": domain,
        "evidence_level": "R0",
        "status": "draft",
        "collected_at": date.today().isoformat(),
        "source_uri": source_uri,
        "confidence": 0.0,
        "expires_at": (date.today() + timedelta(days=180)).isoformat(),
        "promoted_fact_keys": [],
        "related_briefs": [],
        "verified_by_human": False,
        "tags": [],
    }
    safe_domain = ensure_safe_slug(domain, field="domain")
    safe_rs_id = ensure_safe_slug(rs_id, field="rs_id")
    safe_title = ensure_safe_slug(title, field="title")
    return VaultReader(vault_root).write_note(Path("sources") / safe_domain / f"{safe_rs_id}_{safe_title}.md", frontmatter, body)


def collect_structured_note(
    *,
    rs_id: str,
    domain: str,
    source_uri: str,
    title: str,
    observations: list[str],
    vault_root: Path = Path("research"),
) -> Path:
    frontmatter = {
        "rs_id": rs_id,
        "type": "note",
        "domain": domain,
        "evidence_level": "R1",
        "status": "draft",
        "collected_at": date.today().isoformat(),
        "source_uri": source_uri,
        "confidence": 0.6,
        "expires_at": (date.today() + timedelta(days=180)).isoformat(),
        "promoted_fact_keys": [],
        "related_briefs": [],
        "verified_by_human": False,
        "tags": [],
    }
    body = "\n".join(f"- {item}" for item in observations)
    safe_domain = ensure_safe_slug(domain, field="domain")
    safe_rs_id = ensure_safe_slug(rs_id, field="rs_id")
    safe_title = ensure_safe_slug(title, field="title")
    return VaultReader(vault_root).write_note(Path("notes") / safe_domain / f"{safe_rs_id}_{safe_title}.md", frontmatter, body)
