from __future__ import annotations

from pathlib import Path

from PIL import Image

from agent_studio.growth.reference_asset_resolver import ReferenceAssetResolver


def test_iphone_heic_saved_with_a_jpeg_name_still_resolves(tmp_path: Path) -> None:
    """assets/raw/room held three iPhone HEIC files named .jpeg; Pillow alone
    raised UnidentifiedImageError, which surfaced as the 'reference_or_dna_
    file_missing' fallback reason (2026-10-21)."""
    from pillow_heif import from_pillow

    folder = tmp_path / "assets" / "raw" / "room"
    folder.mkdir(parents=True)
    from_pillow(Image.new("RGB", (32, 32), (78, 143, 160))).save(str(folder / "IMG_0001.jpeg"))

    resolver = ReferenceAssetResolver({"room": "assets/raw/room"}, assets_root=tmp_path)
    png = resolver.resolve(["room"], rotation_key="2026-10-26")[0]

    assert png[:8] == b"\x89PNG\r\n\x1a\n"
