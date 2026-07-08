"""Overlay Merge — v2.4 §5.2.

Applies a curated overrides.yaml to a machine-generated DNA object at render time.
The overlay is written by humans and survives DNA regeneration unchanged.

Resolution rule (§6): only one location — config/projects/<project>/subjects/<subject>.overrides.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from knowledge_studio.vision.schemas.base import (
    BaseDNA,
    AllowedImperfection,
    ForbiddenRule,
)

BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"


def overlay_path(project: str, subject: str) -> Path:
    return CONFIG_DIR / "projects" / project / "subjects" / f"{subject}.overrides.yaml"


def load_overlay(project: str, subject: str) -> Optional[dict]:
    """Load overrides.yaml for (project, subject). Returns None if file does not exist."""
    path = overlay_path(project, subject)
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def apply_overlay(dna: BaseDNA, overlay: Optional[dict]) -> BaseDNA:
    """Merge overlay into DNA. Returns updated DNA object.

    Merge rules (§5.2):
    - forbidden:             curated rules prepend observed rules; each rule tagged with source
    - wording_overrides:     replace invariant value with curated wording (key must exist)
    - allowed_imperfections: curated entries prepend observed entries
    - notes → curator_notes: append to curator_notes list

    Does not touch: invariant classification, variable, evidence, source_images.
    """
    if not overlay:
        return dna

    data = dna.model_dump()

    # --- forbidden: curated first, observed second (dedup: drop observed if covered by curated) ---
    curated_rules_lower = {r.strip().lower() for r in overlay.get("forbidden", [])}
    curated_forbidden = [
        {"rule": r, "source": "curated"}
        for r in overlay.get("forbidden", [])
    ]
    observed_forbidden = [
        f for f in data["forbidden"]
        if f["source"] == "observed" and f["rule"].strip().lower() not in curated_rules_lower
    ]
    data["forbidden"] = curated_forbidden + observed_forbidden

    # --- wording_overrides: replace invariant value, mark value_source = "curated" ---
    wording = overlay.get("wording_overrides", {})
    if wording:
        for feat in data["invariant"]:
            if feat["key"] in wording:
                feat["value"] = wording[feat["key"]]
                feat["value_source"] = "curated"

    # --- allowed_imperfections: curated first, observed second ---
    # Only preserve "observed" entries from existing data; curated entries come from overlay fresh
    curated_ai_values_lower = {v.strip().lower() for v in overlay.get("allowed_imperfections", [])}
    curated_ai = [
        {"value": v, "source": "curated"}
        for v in overlay.get("allowed_imperfections", [])
    ]
    observed_ai = [
        ai for ai in data.get("allowed_imperfections", [])
        if ai.get("source") == "observed" and ai.get("value", "").strip().lower() not in curated_ai_values_lower
    ]
    data["allowed_imperfections"] = curated_ai + observed_ai

    # --- curator_notes: always replace with fresh overlay notes (idempotent) ---
    data["curator_notes"] = list(overlay.get("notes", []))

    return dna.__class__.model_validate(data)
