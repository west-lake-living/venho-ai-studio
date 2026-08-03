from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from knowledge_studio.facts.fact_resolver import FactResolver


@dataclass(frozen=True)
class ClaimCheck:
    claim: str
    fact_key: str | None
    status: str
    evidence_version: int | None = None


class ClaimValidator:
    def __init__(self, project: str = "venho_hotel", data_root: Path = Path("data/projects")) -> None:
        self.resolver = FactResolver(project=project, data_root=data_root)

    def validate(self, claims: list[dict[str, str]]) -> dict:
        checks: list[ClaimCheck] = []
        kill_switches: list[str] = []
        for item in claims:
            claim = item.get("text", "")
            fact_key = item.get("fact_key")
            if not fact_key:
                checks.append(ClaimCheck(claim, None, "UNSUPPORTED"))
                kill_switches.append("unsupported_critical_claim")
                continue
            raw_fact = self.resolver.store.get(fact_key)
            if not raw_fact:
                checks.append(ClaimCheck(claim, fact_key, "UNSUPPORTED"))
                kill_switches.append("unsupported_critical_claim")
                continue
            fact = self.resolver.resolve(fact_key)
            if not fact:
                checks.append(ClaimCheck(claim, fact_key, "EXPIRED"))
                kill_switches.append("unsupported_critical_claim")
                continue
            checks.append(ClaimCheck(claim, fact_key, "VERIFIED", int(fact.get("version", 1))))
        return {
            "validator": "claim_validator",
            "status": "completed",
            "verdict": "NEEDS_REVISION" if kill_switches else "READY_FOR_REVIEW",
            "kill_switches": sorted(set(kill_switches)),
            "checks": [check.__dict__ for check in checks],
        }
