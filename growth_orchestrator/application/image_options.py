from __future__ import annotations

"""Image choices per post: A (AI, scenario matched to the topic), B (AI, a
different scene), C (a real hotel/lake photo from assets/raw). Harry picks one
on the Dashboard or uploads his own before Duyệt (2026-10-21).

Why: posts and photos did not match. Root cause was that no image had been
generated since 28/08 (see ops/asus-server/README.md), but even a working
generator drew the scene from the lane's rotation, not the topic -- "sương
sớm trên mặt hồ" got `venho_lobby_cozy`. Choosing among three, with the
default matched to the words of the topic, fixes both the miss rate and the
"AI picked the wrong scene" case without a second copy pass.
"""

import os
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Any, Optional

from PIL import Image

# Option B/C cost one more gpt-image-2 + vision QC call and one Drive upload
# per topic; enabled on the server runner, off in tests and local runs.
ALTERNATIVES_ENV = "GROWTH_IMAGE_ALTERNATIVES"

# Folded (accent-free) keywords -> scenario, places before times of day: a
# place word decides the scene ("sương sớm trên mặt hồ" is the lake, not the
# rooftop); a time word only decides when no place is named.
_ROOFTOP = ("rooftop", "san thuong")
_EVENING = ("hoang hon", "sunset", "chieu muon", "len den")
_TOPIC_SCENARIO_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("venho_lake_view_room_sunrise", ("phong", "cua so", "giuong", "room", "nhan phong", "check in", "check-in")),
    ("venho_lobby_cozy", ("sanh", "lobby", "doc sach", "le tan")),
    ("venho_nguyen_dinh_thi_street", ("nguyen dinh thi", "pho", "doc duong", "tren duong", "con duong", "duong pho", "xe dap", "di bo", "via he", "thanh nien")),
    ("venho_west_lake_landscape", ("mat ho", "ho tay", "west lake", "sen", "mat nuoc", "ven ho", "bo ho", "suong som")),
    ("venho_rooftop_sunset", _EVENING),
    ("venho_rooftop_sunrise", ("binh minh", "sunrise", "sang som")),
]


def alternatives_enabled() -> bool:
    return os.environ.get(ALTERNATIVES_ENV) == "1"


def _fold(text: str) -> str:
    folded = unicodedata.normalize("NFD", str(text or "").replace("đ", "d").replace("Đ", "D"))
    folded = "".join(ch for ch in folded if unicodedata.category(ch) != "Mn").lower()
    return " " + " ".join(re.findall(r"[a-z0-9-]+", folded)) + " "


def topic_scenario(topic_text: str, candidates: list[str]) -> Optional[str]:
    """The candidate scenario the topic's own words point at, or None."""
    folded = _fold(topic_text)

    def has(words: tuple[str, ...]) -> bool:
        return any(f" {word} " in folded for word in words)

    if has(_ROOFTOP):
        rooftop = "venho_rooftop_sunset" if has(_EVENING) else "venho_rooftop_sunrise"
        if rooftop in candidates:
            return rooftop
    for scenario_key, keywords in _TOPIC_SCENARIO_KEYWORDS:
        if scenario_key in candidates and has(keywords):
            return scenario_key
    return None


def alternate_scenario(primary: str, pool: list[str], scenario_registry: Any) -> Optional[str]:
    """A different scene for option B: prefer another DNA subject, then any
    other scenario in the pool."""
    others = [key for key in pool if key != primary]
    if not others:
        return None
    primary_subject = scenario_registry.resolve(primary).dna_subject
    different = [key for key in others if scenario_registry.resolve(key).dna_subject != primary_subject]
    return (different or others)[0]


def library_photo_path(scenario_key: str, scenario_registry: Any, reference_resolver: Any, *, rotation_key: Optional[str]) -> Optional[Path]:
    """A real photo for option C from the scenario's reference folder, one
    step further in the rotation than the photo option A was conditioned on."""
    asset_ids = list(scenario_registry.resolve(scenario_key).reference_asset_ids or [])
    if not asset_ids:
        return None
    relative = reference_resolver.mapping.get(asset_ids[0])
    if not relative:
        return None
    path = reference_resolver.assets_root / relative
    if path.is_dir():
        path = reference_resolver._pick_from_folder(path, rotation_key, 1)
    return path if path.is_file() else None


def to_upload_png(source: Path, *, max_side: int = 2048) -> Path:
    """Re-encode any photo (HEIC/MPO/JPEG) as a bounded PNG for Drive/Make.
    The resolver module registers the HEIF opener on import."""
    import agent_studio.growth.reference_asset_resolver  # noqa: F401 - registers HEIF support

    with Image.open(source) as image:
        image = image.convert("RGB")
        image.thumbnail((max_side, max_side))
        handle = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        handle.close()
        image.save(handle.name, format="PNG")
    return Path(handle.name)


def option(option_id: str, *, kind: str, url: str, scenario: Optional[str] = None, asset_version_id: Optional[str] = None, source: Optional[str] = None) -> dict[str, Any]:
    entry: dict[str, Any] = {"id": option_id, "kind": kind, "url": url}
    if scenario:
        entry["scenario"] = scenario
    if asset_version_id:
        entry["asset_version_id"] = asset_version_id
    if source:
        entry["source"] = source
    return entry
