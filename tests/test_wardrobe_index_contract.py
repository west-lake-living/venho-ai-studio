"""Wardrobe index contract regressions for dashboard outfit visibility."""

from __future__ import annotations

import json
from pathlib import Path


WARDROBE_INDEX = Path("config/projects/linh_an/wardrobe_index.json")


def _load_index() -> dict:
    return json.loads(WARDROBE_INDEX.read_text(encoding="utf-8"))


def test_wardrobe_index_keeps_baseline_non_sport_families_visible() -> None:
    index = _load_index()
    families = {family["family_key"]: family for family in index["families"]}
    outfits = {outfit["outfit_id"]: outfit for outfit in index["outfits"]}

    expected_defaults = {
        "cafe_girl": "cafe_girl_classic",
        "west_lake_sunset": "west_lake_sunset_classic",
        "street_style": "street_style_classic",
        "business_travel": "business_travel_classic",
        "sport_active": "mint_green",
    }

    assert expected_defaults.keys() <= families.keys()
    for family_key, outfit_id in expected_defaults.items():
        assert families[family_key]["default_outfit_id"] == outfit_id
        assert outfit_id in families[family_key]["outfit_ids"]
        assert outfits[outfit_id]["family_key"] == family_key
        assert outfits[outfit_id]["status"] == "approved"


def test_wardrobe_index_outfit_ids_are_unique_for_contract_refs() -> None:
    index = _load_index()
    outfit_ids = [outfit["outfit_id"] for outfit in index["outfits"]]

    assert len(outfit_ids) == len(set(outfit_ids))


def test_manual_seed_outfits_do_not_require_upload_images() -> None:
    index = _load_index()

    for outfit in index["outfits"]:
        if outfit["source_kind"] == "manual_seed":
            assert outfit["source_images_dir"] is None
