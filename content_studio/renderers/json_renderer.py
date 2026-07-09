from __future__ import annotations

import json
from pathlib import Path

from content_studio.schemas.content_output import ContentOutput


def write_json(path: Path, output: ContentOutput) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")

