from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from automation_studio.types import StepResult

BASE_DIR = Path(__file__).resolve().parents[2]


def _safe_id(value: str) -> str:
    if not value or not all(ch.isalnum() or ch in {"_", "-"} for ch in value):
        raise ValueError(f"Invalid outfit_id: {value}")
    return value


def _review_path(outfit_id: str) -> Path:
    return BASE_DIR / "data" / "projects" / "linh_an" / "wardrobe_ingest" / f"{outfit_id}_review.json"


def _index_path() -> Path:
    return BASE_DIR / "config" / "projects" / "linh_an" / "wardrobe_index.json"


def wardrobe_ingest(
    outfit_id: str,
    source_dir: str,
    schema_subject: str,
    display_label: str,
    family_key: str = "sport_active",
    validation_status: str = "pass",
    description: str = "",
    settings: dict[str, Any] | None = None,
) -> StepResult:
    outfit_id = _safe_id(outfit_id)
    source = BASE_DIR / source_dir
    if not source.exists():
        raise FileNotFoundError(f"Wardrobe source_dir not found: {source_dir}")
    review = {
        "contract_version": "1.0",
        "outfit_id": outfit_id,
        "family_key": family_key,
        "schema_subject": schema_subject,
        "display_label": display_label,
        "source_dir": source_dir,
        "description": description,
        "validation_status": validation_status,
        "approved_for_index": False,
        "created_at": datetime.utcnow().isoformat(),
    }
    path = _review_path(outfit_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(review, indent=2, ensure_ascii=False), encoding="utf-8")
    if validation_status != "pass":
        return StepResult(
            status="failed",
            outputs=[path],
            data={"index_update_blocked": True, "review_file": str(path)},
            message="Validation failed; wardrobe index update blocked.",
        )
    return StepResult(
        status="manual_gate",
        outputs=[path],
        data={
            "message": f"Human review required before indexing outfit {outfit_id}.",
            "instructions": ["Open review_file", "Set approved_for_index=true only after visual/QC approval"],
            "next_actions": ["automation_studio.wardrobe_index_update"],
            "review_file": str(path),
        },
        message="Human review required before wardrobe index update.",
    )


def wardrobe_index_update(review_file: str, settings: dict[str, Any] | None = None) -> StepResult:
    path = Path(review_file)
    if not path.is_absolute():
        path = BASE_DIR / review_file
    review = json.loads(path.read_text(encoding="utf-8"))
    if review.get("validation_status") != "pass":
        raise ValueError("Validation did not pass; index update blocked.")
    if review.get("approved_for_index") is not True:
        raise ValueError("Human review not approved; index update blocked.")

    index_path = _index_path()
    index = json.loads(index_path.read_text(encoding="utf-8"))
    outfit = {
        "outfit_id": review["outfit_id"],
        "family_key": review["family_key"],
        "display_label": review["display_label"],
        "status": "approved",
        "schema_subject": review["schema_subject"],
        "source_kind": "source_backed",
        "source_images_dir": review["source_dir"],
        "dna_artifacts": [],
        "description": review.get("description", ""),
        "default": False,
    }
    outfits = [item for item in index.get("outfits", []) if item.get("outfit_id") != outfit["outfit_id"]]
    outfits.append(outfit)
    index["outfits"] = outfits
    for family in index.get("families", []):
        if family.get("family_key") == outfit["family_key"] and outfit["outfit_id"] not in family.get("outfit_ids", []):
            family["outfit_ids"].append(outfit["outfit_id"])
    index["updated_at"] = datetime.utcnow().date().isoformat()
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    return StepResult(status="success", outputs=[index_path], data={"indexed_outfit_id": outfit["outfit_id"]})
