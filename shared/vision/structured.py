from __future__ import annotations

import json
import re


def extract_json(text: str) -> dict | list:
    """Extract JSON (object or array) from a model response.

    Strips markdown code fences if present.
    """
    text = text.strip()

    # Strip ```json ... ``` or ``` ... ``` fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    # Find the outermost JSON structure (object or array)
    obj_start = text.find("{")
    arr_start = text.find("[")

    if obj_start == -1 and arr_start == -1:
        raise ValueError(f"No JSON found in response:\n{text[:300]}")

    if arr_start != -1 and (obj_start == -1 or arr_start < obj_start):
        # Array is first
        start = arr_start
        open_ch, close_ch = "[", "]"
    else:
        start = obj_start
        open_ch, close_ch = "{", "}"

    text = text[start:]
    depth = 0
    for i, ch in enumerate(text):
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                text = text[: i + 1]
                break

    return json.loads(text)
