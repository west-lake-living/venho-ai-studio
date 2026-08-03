from __future__ import annotations


def compose_text_overlay_request(base_artifact: str, text: str, position: str = "bottom") -> dict:
    return {"base_artifact": base_artifact, "text": text, "position": position, "deterministic": True}
