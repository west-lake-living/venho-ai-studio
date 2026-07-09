from __future__ import annotations

import json
from typing import Any


def render_json(payload: Any) -> str:
    data = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
    return json.dumps(data, ensure_ascii=False, indent=2)
