from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
BASE = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png")
FULL_MASK = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/face-mask.png")
MANIFEST = ROOT / "data/identity_restoration_runs/gw-p0-t2-qc4c2f-local-candidate/composite/manifest.json"


def test_authoritative_full_canvas_mask_matches_locked_case_and_crop_space():
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["job"]["base_image"] == str(BASE)
    assert manifest["job"]["metadata"]["mask_path"] == str(FULL_MASK)
    assert manifest["job"]["metadata"]["mask_sha256"] == "506fd5e52274b59af2881dcbaef3fe7904da7f30c75dc3bc23492dadf50ffb94"
    assert hashlib.sha256(FULL_MASK.read_bytes()).hexdigest() == manifest["job"]["metadata"]["mask_sha256"]
    with Image.open(BASE) as base, Image.open(FULL_MASK) as mask:
        assert base.size == mask.size == (1024, 1280)
        crop = mask.crop((201, 0, 888, 659))
        assert crop.size == (687, 659)
        assert crop.getbbox() is not None
