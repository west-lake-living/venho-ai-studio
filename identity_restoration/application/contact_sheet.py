"""Timestamped contact sheets of a motion clip for AI clip review (contract contact-sheet-v1).

FlowKit reviews generated clips from frame grids labelled with their timestamps, so the
reviewer can answer in time ranges. Frames are sampled at a fixed rate (last frame kept), each
tile is labelled "t=1.0s", sheets are written once as PNG. Local only; decodes with OpenCV.
"""

from __future__ import annotations

import hashlib
import io
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .temporal_scan import DecodedFrame, cv2_frame_reader

SCHEMA = "contact-sheet-v1"
TILE_SIZE = (360, 640)  # 9:16 tile; a 3x3 sheet is 1080x1920, inside the 2048 px input bound

FrameReader = Callable[[Path, float], Iterable[DecodedFrame]]


def _tile(frame: DecodedFrame) -> Image.Image:
    tile = frame.image.convert("RGB")
    tile.thumbnail(TILE_SIZE, Image.LANCZOS)
    canvas = Image.new("RGB", TILE_SIZE, (0, 0, 0))
    canvas.paste(tile, ((TILE_SIZE[0] - tile.width) // 2, (TILE_SIZE[1] - tile.height) // 2))
    draw = ImageDraw.Draw(canvas)
    label = f"t={frame.timestamp_ms / 1000:.1f}s"
    draw.rectangle((0, 0, 120, 28), fill=(0, 0, 0))
    draw.text((8, 6), label, fill=(255, 255, 0))
    return canvas


def build_contact_sheets(
    video: Path,
    out_dir: Path,
    *,
    sample_fps: float = 1.0,
    cols: int = 3,
    rows: int = 3,
    reader: FrameReader = cv2_frame_reader,
) -> dict[str, Any]:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(f"out-dir must be empty (write-once): {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = list(reader(video, sample_fps))
    if not frames:
        raise ValueError("no frame could be decoded")
    per_sheet = cols * rows
    sheets: list[dict[str, Any]] = []
    for start in range(0, len(frames), per_sheet):
        chunk = frames[start : start + per_sheet]
        sheet = Image.new("RGB", (TILE_SIZE[0] * cols, TILE_SIZE[1] * rows), (0, 0, 0))
        for index, frame in enumerate(chunk):
            sheet.paste(_tile(frame), ((index % cols) * TILE_SIZE[0], (index // cols) * TILE_SIZE[1]))
        buffer = io.BytesIO()
        sheet.save(buffer, format="PNG")
        data = buffer.getvalue()
        path = out_dir / f"sheet_{len(sheets) + 1:02d}.png"
        path.write_bytes(data)
        sheets.append({
            "path": str(path),
            "sha256": hashlib.sha256(data).hexdigest(),
            "timestamps_ms": [frame.timestamp_ms for frame in chunk],
        })
    return {
        "schema": SCHEMA,
        "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
        "sample_fps": sample_fps,
        "duration_sec": frames[-1].timestamp_ms / 1000,
        "sheets": sheets,
    }
