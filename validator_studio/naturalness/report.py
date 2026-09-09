from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


ViolationSeverity = Literal["warning", "error"]


@dataclass(frozen=True)
class Violation:
    """One explainable gate finding.

    ``excerpt`` is intentionally short and is safe to surface to the writer;
    the full draft remains owned by the content package.
    """

    rule_id: str
    message: str
    excerpt: str = ""
    suggestion: str = ""
    severity: ViolationSeverity = "error"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class NaturalnessReport:
    verdict: Literal["PASS", "REWRITE", "ESCALATE_HUMAN"]
    violations: list[Violation]
    specificity_score: float
    rewrite_round: int = 0
    voice_distance: float | None = None

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "violations": [item.to_dict() for item in self.violations],
            "specificity_score": self.specificity_score,
            "rewrite_round": self.rewrite_round,
            "voice_distance": self.voice_distance,
        }
