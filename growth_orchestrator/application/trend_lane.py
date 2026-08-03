from __future__ import annotations


def trend_lane_cutoff_state(*, candidate_selected: bool, final_approved: bool) -> str:
    if not candidate_selected:
        return "fallback_regular_queue"
    if not final_approved:
        return "fallback_regular_queue"
    return "ready_for_saturday_dispatch"
