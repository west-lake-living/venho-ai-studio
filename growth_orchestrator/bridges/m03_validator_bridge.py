from __future__ import annotations

from validator_studio.alignment_validator import validate_alignment
from validator_studio.claim_validator import ClaimValidator


class M03ValidatorBridge:
    def validate_package(self, brief: dict, copy_candidate: dict) -> dict:
        claim_report = ClaimValidator().validate([{"text": c, "fact_key": None} if isinstance(c, str) else c for c in copy_candidate.get("claims", [])])
        alignment_report = validate_alignment(brief, copy_candidate.get("scene_summary", {}))
        verdict = "READY_FOR_REVIEW"
        if "UNVALIDATED" in {claim_report["verdict"], alignment_report["verdict"]}:
            verdict = "UNVALIDATED"
        elif claim_report["kill_switches"] or alignment_report["kill_switches"]:
            verdict = "NEEDS_REVISION"
        return {"verdict": verdict, "reports": [claim_report, alignment_report]}
