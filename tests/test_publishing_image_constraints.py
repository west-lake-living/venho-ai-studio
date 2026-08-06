from __future__ import annotations

import shutil
import struct
import subprocess
import zlib
from pathlib import Path

import pytest

from growth_orchestrator.application.daily_cycle import _upload_image_to_drive
from publishing_gateway.image_constraints import aspect_ratio_rejection, read_image_size


def _png(path: Path, width: int, height: int) -> Path:
    """Smallest valid PNG of a given size -- header fields are what's read."""
    def chunk(tag: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(height))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    )
    return path


def test_reads_png_dimensions(tmp_path: Path) -> None:
    assert read_image_size(_png(tmp_path / "a.png", 1024, 1280)) == (1024, 1280)


def test_reads_jpeg_dimensions(tmp_path: Path) -> None:
    """JPEG dimensions sit in a SOFn segment at no fixed offset, so this walks
    the marker chain -- worth testing against a real encoder's output."""
    if shutil.which("sips") is None:
        pytest.skip("sips (macOS) unavailable")
    source = _png(tmp_path / "src.png", 1440, 1080)
    subprocess.run(
        ["sips", "-s", "format", "jpeg", str(source), "--out", str(tmp_path / "out.jpg")],
        check=True, capture_output=True,
    )
    assert read_image_size(tmp_path / "out.jpg") == (1440, 1080)


def test_accepts_the_size_daily_cycle_asks_for(tmp_path: Path) -> None:
    """1024x1280 is exactly 0.80 -- the boundary. It must pass, or every
    generated photo would be discarded in favour of a fallback."""
    assert aspect_ratio_rejection(_png(tmp_path / "a.png", 1024, 1280)) is None


def test_accepts_landscape_within_the_window(tmp_path: Path) -> None:
    assert aspect_ratio_rejection(_png(tmp_path / "a.png", 1440, 1080)) is None


def test_rejects_the_ratio_instagram_actually_refused(tmp_path: Path) -> None:
    """659x1440 (0.46) -- the facade fallback photo that failed the first real
    Instagram dispatch with (36003)."""
    rejection = aspect_ratio_rejection(_png(tmp_path / "a.png", 659, 1440))
    assert rejection is not None and "0.46" in rejection


def test_rejects_too_wide(tmp_path: Path) -> None:
    assert aspect_ratio_rejection(_png(tmp_path / "a.png", 2000, 500)) is not None


def test_unreadable_file_is_not_treated_as_a_rejection(tmp_path: Path) -> None:
    """This guard catches one known failure; it must never become a second
    validation gate that silently drops photos it simply couldn't parse."""
    (tmp_path / "weird.webp").write_bytes(b"RIFF????WEBPVP8 ")
    assert aspect_ratio_rejection(tmp_path / "weird.webp") is None
    assert aspect_ratio_rejection(tmp_path / "missing.png") is None


class _RecordingUploader:
    def __init__(self) -> None:
        self.calls: list[Path] = []

    def upload_and_publish(self, path: Path, **kwargs) -> str:
        self.calls.append(path)
        return "https://drive.example/photo.png"


def _run_folder(tmp_path: Path, width: int, height: int) -> Path:
    folder = tmp_path / "run-1"
    folder.mkdir()
    _png(folder / "image.png", width, height)
    (folder / "manifest.json").write_text('{"artifacts": [{"path": "image.png"}]}', encoding="utf-8")
    return folder


def test_out_of_window_photo_is_never_uploaded(tmp_path: Path) -> None:
    uploader = _RecordingUploader()
    result = _upload_image_to_drive(
        _run_folder(tmp_path, 659, 1440), day="monday", content_package_id="pkg-1", uploader=uploader
    )
    # None is what makes daily_cycle substitute the on-brand fallback photo.
    assert result is None
    assert uploader.calls == []


def test_valid_photo_still_uploads(tmp_path: Path) -> None:
    uploader = _RecordingUploader()
    result = _upload_image_to_drive(
        _run_folder(tmp_path, 1024, 1280), day="monday", content_package_id="pkg-1", uploader=uploader
    )
    assert result == "https://drive.example/photo.png"
    assert len(uploader.calls) == 1
