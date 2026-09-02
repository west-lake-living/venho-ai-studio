"""Case-scoped authoritative Candidate v3 runtime parameter bindings."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from ..errors import RestorationError
from ..value_objects import RestorationParams


R2_WINNING_CONFIG_ID = "candidate-v3-r2-b05-winning-config-v1"
R2_WINNING_CONFIG_SOURCE = (
    "artifacts/identity-restoration/phase7-candidate-v3/"
    "r2-b05-face-local-focused-recovery-20260902T080000Z/"
    "winner_selection.json"
)
R2_WINNING_CONFIG = {
    "caseId": "B05",
    "denoise": 0.35,
    "cfg": 6.1,
    "steps": 21,
    "sampler": "euler",
    "scheduler": "normal",
    "configId": R2_WINNING_CONFIG_ID,
    "source": R2_WINNING_CONFIG_SOURCE,
}
R2_WINNING_CONFIG_SHA256 = hashlib.sha256(
    json.dumps(R2_WINNING_CONFIG, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
KNOWN_CANDIDATE_V3_CASE_IDS = frozenset({f"B{number:02d}" for number in range(1, 10)})


@dataclass(frozen=True)
class CandidateV3ParameterResolution:
    params: RestorationParams
    source: str
    config_id: str | None = None
    config_sha256: str | None = None


def resolve_candidate_v3_params(*, case_id: str | None, requested: RestorationParams) -> CandidateV3ParameterResolution:
    """Resolve the only authorized case-specific pin before graph binding.

    A supplied Candidate v3 case identifier must be from the frozen benchmark
    authority set.  B05 is always resolved to its R2 winner, never merged with
    caller values; absent case authority preserves the existing caller path.
    """
    if case_id is None:
        return CandidateV3ParameterResolution(params=requested, source="CALLER_REQUEST")
    if case_id not in KNOWN_CANDIDATE_V3_CASE_IDS:
        raise RestorationError(
            "ERR_CANDIDATE_V3_CASE_AUTHORITY_INVALID",
            f"unknown Candidate v3 case authority {case_id!r}",
            retryable=False,
        )
    if case_id != "B05":
        return CandidateV3ParameterResolution(params=requested, source="CALLER_REQUEST")
    return CandidateV3ParameterResolution(
        params=RestorationParams(
            denoise=0.35, steps=21, cfg=6.1, sampler="euler", scheduler="normal"
        ),
        source="R2_WINNING_CONFIG",
        config_id=R2_WINNING_CONFIG_ID,
        config_sha256=R2_WINNING_CONFIG_SHA256,
    )
