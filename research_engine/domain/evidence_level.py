from __future__ import annotations

from enum import Enum


class EvidenceLevel(str, Enum):
    R0 = "R0"
    R1 = "R1"
    R2 = "R2"
    R2_T = "R2-T"
    R3 = "R3"
    R4 = "R4"

    @property
    def citable(self) -> bool:
        return self is EvidenceLevel.R3

    @property
    def requires_expiry(self) -> bool:
        return self in {EvidenceLevel.R2, EvidenceLevel.R2_T}


ALLOWED_TRANSITIONS = {
    EvidenceLevel.R0: {EvidenceLevel.R1},
    EvidenceLevel.R1: {EvidenceLevel.R2, EvidenceLevel.R2_T},
    EvidenceLevel.R2: {EvidenceLevel.R3},
    EvidenceLevel.R2_T: set(),
    EvidenceLevel.R3: {EvidenceLevel.R4},
    EvidenceLevel.R4: set(),
}


def can_transition(current: EvidenceLevel, target: EvidenceLevel, *, human_approved: bool = False) -> bool:
    if target not in ALLOWED_TRANSITIONS[current]:
        return False
    if target is EvidenceLevel.R3:
        return human_approved
    return True
