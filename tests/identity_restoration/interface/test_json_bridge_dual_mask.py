from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

from PIL import Image

from identity_restoration.interface.json_bridge import parse_restore_command


def _png(size: tuple[int, int], color: int) -> bytes:
    image = Image.new("L", size, color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_json_bridge_keeps_crop_and_full_canvas_masks_in_distinct_spaces(tmp_path: Path):
    base = tmp_path / "base.png"
    crop = tmp_path / "crop.png"
    crop_mask = tmp_path / "crop-mask.png"
    full_mask = tmp_path / "full-mask.png"
    Image.new("RGBA", (64, 64), (10, 20, 30, 255)).save(base)
    Image.new("RGBA", (16, 16), (100, 110, 120, 255)).save(crop)
    crop_mask.write_bytes(_png((16, 16), 255))
    full_mask.write_bytes(_png((64, 64), 255))
    payload = {
        "runId": "run-test", "attemptId": "attempt-1", "restorerId": "mock",
        "basePath": str(base), "cropPath": str(crop), "maskEditablePath": str(crop_mask),
        "fullCanvasMaskPath": str(full_mask),
        "fullCanvasMaskSha256": hashlib.sha256(full_mask.read_bytes()).hexdigest(),
        "cropBox": {"left": 8, "top": 8, "right": 24, "bottom": 24, "targetSize": 16},
        "a2Path": "a2.png", "a2Sha256": "a" * 64, "workflowId": "mock",
        "seed": 42,
        "params": {"denoise": 0.45, "steps": 28, "cfg": 5.5,
                    "sampler": "dpmpp_2m", "scheduler": "karras"},
    }

    command = parse_restore_command(payload)

    assert Image.open(BytesIO(command.mask.editable)).size == (16, 16)
    assert Image.open(BytesIO(command.full_canvas_mask.editable)).size == (64, 64)

