from __future__ import annotations


def compile_brief_from_campaign(campaign: dict, insights: list[dict]) -> dict:
    proof_points = campaign.get("proof_points", [])
    context_refs = [
        {"rs_id": item["rs_id"], "evidence_level": item["evidence_level"], "role": item.get("role", "context")}
        for item in insights
        if item.get("evidence_level") in {"R2", "R2-T"}
    ]
    return {
        "schema_version": "1.0",
        "id": campaign["brief_id"],
        "version": 1,
        "brand_id": campaign.get("brand_id", "venho-hotel"),
        "campaign_id": campaign["id"],
        "objective": campaign.get("objective", "qualified_inquiry"),
        "primary_metric": campaign.get("primary_metric", "qualified_dm_rate"),
        "platforms": campaign.get("platforms", ["facebook", "instagram"]),
        "audience_segment": campaign.get("audience_segment", "couple"),
        "funnel_stage": campaign.get("funnel_stage", "consideration"),
        "single_minded_message": campaign["message"],
        "proof_points": proof_points,
        "context_refs": context_refs,
        "cta": campaign.get("cta", {"type": "booking_link", "destination_key": "hotel.website", "strength": "soft"}),
        "visual": campaign["visual"],
        "lane": campaign.get("lane", "daily"),
        "status": "DRAFT",
        "checksum": "",
    }
