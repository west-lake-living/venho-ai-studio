from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT_REGISTRY_PATH = Path("config/projects/venho_hotel/growth/reference_assets.yaml")
DEFAULT_ASSETS_ROOT = Path(".")


class ReferenceAssetResolver:
    """Resolves scenario_registry.yaml's `reference_asset_ids` to real file bytes.

    See reference_assets.yaml for the caveat: mappings are provisional
    defaults, not a curated/approved reference pack.
    """

    def __init__(self, mapping: dict[str, str], *, assets_root: Path = DEFAULT_ASSETS_ROOT) -> None:
        self.mapping = mapping
        self.assets_root = assets_root

    @classmethod
    def from_file(cls, path: Path = DEFAULT_REGISTRY_PATH, *, assets_root: Path = DEFAULT_ASSETS_ROOT) -> "ReferenceAssetResolver":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(dict(payload.get("assets") or {}), assets_root=assets_root)

    def resolve(self, asset_ids: list[str]) -> list[bytes]:
        images: list[bytes] = []
        for asset_id in asset_ids:
            relative_path = self.mapping.get(asset_id)
            if relative_path is None:
                raise KeyError(f"No reference asset mapped for id: {asset_id}")
            images.append((self.assets_root / relative_path).read_bytes())
        return images
