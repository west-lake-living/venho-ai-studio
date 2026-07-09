from __future__ import annotations

import json
from pathlib import Path

from video_studio.schemas.video_package import VideoPackage


def write_json(path: Path, package: VideoPackage) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(package.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")

