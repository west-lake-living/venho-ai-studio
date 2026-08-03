from __future__ import annotations

from dataclasses import dataclass


STAGES = ["shadow", "pilot_25", "pilot_50", "pilot_100"]


@dataclass(frozen=True)
class RolloutDecision:
    current_stage: str
    next_stage: str
    allowed: bool
    reason: str | None = None
    human_approval_required: bool = True


def next_rollout_stage(current_stage: str, *, scorecard_passed: bool, has_90_day_metrics: bool, lane: str = "standard") -> RolloutDecision:
    if lane == "trend" and current_stage == "pilot_100":
        return RolloutDecision(current_stage, current_stage, False, "trend_lane_never_auto_approves")
    if current_stage not in STAGES:
        raise ValueError(f"unknown rollout stage: {current_stage}")
    if not scorecard_passed:
        return RolloutDecision(current_stage, current_stage, False, "scorecard_not_passed")
    if current_stage == "pilot_50" and not has_90_day_metrics:
        return RolloutDecision(current_stage, current_stage, False, "requires_90_day_metrics")
    index = STAGES.index(current_stage)
    next_stage = STAGES[min(index + 1, len(STAGES) - 1)]
    return RolloutDecision(current_stage, next_stage, True)


def rollback_sequence(*, disable_dispatch_done: bool, approved_artifacts_mutated: bool = False) -> dict:
    if not disable_dispatch_done:
        raise ValueError("disable dispatch before rollback approval or validation")
    if approved_artifacts_mutated:
        raise ValueError("approved artifacts are immutable")
    return {
        "steps": ["disable_dispatch", "freeze_new_approvals", "rollback_flags", "export_git_recovery_bundle"],
        "forward_only_migration": True,
        "compatible_reads_required": True,
    }
