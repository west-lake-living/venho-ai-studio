from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime

from knowledge_studio.facts.fact_resolver import FactResolver


def brief_checksum(brief: dict) -> str:
    payload = {key: value for key, value in brief.items() if key != "checksum"}
    return "sha256:" + hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def validate_brief_facts(brief: dict, resolver: FactResolver) -> list[str]:
    missing: list[str] = []
    for proof in brief.get("proof_points", []):
        fact_key = proof.get("fact_key")
        if not fact_key or not resolver.resolve(fact_key):
            missing.append(fact_key or "<missing>")
    return missing


def lock_brief(brief: dict, *, approved_by: str, resolver: FactResolver | None = None) -> dict:
    fact_resolver = resolver or FactResolver()
    missing = validate_brief_facts(brief, fact_resolver)
    if missing:
        raise ValueError(f"Brief proof points missing active R3 facts: {', '.join(missing)}")
    locked = deepcopy(brief)
    locked["status"] = "LOCKED"
    locked["locked_by"] = approved_by
    locked["locked_at"] = datetime.now().isoformat()
    locked["checksum"] = brief_checksum(locked)
    return locked


def supersede_locked_brief(brief: dict, patch: dict) -> dict:
    if brief.get("status") != "LOCKED":
        raise ValueError("Only LOCKED briefs can be superseded")
    new_brief = {**brief, **patch}
    new_brief["version"] = int(brief.get("version", 1)) + 1
    new_brief["status"] = "DRAFT"
    new_brief.pop("locked_by", None)
    new_brief.pop("locked_at", None)
    new_brief["supersedes"] = brief["id"]
    new_brief["checksum"] = brief_checksum(new_brief)
    return new_brief
