from __future__ import annotations

import json
import re


class StructuredResponseError(ValueError):
    """A response could not be normalized into the expected JSON value.

    The raw provider response is deliberately retained on the exception so a
    caller can persist it before classifying the validator attempt as invalid.
    """

    def __init__(self, message: str, *, raw: str) -> None:
        super().__init__(message)
        self.raw = raw


def _json_candidate(text: str) -> str:
    """Return one balanced JSON object/array from harmless wrapper prose."""
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text, re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()

    starts = [(index, char, "}" if char == "{" else "]")
              for index, char in enumerate(text) if char in "{["]
    if not starts:
        raise StructuredResponseError("No JSON found in response", raw=text)
    start, opening, closing = min(starts, key=lambda item: item[0])
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise StructuredResponseError("Truncated JSON response", raw=text)


def extract_json(text: str) -> dict | list:
    """Extract JSON (object or array) from a model response.

    Strips markdown code fences if present.
    """
    raw = str(text)
    normalized = raw.strip()
    try:
        candidate = _json_candidate(normalized)
        return json.loads(candidate)
    except StructuredResponseError:
        raise
    except json.JSONDecodeError as exc:
        raise StructuredResponseError(
            f"Invalid JSON response: {exc.msg} at line {exc.lineno} column {exc.colno}",
            raw=raw,
        ) from exc
