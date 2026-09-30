"""Locked calibration fixtures for the identity measurement policy.

Positives are real frames (A2, B01). Every negative is derived from A2 by a fixed, parameterised
recipe, so the fixture set is reproducible and its pixel hashes can live in the policy payload.
``pixel_sha256`` hashes decoded RGB pixels (not PNG bytes), so it does not depend on the encoder.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any, Callable, Mapping

import numpy as np
from PIL import Image, ImageFilter

from .identity_measurement import BLUR, FRAMING, measure_identity, sha256_hex

RECIPE_VERSION = "identity-measurement-fixtures-v1"
# The ladder crosses the threshold: the first rung is still sharp enough (a sanity check that BLUR
# is not over-strict); the rest sit below it.
BLUR_SIGMAS_ABOVE = (2.0,)
BLUR_SIGMAS_BELOW = (4.0, 8.0, 12.0)
SMALL_FACE_HEIGHT_RATIO = 0.05
SMALL_FACE_CANVAS = 1024
EDGE_CROP_FRACTION = 0.55  # keep the left 55% of the face box width: the face is cut at the edge


def pixel_sha256(image: Image.Image) -> str:
    rgb = image.convert("RGB")
    return sha256_hex(f"{rgb.width}x{rgb.height}:RGB:".encode() + rgb.tobytes())


def png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def _observe(image: Image.Image, observer: Any) -> Mapping[str, Any]:
    from .identity_measurement import _full_mask

    return observer.observe(png_bytes(image), _full_mask(image.size)).as_dict()


def gaussian_blur(base: Image.Image, sigma: float) -> Image.Image:
    return base.convert("RGB").filter(ImageFilter.GaussianBlur(radius=sigma))


def small_face(base: Image.Image, observation: Mapping[str, Any]) -> Image.Image:
    box = observation["bbox"]
    face_h = box["bottom"] - box["top"]
    scale = (SMALL_FACE_HEIGHT_RATIO * SMALL_FACE_CANVAS) / face_h
    resized = base.convert("RGB").resize(
        (max(1, round(base.width * scale)), max(1, round(base.height * scale))), Image.LANCZOS
    )
    canvas = Image.new("RGB", (SMALL_FACE_CANVAS, SMALL_FACE_CANVAS), (128, 128, 128))
    canvas.paste(resized, ((SMALL_FACE_CANVAS - resized.width) // 2, (SMALL_FACE_CANVAS - resized.height) // 2))
    return canvas


def edge_cropped_face(base: Image.Image, observation: Mapping[str, Any]) -> Image.Image:
    box = observation["bbox"]
    right = int(box["left"] + EDGE_CROP_FRACTION * (box["right"] - box["left"]))
    return base.convert("RGB").crop((0, 0, right, base.height))


def two_faces(base: Image.Image, other: Image.Image) -> Image.Image:
    other = other.convert("RGB").resize(
        (max(1, round(other.width * base.height / other.height)), base.height), Image.LANCZOS
    )
    canvas = Image.new("RGB", (base.width + other.width, base.height))
    canvas.paste(base.convert("RGB"), (0, 0))
    canvas.paste(other, (base.width, 0))
    return canvas


def build_fixtures(a2: Image.Image, b01: Image.Image, observer: Any) -> list[dict[str, Any]]:
    """[{id, role, target, recipe, image}] in a fixed order."""
    a2_obs = _observe(a2, observer)
    items: list[dict[str, Any]] = [
        {"id": "A2", "role": "positive", "target": None, "recipe": None, "image": a2.convert("RGB")},
        {"id": "B01", "role": "positive", "target": None, "recipe": None, "image": b01.convert("RGB")},
    ]
    for sigma in BLUR_SIGMAS_ABOVE + BLUR_SIGMAS_BELOW:
        below = sigma in BLUR_SIGMAS_BELOW
        items.append({"id": f"A2_blur_sigma_{sigma:g}", "role": "negative" if below else "positive",
                      "target": BLUR if below else None,
                      "recipe": {"op": "gaussian_blur", "sigma_px": sigma, "of": "A2"},
                      "image": gaussian_blur(a2, sigma)})
    items += [
        {"id": "A2_face_below_8pct", "role": "negative", "target": FRAMING,
         "recipe": {"op": "small_face", "face_height_ratio": SMALL_FACE_HEIGHT_RATIO,
                    "canvas": SMALL_FACE_CANVAS, "fill": [128, 128, 128], "of": "A2"},
         "image": small_face(a2, a2_obs)},
        {"id": "A2_face_cut_at_edge", "role": "negative", "target": FRAMING,
         "recipe": {"op": "crop_left", "face_width_fraction": EDGE_CROP_FRACTION, "of": "A2"},
         "image": edge_cropped_face(a2, a2_obs)},
        {"id": "A2_B01_two_faces", "role": "negative", "target": FRAMING,
         "recipe": {"op": "side_by_side", "of": ["A2", "B01"]},
         "image": two_faces(a2, b01)},
    ]
    return items


def calibrate(a2: Image.Image, b01: Image.Image, observer: Any, policy: Mapping[str, Any]) -> dict[str, Any]:
    """Measure every fixture. A positive must pass all three; a negative must fail its target."""
    rows: list[dict[str, Any]] = []
    for item in build_fixtures(a2, b01, observer):
        measured = measure_identity(png_bytes(item["image"]), policy, observer)
        by_type = {r["measurementType"]: r for r in measured["results"]}
        if item["role"] == "positive":
            ok = all(r["pass"] for r in by_type.values())
        else:
            ok = not by_type[item["target"]]["pass"]
        rows.append({
            "id": item["id"], "role": item["role"], "target": item["target"], "recipe": item["recipe"],
            "pixelSha256": pixel_sha256(item["image"]),
            "results": {k: {"pass": v["pass"], "value": v["measuredValue"], "reasons": v["failureReasons"],
                            "checks": v["checks"]} for k, v in by_type.items()},
            "faceCount": measured["faceCount"],
            "expected": "all_pass" if item["role"] == "positive" else f"{item['target']}_fails",
            "calibrationOk": ok,
        })
    return {"recipeVersion": RECIPE_VERSION, "fixtures": rows, "allOk": all(r["calibrationOk"] for r in rows)}


__all__ = ["RECIPE_VERSION", "build_fixtures", "calibrate", "pixel_sha256", "png_bytes"]
