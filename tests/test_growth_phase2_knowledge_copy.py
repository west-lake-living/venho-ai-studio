from __future__ import annotations

from pathlib import Path

import pytest

from agent_studio.growth.brief_compiler import compile_brief_from_campaign
from agent_studio.growth.brief_lifecycle import lock_brief, supersede_locked_brief
from content_studio.generators.candidate_generator import generate_and_select_candidate, generate_three_candidates
from knowledge_studio.facts.fact_resolver import FactResolver
from knowledge_studio.facts.fact_store import FactStore
from validator_studio.claim_validator import ClaimValidator


ROOT = Path(__file__).resolve().parents[1]


def seed_facts(tmp_path) -> FactResolver:
    store = FactStore(data_root=tmp_path / "data")
    store.load_seed_facts(ROOT / "config/projects/venho_hotel/growth/seed_facts.json")
    return FactResolver(data_root=tmp_path / "data")


def campaign() -> dict:
    return {
        "id": "campaign-001",
        "brief_id": "brief-001",
        "message": "Một khách sạn boutique nhỏ cạnh Hồ Tây.",
        "proof_points": [{"text": "12 phòng boutique", "fact_key": "hotel.room_count"}],
        "visual": {"scenario_key": "venho_rooftop_sunrise", "required_entities": ["west_lake"], "target_formats": ["feed_4_5"]},
    }


def test_seed_facts_resolve_active_r3_values(tmp_path) -> None:
    resolver = seed_facts(tmp_path)
    assert resolver.resolve("hotel.room_count")["value"] == 12
    assert resolver.resolve("hotel.address")["value"].startswith("181 Nguyen Dinh Thi")
    assert resolver.resolve("review.agoda_overall")["value"] == "8.5/10"


def test_claim_validator_blocks_unsupported_price_policy_review_distance(tmp_path) -> None:
    seed_facts(tmp_path)
    validator = ClaimValidator(data_root=tmp_path / "data")
    claims = [
        {"text": "Phòng từ 400,000 VND", "fact_key": "offer.price_from"},
        {"text": "Trẻ em dưới 9 tuổi miễn phí", "fact_key": "hotel.policy.children"},
        {"text": "Agoda 8.5/10", "fact_key": "review.agoda_overall"},
        {"text": "Cách công viên nước 1.2km", "fact_key": "venue.distance.waterpark"},
    ]
    report = validator.validate(claims)
    statuses = {item["fact_key"]: item["status"] for item in report["checks"]}
    assert statuses["review.agoda_overall"] == "VERIFIED"
    assert statuses["offer.price_from"] in {"UNSUPPORTED", "EXPIRED"}
    assert statuses["hotel.policy.children"] in {"UNSUPPORTED", "EXPIRED"}
    assert statuses["venue.distance.waterpark"] in {"UNSUPPORTED", "EXPIRED"}
    assert report["verdict"] == "NEEDS_REVISION"


def test_harry_can_lock_brief_before_paid_generation(tmp_path) -> None:
    resolver = seed_facts(tmp_path)
    brief = compile_brief_from_campaign(campaign(), insights=[{"rs_id": "RS-2026-08-0014", "evidence_level": "R2", "role": "guest_voice"}])
    locked = lock_brief(brief, approved_by="harry", resolver=resolver)
    assert locked["status"] == "LOCKED"
    assert locked["locked_by"] == "harry"
    assert locked["checksum"].startswith("sha256:")


def test_brief_with_missing_fact_cannot_lock(tmp_path) -> None:
    resolver = seed_facts(tmp_path)
    bad = campaign()
    bad["proof_points"] = [{"text": "Phòng từ 400,000 VND", "fact_key": "offer.price_from"}]
    brief = compile_brief_from_campaign(bad, insights=[])
    with pytest.raises(ValueError):
        lock_brief(brief, approved_by="harry", resolver=resolver)


def test_locked_brief_generates_three_candidates_and_selects_one(tmp_path) -> None:
    resolver = seed_facts(tmp_path)
    locked = lock_brief(compile_brief_from_campaign(campaign(), insights=[]), approved_by="harry", resolver=resolver)
    candidates = generate_three_candidates(locked)
    assert {item["angle_type"] for item in candidates} == {"emotional", "practical", "proof_led"}
    selected = generate_and_select_candidate(locked)
    assert selected["rubric"]["total"] >= 8.0
    assert selected["claims"][0]["fact_key"] == "hotel.room_count"


def test_edit_after_lock_supersedes_and_requires_new_approval(tmp_path) -> None:
    resolver = seed_facts(tmp_path)
    locked = lock_brief(compile_brief_from_campaign(campaign(), insights=[]), approved_by="harry", resolver=resolver)
    draft = supersede_locked_brief(locked, {"single_minded_message": "Thông điệp mới"})
    assert draft["status"] == "DRAFT"
    assert draft["version"] == 2
    assert "locked_by" not in draft
