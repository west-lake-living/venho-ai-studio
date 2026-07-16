from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class OutfitContractRef(BaseModel):
    outfit_id: str
    family_key: str
    display_label: str
    status: Literal["draft", "needs_review", "approved", "quarantined"]
    schema_subject: str
    source_kind: str
    source_images_dir: Optional[str] = None
    dna_artifacts: List[str] = Field(default_factory=list)
    description: str
    selection_reason: str = "user_selection"


class ScenarioProfileRef(BaseModel):
    scenario_id: str
    scenario_label: str
    dna_subject: Optional[str] = None
    environment_ref: Optional[str] = None


class ContractRefs(BaseModel):
    character_id: Optional[str] = None
    outfit: Optional[OutfitContractRef] = None
    scenario_profile: Optional[ScenarioProfileRef] = None


def load_wardrobe_index(config_root: Path = Path("config")) -> dict:
    path = config_root / "projects" / "linh_an" / "wardrobe_index.json"
    if not path.exists():
        return {"families": [], "outfits": []}
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_outfit_ref(
    outfit_id: Optional[str],
    *,
    family_key: str = "sport_active",
    selection_reason: str = "user_selection",
    config_root: Path = Path("config"),
) -> Optional[OutfitContractRef]:
    if not outfit_id:
        return None
    index = load_wardrobe_index(config_root)
    outfit = next((item for item in index.get("outfits", []) if item.get("outfit_id") == outfit_id), None)
    if not outfit:
        raise ValueError(f"Unknown outfit_id: {outfit_id}")
    if outfit.get("status") == "quarantined":
        raise ValueError(f"Outfit is quarantined: {outfit_id}")
    family = next((item for item in index.get("families", []) if item.get("family_key") == outfit.get("family_key")), {})
    return OutfitContractRef(
        outfit_id=outfit["outfit_id"],
        family_key=outfit.get("family_key", family_key),
        display_label=outfit.get("display_label", outfit["outfit_id"]),
        status=outfit.get("status", "draft"),
        schema_subject=outfit.get("schema_subject", ""),
        source_kind=outfit.get("source_kind", "unknown"),
        source_images_dir=outfit.get("source_images_dir"),
        dna_artifacts=list(outfit.get("dna_artifacts", [])),
        description=outfit.get("description", ""),
        selection_reason=selection_reason,
    )


def contract_refs_dump(refs: Optional[ContractRefs]) -> Dict[str, object]:
    return refs.model_dump(mode="json", exclude_none=True) if refs else {}
