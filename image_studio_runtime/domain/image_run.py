from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


ImageRunState = Literal["QUEUED", "GENERATING", "GENERATED", "VALIDATING", "APPROVED", "NEEDS_REVIEW", "UNVALIDATED", "FAILED"]
ImageRunOperation = Literal["generate", "repair"]


class ImageRun(BaseModel):
    run_id: str
    content_package_id: str
    creative_brief_id: str
    operation: ImageRunOperation = "generate"
    attempt_index: int = 1
    paid: bool = False
    state: ImageRunState = "QUEUED"

    def transition(self, target: ImageRunState) -> "ImageRun":
        allowed = {
            "QUEUED": {"GENERATING", "FAILED"},
            "GENERATING": {"GENERATED", "FAILED"},
            "GENERATED": {"VALIDATING", "FAILED"},
            "VALIDATING": {"APPROVED", "NEEDS_REVIEW", "UNVALIDATED", "FAILED"},
            "APPROVED": set(),
            "NEEDS_REVIEW": set(),
            "UNVALIDATED": set(),
            "FAILED": set(),
        }
        if target not in allowed[self.state]:
            raise ValueError(f"Invalid ImageRun transition: {self.state} -> {target}")
        return self.model_copy(update={"state": target})


def enforce_paid_attempt_policy(existing_runs: list[ImageRun], *, operation: ImageRunOperation) -> None:
    paid_runs = [run for run in existing_runs if run.paid]
    generation_count = sum(1 for run in paid_runs if run.operation == "generate")
    repair_count = sum(1 for run in paid_runs if run.operation == "repair")
    if operation == "generate" and generation_count >= 1:
        raise ValueError("Paid image policy allows only one generation attempt")
    if operation == "repair" and (generation_count < 1 or repair_count >= 1):
        raise ValueError("Paid image policy allows one targeted repair after one generation")
