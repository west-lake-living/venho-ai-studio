from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from growth_engine.adapters.outbound.media.local_legacy_image_library import LocalLegacyImageLibrary


def _jpeg(path: Path, color: tuple[int, int, int]) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 24), color).save(path, format="JPEG")
    return path.read_bytes()


def test_local_library_reads_only_hash_pinned_files_under_root(tmp_path: Path) -> None:
    root = tmp_path / "assets/raw"
    image_path = root / "outside" / "hotel.jpg"
    payload = _jpeg(image_path, (30, 70, 100))
    digest = hashlib.sha256(payload).hexdigest()
    library = LocalLegacyImageLibrary(
        root,
        {"venho_rooftop_railing_approved": ({"path": "outside/hotel.jpg", "sha256": digest},)},
    )

    image = library.resolve("venho_rooftop_railing_approved", "2026-11-21", 1)

    assert image is not None
    assert image.relative_path == "outside/hotel.jpg"
    assert image.sha256 == digest
    assert image.mime_type == "image/jpeg"
    library.validate_reference_ids({"venho_rooftop_railing_approved"})


@pytest.mark.parametrize("bad_path", ["../outside.jpg", "/outside.jpg", "outside//x.jpg", r"outside\x.jpg"])
def test_local_library_rejects_unsafe_allowlist_paths(tmp_path: Path, bad_path: str) -> None:
    root = tmp_path / "assets/raw"
    root.mkdir(parents=True)
    with pytest.raises(ValueError, match="safe relative|unsafe component"):
        LocalLegacyImageLibrary(
            root,
            {"group": ({"path": bad_path, "sha256": "a" * 64},)},
        )


def test_local_library_rejects_symlink_escape_and_changed_sha(tmp_path: Path) -> None:
    root = tmp_path / "assets/raw"
    outside = tmp_path / "outside.jpg"
    payload = _jpeg(outside, (80, 30, 10))
    digest = hashlib.sha256(payload).hexdigest()
    link = root / "outside" / "escape.jpg"
    link.parent.mkdir(parents=True)
    link.symlink_to(outside)
    library = LocalLegacyImageLibrary(
        root,
        {"group": ({"path": "outside/escape.jpg", "sha256": digest},)},
    )
    with pytest.raises(OSError):
        library.read_for_reference("group", "outside/escape.jpg")

    regular = root / "outside" / "regular.jpg"
    changed_payload = _jpeg(regular, (5, 160, 20))
    changed = LocalLegacyImageLibrary(
        root,
        {"group": ({"path": "outside/regular.jpg", "sha256": digest},)},
    )
    assert hashlib.sha256(changed_payload).hexdigest() != digest
    with pytest.raises(ValueError, match="changed after allowlist review"):
        changed.read_for_reference("group", "outside/regular.jpg")

    root_alias = tmp_path / "assets/raw-alias"
    root_alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError, match="root contains a symlink"):
        LocalLegacyImageLibrary(
            root_alias,
            {"group": ({"path": "outside/regular.jpg", "sha256": digest},)},
        )


def test_inventory_uses_legacy_catalog_mapping_and_excludes_unmapped_folders(tmp_path: Path) -> None:
    root = tmp_path / "assets/raw"
    _jpeg(root / "outside" / "rooftop.jpg", (10, 50, 120))
    _jpeg(root / "westlake" / "lake.jpg", (20, 60, 130))
    _jpeg(root / "facade" / "front.jpg", (30, 70, 140))
    _jpeg(root / "linh_an" / "portrait.jpg", (40, 80, 150))
    catalog = tmp_path / "reference_assets.yaml"
    catalog.write_text(
        "assets:\n"
        "  venho_rooftop_railing_approved: assets/raw/outside\n"
        "  venho_street_railing_approved: assets/raw/westlake\n"
        "  venho_lake_landscape_approved: assets/raw/westlake\n",
        encoding="utf-8",
    )
    output = tmp_path / "config/growth-engine-image-library.yaml"
    script = Path(__file__).resolve().parents[2] / "scripts/growth_engine/prepare_legacy_image_library.py"
    result = subprocess.run(
        [sys.executable, str(script), "--assets-root", str(root), "--catalog", str(catalog), "--output", str(output), "--apply"],
        input="WRITE\n",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "venho_street_railing_approved" in result.stdout
    assert "venho_lake_landscape_approved" in result.stdout
    assert "unmapped_top_level_dirs=facade,linh_an" in result.stdout
    assert "linh_an/portrait.jpg" not in result.stdout
    assert "IMAGE_LIBRARY_WRITE=PASS entries=3 mode=600" in result.stdout
    assert os.stat(output).st_mode & 0o777 == 0o600
