from __future__ import annotations

import hashlib
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from growth_engine.adapters.outbound.media.local_legacy_image_library import LocalLegacyImageLibrary
from tests.growth_engine.support.image_fixtures import make_mpo, make_orientation_jpeg


def _jpeg(path: Path, color: tuple[int, int, int]) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 24), color).save(path, format="JPEG")
    return path.read_bytes()


def _heic_bytes() -> bytes:
    pillow_heif = pytest.importorskip("pillow_heif")
    image = Image.new("RGB", (32, 24), (55, 80, 110))
    output = io.BytesIO()
    pillow_heif.from_pillow(image).save(output)
    return output.getvalue()


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


def test_local_library_detects_heic_by_content_and_ignores_jpeg_suffix(tmp_path: Path) -> None:
    root = tmp_path / "assets/raw"
    path = root / "room/ViewHo-room-1/IMG_5584.jpeg"
    path.parent.mkdir(parents=True)
    heic = _heic_bytes()
    path.write_bytes(heic)
    digest = hashlib.sha256(heic).hexdigest()
    library = LocalLegacyImageLibrary(
        root,
        {"venho_room_lake_view_approved": ({"path": path.relative_to(root).as_posix(), "sha256": digest},)},
    )

    image = library.resolve("venho_room_lake_view_approved", "2026-11-21")

    assert image is not None
    assert image.mime_type == "image/heif"
    assert image.sha256 == digest


def test_local_library_accepts_mpo_as_jpeg_source_and_keeps_original_hash(tmp_path: Path) -> None:
    root = tmp_path / "assets/raw"
    path = root / "outside/IMG_5136.jpeg"
    path.parent.mkdir(parents=True)
    original = make_mpo()
    path.write_bytes(original)
    digest = hashlib.sha256(original).hexdigest()
    library = LocalLegacyImageLibrary(
        root,
        {"venho_rooftop_railing_approved": ({"path": "outside/IMG_5136.jpeg", "sha256": digest},)},
    )

    image = library.resolve("venho_rooftop_railing_approved", "2026-11-21")

    assert image is not None
    assert image.mime_type == "image/jpeg"
    assert image.sha256 == digest
    with Image.open(io.BytesIO(image.data)) as decoded:
        assert decoded.format == "MPO"
        assert decoded.n_frames == 2
        decoded.seek(0)
        decoded.load()


def test_local_library_accepts_exif_oriented_jpeg_source(tmp_path: Path) -> None:
    root = tmp_path / "assets/raw"
    path = root / "room/rotated.JPG"
    path.parent.mkdir(parents=True)
    original = make_orientation_jpeg(6)
    path.write_bytes(original)
    digest = hashlib.sha256(original).hexdigest()
    library = LocalLegacyImageLibrary(
        root,
        {"venho_room_lake_view_approved": ({"path": "room/rotated.JPG", "sha256": digest},)},
    )

    image = library.resolve("venho_room_lake_view_approved", "2026-11-21")

    assert image is not None
    assert image.mime_type == "image/jpeg"
    assert image.sha256 == digest


def test_local_library_accepts_uppercase_jpg_and_warns_for_corrupt_peer(tmp_path: Path) -> None:
    root = tmp_path / "assets/raw"
    good_path = root / "westlake/Valid.JPG"
    good_bytes = _jpeg(good_path, (70, 90, 110))
    bad_path = root / "westlake/broken.jpeg"
    bad_path.write_bytes(b"not an image")
    entries = tuple(
        {"path": p.relative_to(root).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in (good_path, bad_path)
    )
    library = LocalLegacyImageLibrary(root, {"group": entries})

    issues = library.validate_reference_ids({"group"})
    selected = library.resolve("group", "2026-11-21")

    assert len(issues) == 1
    assert issues[0].code == "ERR_GC2_LEGACY_IMAGE_INVALID"
    assert issues[0].relative_path == "westlake/broken.jpeg"
    assert selected is not None and selected.mime_type == "image/jpeg"
    assert selected.sha256 == hashlib.sha256(good_bytes).hexdigest()


def test_local_library_reports_code_group_and_file_when_no_valid_image_remains(tmp_path: Path) -> None:
    root = tmp_path / "assets/raw"
    broken = root / "room/broken.jpeg"
    broken.parent.mkdir(parents=True)
    broken.write_bytes(b"broken bytes")
    library = LocalLegacyImageLibrary(
        root,
        {"venho_room_lake_view_approved": ({
            "path": "room/broken.jpeg",
            "sha256": hashlib.sha256(broken.read_bytes()).hexdigest(),
        },)},
    )

    with pytest.raises(ValueError) as caught:
        library.validate_reference_ids({"venho_room_lake_view_approved"})

    assert "ERR_GC2_LEGACY_IMAGE_GROUP_NO_VALID_FILES" in str(caught.value)
    assert "ERR_GC2_LEGACY_IMAGE_INVALID" in str(caught.value)
    assert "group=venho_room_lake_view_approved" in str(caught.value)
    assert "file=room/broken.jpeg" in str(caught.value)
    assert "broken bytes" not in str(caught.value)


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
    with pytest.raises(ValueError) as symlink_error:
        library.read_for_reference("group", "outside/escape.jpg")
    assert "ERR_GC2_LEGACY_IMAGE_READ" in str(symlink_error.value)
    assert "group=group" in str(symlink_error.value)
    assert "file=outside/escape.jpg" in str(symlink_error.value)

    regular = root / "outside" / "regular.jpg"
    changed_payload = _jpeg(regular, (5, 160, 20))
    changed = LocalLegacyImageLibrary(
        root,
        {"group": ({"path": "outside/regular.jpg", "sha256": digest},)},
    )
    assert hashlib.sha256(changed_payload).hexdigest() != digest
    with pytest.raises(ValueError, match="ERR_GC2_LEGACY_IMAGE_SHA256_MISMATCH"):
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

    unchanged = subprocess.run(
        [sys.executable, str(script), "--assets-root", str(root), "--catalog", str(catalog), "--output", str(output), "--apply"],
        input="",
        text=True,
        capture_output=True,
        check=False,
    )
    assert unchanged.returncode == 0, unchanged.stderr
    assert "IMAGE_LIBRARY_WRITE=UNCHANGED entries=3 mode=600" in unchanged.stdout
    assert "Type WRITE" not in unchanged.stdout
