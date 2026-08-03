from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from knowledge_studio.facts.fact_store import FactStore


def detect_stale_facts(project: str = "venho_hotel", data_root: Path = Path("data/projects"), today: date | None = None) -> list[str]:
    now = today or date.today()
    store = FactStore(project=project, data_root=data_root)
    expired: list[str] = []
    for fact in store.list_all():
        valid_to = fact.get("valid_to")
        if fact.get("status") == "approved" and valid_to and datetime.fromisoformat(valid_to).date() < now:
            fact["status"] = "expired"
            store.save(fact, overwrite=True)
            expired.append(fact["fact_key"])
    return expired


def revoke_approvals_for_expired_facts(approvals: list[dict], expired_fact_keys: list[str]) -> list[dict]:
    expired = set(expired_fact_keys)
    revoked: list[dict] = []
    for approval in approvals:
        referenced = set(approval.get("fact_keys", []))
        if approval.get("status") == "approved" and referenced & expired:
            revoked.append({**approval, "status": "revoked", "revoked_reason": "referenced_fact_expired"})
        else:
            revoked.append(approval)
    return revoked
