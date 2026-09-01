from __future__ import annotations

import hashlib
from datetime import date
from io import BytesIO
from pathlib import Path

import yaml
from PIL import Image

DEFAULT_REGISTRY_PATH = Path("config/projects/venho_hotel/growth/reference_assets.yaml")
DEFAULT_ASSETS_ROOT = Path(".")

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _rotation_index(rotation_key: str | None, pool_size: int) -> int:
    """Deterministic pick within a pool, stable across a run but varied over time.

    Same convention as publishing_gateway.fallback_images._rotation_index (a
    calendar rotation_key advances by date; anything else falls back to a
    stable hash) -- kept as a private duplicate here rather than importing
    across modules for one small helper with a slightly different pool
    (per-scenario reference photos, not per-DNA-subject fallback photos).
    """
    if pool_size <= 1 or not rotation_key:
        return 0
    try:
        return date.fromisoformat(rotation_key).toordinal() % pool_size
    except ValueError:
        digest = hashlib.sha256(rotation_key.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % pool_size


class ReferenceAssetResolver:
    """Resolves scenario_registry.yaml's `reference_asset_ids` to real file bytes.

    Each id in reference_assets.yaml maps to either a single file (pinned) or
    a folder under assets/raw/ (rotating pool). Folder mode (2026-09-01) is
    what lets Harry add a new phone photo straight into an existing
    assets/raw/<subject>/ folder and have it picked up on the next run with
    no config edit -- the alternative (one hardcoded filename per scenario)
    is what left westlake/outside/lobby generation drawing on the same one
    or two "first usable shot found" photos for a month. See
    reference_assets.yaml for the per-id mapping and provenance caveat.
    """

    def __init__(self, mapping: dict[str, str], *, assets_root: Path = DEFAULT_ASSETS_ROOT) -> None:
        self.mapping = mapping
        self.assets_root = assets_root

    @classmethod
    def from_file(cls, path: Path = DEFAULT_REGISTRY_PATH, *, assets_root: Path = DEFAULT_ASSETS_ROOT) -> "ReferenceAssetResolver":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(dict(payload.get("assets") or {}), assets_root=assets_root)

    def resolve(self, asset_ids: list[str], *, rotation_key: str | None = None) -> list[bytes]:
        images: list[bytes] = []
        for asset_id in asset_ids:
            relative_path = self.mapping.get(asset_id)
            if relative_path is None:
                raise KeyError(f"No reference asset mapped for id: {asset_id}")
            path = self.assets_root / relative_path
            if path.is_dir():
                path = self._pick_from_folder(path, rotation_key)
            images.append(self._load_as_png(path))
        return images

    @staticmethod
    def _pick_from_folder(folder: Path, rotation_key: str | None) -> Path:
        # rglob so a subject folder organised into sub-albums (e.g.
        # assets/raw/room/ViewHo-room-1/, ViewHo-room-2/) still pools every
        # photo underneath it, not just loose files at the top level.
        candidates = sorted(
            (p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in _IMAGE_EXTENSIONS),
            key=lambda p: p.relative_to(folder).as_posix(),
        )
        if not candidates:
            raise FileNotFoundError(f"No reference photos found in {folder} (expected .jpg/.jpeg/.png)")
        return candidates[_rotation_index(rotation_key, len(candidates))]

    @staticmethod
    def _load_as_png(path: Path) -> bytes:
        # Re-encode through PIL rather than returning raw file bytes: some
        # raw phone photos are MPO (multi-picture JPEG container, e.g. iOS
        # portrait-mode shots) which OpenAI's images.edit endpoint rejects
        # with "Invalid image file or mode" -- a plain single-frame PNG is
        # always accepted regardless of the source file's original format.
        with Image.open(path) as image:
            buffer = BytesIO()
            image.convert("RGB").save(buffer, format="PNG")
            return buffer.getvalue()
