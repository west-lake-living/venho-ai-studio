from __future__ import annotations

import uuid
from typing import Optional

from growth_orchestrator.bridges.m03_validator_bridge import M03ValidatorBridge
from growth_orchestrator.bridges.m05_content_bridge import M05ContentBridge


def run_content_pipeline(
    brief: dict,
    *,
    content_bridge: Optional[M05ContentBridge] = None,
    validator_bridge: Optional[M03ValidatorBridge] = None,
) -> dict:
    if brief.get("status") != "LOCKED":
        raise ValueError("Only LOCKED briefs can generate final packages")
    package_id = str(uuid.uuid4())
    candidates = (content_bridge or M05ContentBridge()).generate_candidates(brief)
    selected = candidates[0]
    validation = (validator_bridge or M03ValidatorBridge()).validate_package(brief, selected)
    state = "READY_FOR_REVIEW" if validation["verdict"] == "READY_FOR_REVIEW" else validation["verdict"]
    return {
        "id": package_id,
        "brand_id": brief["brand_id"],
        "campaign_id": brief["campaign_id"],
        "creative_brief_id": brief["id"],
        "state": state,
        "copy_candidates": candidates,
        "selected_copy_candidate_id": selected["id"],
        "validation": validation,
    }
