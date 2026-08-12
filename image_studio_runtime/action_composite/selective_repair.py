from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List


RETRY_CAPS = {"scene": 3, "face": 5, "boundary": 3, "region": 3}


@dataclass
class RepairDecision:
    region: str
    repair_type: str
    attempt: int
    allowed: bool
    reason: str


@dataclass
class SelectiveRepairController:
    """Routes only failed regions to repair and stops at documented retry caps."""

    retry_caps: Dict[str, int] = field(default_factory=lambda: dict(RETRY_CAPS))
    attempts: Dict[str, int] = field(default_factory=dict)

    def choose(self, failed_regions: Iterable[str]) -> List[RepairDecision]:
        """Consumes one retry budget per routed region; not a pure query."""
        decisions: List[RepairDecision] = []
        default_cap = self.retry_caps.get("region", RETRY_CAPS["region"])
        for region in dict.fromkeys(failed_regions):
            repair_type = self._repair_type(region)
            attempt = self.attempts.get(repair_type, 0) + 1
            cap = self.retry_caps.get(repair_type, default_cap)
            allowed = attempt <= cap
            if allowed:
                self.attempts[repair_type] = attempt
            decisions.append(RepairDecision(region=region, repair_type=repair_type, attempt=attempt,
                                            allowed=allowed,
                                            reason="within_retry_cap" if allowed else "retry_cap_exceeded"))
        return decisions

    def execute(self, failed_regions: Iterable[str], repair: Callable[[str], object]) -> List[object]:
        outputs: List[object] = []
        for decision in self.choose(failed_regions):
            if decision.allowed:
                outputs.append(repair(decision.region))
        return outputs

    @staticmethod
    def _repair_type(region: str) -> str:
        name = region.lower()
        if "face" in name or "identity" in name or "geometry" in name:
            return "face"
        if "boundary" in name or "seam" in name:
            return "boundary"
        if name in {"scene", "global", "composition"}:
            return "scene"
        return "region"
