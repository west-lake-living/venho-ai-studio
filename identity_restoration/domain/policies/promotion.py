from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn

from .pixel_preservation import PixelLockReport

# BẤT BIẾN — wraps VENHO's locked rule. No code path in this module creates
# "official". Full-gate pass means the machine gate was cleared; it is not
# human approval.


@dataclass(frozen=True)
class QcResult:
    face_score: float
    all_validators_approved: bool
    kill_switch_triggered: bool
    source_authority: dict[str, object] | None = None


def is_full_gate_pass(qc: QcResult, pixel: PixelLockReport, *, face_qc_min: float) -> bool:
    """``face_qc_min`` is injected from Character Bible 07F, never hardcoded here (GW-D12)."""
    return (
        (qc.source_authority is None or qc.source_authority.get("qualityAcceptanceEligible") is not False)
        and qc.face_score >= face_qc_min
        and qc.all_validators_approved
        and not qc.kill_switch_triggered
        and pixel.passed
    )


def is_official(*_args: object, **_kwargs: object) -> NoReturn:
    raise NotImplementedError(
        "Official promotion is a human action. No code path in this module is allowed to create it."
    )
